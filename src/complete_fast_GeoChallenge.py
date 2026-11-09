"""Publish text and PNG from saved coordinates. No DDAR or random graph rebuild."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from multiprocessing import Pool
import os
from pathlib import Path
import random
import tempfile
import traceback

import matplotlib
matplotlib.use("Agg")
import numpy as np
from tqdm import tqdm

import _paths
import drawing
import graph as gh
import problem as pr
from display_rewrite import build_display_rewrite_plan
from geometry_snapshot import capture_graph, restore_graph
from publication import atomic_json, compact_payload
from translation import translate_goals_to_natural_language, translate_problem_to_natural_language


CONFIG = {}


def init_worker(config):
    global CONFIG
    CONFIG = config


def is_complete_publication(run_dir, draft):
    folder = Path(run_dir) / "published"
    try:
        payload = json.loads((folder / (draft["ID"] + ".json")).read_text(encoding="utf-8"))
        image = folder / (draft["ID"] + ".png")
        with image.open("rb") as stream:
            valid_png = stream.read(8) == b"\x89PNG\r\n\x1a\n" and image.stat().st_size > 24
        return (valid_png and payload.get("ID") == draft["ID"]
                and payload.get("Answer") == draft["Answer"]
                and payload.get("SimplifiedFormalText") == draft["FormalProblemText"].split("?")[0].rstrip()
                and all(payload.get(key) for key in ["Question_zh", "A_zh", "B_zh", "C_zh", "D_zh"]))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def get_snapshot(draft, path):
    if "GeometrySnapshot" in draft:
        return draft["GeometrySnapshot"], 0
    retries = CONFIG["legacy_build_retries"]
    if not retries:
        raise ValueError("Legacy draft has no saved coordinates. Use --legacy-build-retries N once to migrate it; new v2 drafts need no rebuild.")
    definitions = pr.Definition.from_txt_file(_paths.DEFS_PATH, to_dict=True)
    last_error = None
    for attempt in range(retries):
        seed = (CONFIG["seed"] + int.from_bytes(draft["ID"].encode(), "little") + attempt * 104729) % (2 ** 32)
        random.seed(seed)
        np.random.seed(seed)
        original = pr.Problem.from_txt(draft["OriginalFormalText"], translate=False)
        # A recorded source proof already exists; this is coordinate migration only.
        original.goal = None
        try:
            graph, _ = gh.Graph.build_problem(original, definitions, verbose=False)
            snapshot = capture_graph(graph, draft["OriginalFormalText"])
            draft["GeometrySnapshot"] = snapshot
            draft["Format"] = "fast_geochallenge_draft_v2"
            atomic_json(path, draft)
            return snapshot, attempt + 1
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Could not migrate legacy coordinates after {retries} attempts: {last_error}")


def draw_png(problem, snapshot, original_formal, used_points, suppressed_ids, conclusions, output):
    # Fresh, light drawing state each time; no Graph.copy() hidden rebuild.
    graph = restore_graph(snapshot, original_formal, used_points)
    descriptor, temporary = tempfile.mkstemp(prefix=".drawing_", suffix=".png", dir=output.parent)
    os.close(descriptor)
    try:
        drawer = drawing.ProblemDrawing(problem, graph, suppressed_ids)
        drawer.draw_problem(temporary, used_points=used_points, conclusions=conclusions)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def complete_one(draft_path):
    path = Path(draft_path)
    result = {"draft": path.name, "status": "failed"}
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
        problem_id = draft["ID"]
        if problem_id != path.stem or not problem_id.startswith("gen_"):
            raise ValueError("Draft ID does not match its file name")
        if is_complete_publication(CONFIG["run_dir"], draft):
            return {**result, "status": "skipped_existing"}
        snapshot, legacy_attempts = get_snapshot(draft, path)
        used_points = draft["StructuralPoints"]
        # Validate saved coordinates BEFORE any rendering, without falling back to random construction.
        restore_graph(snapshot, draft["OriginalFormalText"], used_points)
        problem = pr.Problem.from_txt(draft["FormalProblemText"], translate=False)
        problem.url = problem_id
        plan = build_display_rewrite_plan(problem)
        question = translate_problem_to_natural_language(plan.display_problem, "zh", used_points=used_points)
        options = draft["FormalOptions"]
        if len(options) != 4:
            raise ValueError("Expected four options")
        expected_answer = "".join("ABCD"[index] for index, option in enumerate(options) if option["is_correct"])
        if draft["Answer"] != expected_answer or not expected_answer:
            raise ValueError("Answer letters do not agree with formal options")
        candidates = [pr.Construction.from_txt(option["formal"]) for option in options]
        all_points = set(snapshot["points"])
        option_points = {name for candidate in candidates for name in candidate.args if name in all_points}
        formal_points = {name for clause in problem.clauses for name in clause.points}
        if not option_points.issubset(set(used_points) & formal_points):
            raise ValueError("Option contains a point outside the displayed construction")
        if not question or any(name.upper() not in question for name in option_points):
            raise ValueError("An option point is absent from the translated question")
        payload = dict(ID=problem_id, Question_zh=question, Answer=draft["Answer"],
                       Prior_Difficulty=draft["Prior_Difficulty"],
                       SimplifiedFormalText=draft["FormalProblemText"].split("?")[0].rstrip(),
                       AuxiliaryFormalText=draft.get("AuxiliaryFormalText", ""))
        translation_fallbacks = []
        for letter, candidate, option in zip("ABCD", candidates, options):
            try:
                text = translate_goals_to_natural_language((candidate.name,) + tuple(candidate.args), "zh", used_points=used_points)
                if not text:
                    raise ValueError("Empty option translation")
            except Exception as error:
                text = "形式化结论：" + candidate.txt()
                translation_fallbacks.append({"option": letter, "formal": candidate.txt(), "error": str(error)})
            payload[letter + "_zh"] = text
            payload["ProofSteps_" + letter] = option.get("source_proof", "")
        payload = compact_payload(payload)
        conclusions = [(candidate, option["is_correct"], "", candidate)
                       for candidate, option in zip(candidates, options)]
        folder = Path(CONFIG["run_dir"]) / "published"
        folder.mkdir(parents=True, exist_ok=True)
        image_path = folder / (problem_id + ".png")
        drawing_fallback = None
        try:
            draw_png(problem, snapshot, draft["OriginalFormalText"], used_points,
                     plan.suppressed_circle_construction_ids, conclusions, image_path)
        except Exception as error:
            # A degenerate false-option segment must not discard a valid premise diagram.
            # Both draws use exactly the saved coordinates, without a construction retry.
            drawing_fallback = {"error_type": type(error).__name__, "error": str(error)}
            draw_png(problem, snapshot, draft["OriginalFormalText"], used_points,
                     plan.suppressed_circle_construction_ids, [], image_path)
        audit = {"ID": problem_id, "draft": "../drafts/" + path.name,
                 "coordinate_mode": "saved_points", "legacy_build_attempts": legacy_attempts,
                 "drawing_fallback": drawing_fallback, "translation_fallbacks": translation_fallbacks,
                 "DisplayRewriteRecords": plan.records,
                 "FormalOptions": options, "OptionSourceCandidates": draft.get("OptionSourceCandidates", []),
                 "AuxiliaryClauseIndices": draft.get("AuxiliaryClauseIndices", [])}
        atomic_json(Path(CONFIG["run_dir"]) / "audit" / path.name, audit)
        atomic_json(folder / path.name, payload)
        return {**result, "status": "published", "legacy_build_attempts": legacy_attempts,
                "translation_fallbacks": len(translation_fallbacks), "drawing_fallback": bool(drawing_fallback)}
    except Exception as error:
        return {**result, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--resume", action="store_true", help="Compatibility option; completed pairs are always skipped")
    parser.add_argument("--legacy-build-retries", type=int, default=0,
                        help="Opt-in one-time migration for old drafts without coordinates; defaults to disabled")
    parser.add_argument("--seed", type=int, default=2447, help="Only used for legacy coordinate migration")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.legacy_build_retries < 0:
        parser.error("workers must be positive and legacy-build-retries must be nonnegative")
    run_dir = args.run_dir.resolve()
    drafts = sorted((run_dir / "drafts").glob("gen_*.json"))
    if not drafts:
        parser.error(f"No drafts under {run_dir / 'drafts'}")
    print(json.dumps({"draft_count": len(drafts), "workers": args.workers,
                      "coordinate_mode": "saved_points", "legacy_build_retries": args.legacy_build_retries}), flush=True)
    if args.dry_run:
        return
    config = {"run_dir": str(run_dir), "legacy_build_retries": args.legacy_build_retries, "seed": args.seed}
    counts = Counter()
    def consume(results):
        with (run_dir / "stage2_results.jsonl").open("a", encoding="utf-8") as stream:
            for result in tqdm(results, total=len(drafts), desc="Publish saved geometry"):
                counts[result["status"]] += 1
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                if result["status"] == "failed":
                    with (run_dir / "stage2_failures.jsonl").open("a", encoding="utf-8") as failures:
                        failures.write(json.dumps(result, ensure_ascii=False) + "\n")
    if args.workers == 1:
        init_worker(config)
        consume(map(complete_one, map(str, drafts)))
    else:
        with Pool(args.workers, initializer=init_worker, initargs=(config,), maxtasksperchild=50) as pool:
            consume(pool.imap_unordered(complete_one, map(str, drafts)))
    atomic_json(run_dir / "stage2_summary.json", {"finished_at": datetime.now(timezone.utc).isoformat(), **counts})


if __name__ == "__main__":
    main()
