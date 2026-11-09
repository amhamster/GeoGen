"""Fast, solver-only GeoChallenge generation stage.

Writes resumable draft JSON files.  Use complete_fast_GeoChallenge.py later
to add display rewrites, translated statements, and PNG diagrams.
"""
import argparse
import json
import os
import random
import re
import tempfile
import time
import traceback
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from tqdm import tqdm

import GeoChallenge as gc
import _paths
import graph as gh
import problem as pr
from translation import generate_wrong_answer
from geometry_snapshot import capture_graph


DEFINITIONS = None
RULES = None
CONFIG = {}


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tmp_", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def init_worker(config: dict) -> None:
    global DEFINITIONS, RULES, CONFIG
    CONFIG = config
    DEFINITIONS = pr.Definition.from_txt_file(_paths.DEFS_PATH, to_dict=True)
    RULES = pr.Theorem.from_txt_file(_paths.RULES_PATH, to_dict=True)
    gc.DEFINITIONS, gc.RULES = DEFINITIONS, RULES


def numeric_id(problem_id: str) -> int:
    match = re.search(r"(\d+)$", problem_id)
    return int(match.group(1)) if match else 0


def is_complete_draft(path: Path, problem_id: str) -> bool:
    """Return whether *path* is an atomically committed usable stage-1 draft.

    Stage 1 is deliberately restartable by default.  A partially written,
    malformed, or stale draft must therefore be regenerated instead of being
    mistaken for completed work.
    """
    try:
        with path.open("r", encoding="utf-8") as file:
            draft = json.load(file)
        required_fields = {
            "OriginalFormalText", "FormalProblemText", "Prior_Difficulty",
            "Answer", "FormalOptions", "ProofSteps",
        }
        return (isinstance(draft, dict)
                and draft.get("Format") in {"fast_geochallenge_draft_v1", "fast_geochallenge_draft_v2"}
                and (draft.get("Format") != "fast_geochallenge_draft_v2" or "GeometrySnapshot" in draft)
                and draft.get("ID") == problem_id
                and required_fields.issubset(draft))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def draft_one(source_problem: pr.Problem) -> dict | None:
    """Solve once and write all data needed by the later presentation stage."""
    start = time.perf_counter()
    try:
        random.seed(CONFIG["seed"] + numeric_id(source_problem.url))
        np.random.seed((CONFIG["seed"] + numeric_id(source_problem.url)) % (2 ** 32))
        graph, _ = gh.Graph.build_problem(source_problem, DEFINITIONS, verbose=False)
        layout_record = {"enabled": False}
        if CONFIG.get("layout_trials", 0):
            from layout_optimization import choose_layout
            graph, layout_record = choose_layout(
                source_problem, DEFINITIONS, graph, CONFIG["layout_trials"],
                (CONFIG["seed"] + numeric_id(source_problem.url)) % (2 ** 32))
        target, score, mixed, selection = gc.run_ddar_nogoal(graph, source_problem)
        if target is None:
            return None
        source_problem.goal = pr.Construction.from_txt(" ".join(target))
        original_formal = source_problem.txt()
        detail = gc.write_solution2(graph, source_problem)
        union = selection["union_plan"]
        detail["problem_content"] = union["problem_content"]
        detail["structural_clause_indices"] = union["clause_indices"]
        detail["structural_points"] = union["displayed_points"]
        detail["option_union_structural_points"] = union["seed_points"]
        detail["option_union_clause_indices"] = union["clause_indices"]
        detail["auxiliary_clause_indices"] = sorted(
            set(detail["proof_clause_indices"]) - set(union["clause_indices"]))
        detail["auxiliary_formal_text"] = gc.get_clauses_txt(
            [source_problem.clauses[i] for i in detail["auxiliary_clause_indices"]])
        detail["auxiliary_points"] = sorted(
            set(detail["proof_slice_points"]) - set(union["displayed_points"]))
        target_record = selection["selected_records"][0]
        score = gc.get_raw_difficulty(
            detail, target_record["search_level"], target_record["proof_step_count"])
        candidates = [(source_problem.goal, True, detail["proof_steps"], source_problem.goal)]
        candidates.extend(mixed)
        for _ in range(10):
            if len({candidate[0].txt() for candidate in candidates}) == 4:
                break
            mixed = generate_wrong_answer(
                [(record["goal"], record["proof_steps"])
                 for record in selection["selected_records"][1:]],
                union["displayed_points"])
            candidates = [(source_problem.goal, True, detail["proof_steps"], source_problem.goal)] + mixed
        if len(candidates) != 4:
            return None
        option_points = gc.option_point_names(candidates, set(selection["all_problem_point_names"]))
        if not option_points.issubset(set(union["displayed_points"])):
            return None
        random.shuffle(candidates)
        answer = "".join("ABCD"[index] for index, candidate in enumerate(candidates) if candidate[1])
        draft = {
            "Format": "fast_geochallenge_draft_v2",
            "GeometrySnapshot": capture_graph(graph, original_formal),
            "LayoutOptimization": layout_record,
            "ID": source_problem.url,
            "OriginalFormalText": original_formal,
            "FormalProblemText": detail["problem_content"],
            "Prior_Difficulty": score,
            "Answer": answer,
            "FormalOptions": [{
                "formal": candidate[0].txt(), "is_correct": candidate[1],
                "source_proof": candidate[2], "source_conclusion": candidate[3].txt(),
            } for candidate in candidates],
            "ProofUsedPoints": detail["used_points"],
            "ProofSetupPoints": detail["proof_setup_points"],
            "ProofAuxiliaryPoints": detail["proof_auxiliary_points"],
            "ProofSlicePoints": detail["proof_slice_points"],
            "StructuralPoints": detail["structural_points"],
            "StructuralDependencyPoints": detail["structural_dependency_points"],
            "AuxiliaryPoints": detail["auxiliary_points"],
            "StructuralClauseIndices": detail["structural_clause_indices"],
            "ProofClauseIndices": detail["proof_clause_indices"],
            "AuxiliaryClauseIndices": detail["auxiliary_clause_indices"],
            "AuxiliaryFormalText": detail["auxiliary_formal_text"],
            "AuxiliaryConstructionCount": len(detail["auxiliary_clause_indices"]),
            "NeedsAuxiliaryConstruction": bool(detail["auxiliary_clause_indices"]),
            "OptionSelectionMode": "global_top4",
            "TargetSourceDifficulty": target_record["difficulty"],
            "OptionSourceCandidates": [{
                "rank": i + 1, "formal": record["goal"].txt(),
                "source_difficulty": record["difficulty"],
                "structural_points": record["structural_points"],
                "proof_used_points": record["proof_used_points"],
            } for i, record in enumerate(selection["selected_records"])],
            "OptionUnionStructuralPoints": detail["option_union_structural_points"],
            "OptionUnionClauseIndices": detail["option_union_clause_indices"],
            "OptionPointNames": sorted(option_points),
            "premises": detail["theorem_premises"],
            "ProofSteps": [candidate[2] for candidate in candidates],
            "Stage1Seconds": round(time.perf_counter() - start, 6),
        }
        return draft
    except Exception as error:
        return {"_failure": {"problem_id": source_problem.url, "error_type": type(error).__name__,
                              "error": str(error), "traceback": traceback.format_exc()}}


def process_file(file_path: str) -> dict:
    path = Path(file_path)
    result = {
        "file": path.name,
        "processed": 0,
        "drafted": 0,
        "skipped_existing": 0,
        "failures": [],
    }
    try:
        problems = pr.Problem.from_txt_file(path, to_dict=True, translate=False)
    except Exception as error:
        result["failures"].append({"stage": "read_input", "error": repr(error)})
        return result
    draft_dir = Path(CONFIG["output_dir"]) / "drafts"
    for source_problem in problems.values():
        draft_path = draft_dir / f"{source_problem.url}.json"
        # Reusing an output directory is the normal mode: retain every valid
        # committed draft and compute only missing/corrupt entries.
        if is_complete_draft(draft_path, source_problem.url):
            result["skipped_existing"] += 1
            continue
        result["processed"] += 1
        draft = draft_one(source_problem)
        if draft is None:
            continue
        if "_failure" in draft:
            result["failures"].append(draft["_failure"])
            continue
        atomic_json(draft_path, draft)
        result["drafted"] += 1
    return result


def input_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("problems_*.txt"), key=lambda p: int(p.stem.split("_")[-1]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast DDAR stage: generate GeoChallenge drafts without diagrams.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(os.cpu_count() or 1, 64))
    parser.add_argument("--maxtasksperchild", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2447)
    parser.add_argument("--layout-trials", type=int, default=0,
                        help="Optional phase-1 aesthetic candidates before DDAR; 0 disables layout search")
    parser.add_argument(
        "--resume", action="store_true",
        help="兼容旧命令；输出目录现在默认可续跑，无需指定此参数。")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.maxtasksperchild < 1 or args.layout_trials < 0:
        parser.error("--workers/--maxtasksperchild must be positive and --layout-trials must be nonnegative")
    input_dir, output_dir = args.input_dir.resolve(), args.output_dir.resolve()
    files = input_files(input_dir) if input_dir.is_dir() else []
    if not files:
        parser.error(f"No problems_N.txt in {input_dir}")
    print(json.dumps({"input_files": len(files), "workers": args.workers, "output_dir": str(output_dir)}, ensure_ascii=False))
    if args.dry_run:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "stage1_manifest.json"
    try:
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous_manifest = {}
    try:
        previous_run_count = int(previous_manifest.get("run_count", 0))
    except (TypeError, ValueError):
        previous_run_count = 0
    atomic_json(manifest_path, {
        "format": "fast_geochallenge_draft_v2",
        "created_at": previous_manifest.get("created_at", datetime.now().isoformat(timespec="seconds")),
        "last_started_at": datetime.now().isoformat(timespec="seconds"),
        "run_count": previous_run_count + 1,
        "input_dir": str(input_dir), "workers": args.workers, "seed": args.seed,
        "layout_trials": args.layout_trials,
    })
    config = {"output_dir": str(output_dir), "seed": args.seed, "layout_trials": args.layout_trials}
    failures, processed, drafted, skipped_existing = [], 0, 0, 0
    with Pool(args.workers, initializer=init_worker, initargs=(config,), maxtasksperchild=args.maxtasksperchild) as pool:
        for summary in tqdm(pool.imap_unordered(process_file, map(str, files)), total=len(files), desc="Fast GeoChallenge"):
            processed += summary["processed"]
            drafted += summary["drafted"]
            skipped_existing += summary["skipped_existing"]
            failures.extend(summary["failures"])
    if failures:
        # Keep failures from earlier interrupted invocations for diagnosis.
        with (output_dir / "stage1_failures.jsonl").open("a", encoding="utf-8") as file:
            for failure in failures:
                file.write(json.dumps(failure, ensure_ascii=False) + "\n")
    atomic_json(output_dir / "stage1_summary.json", {
        "processed": processed,
        "drafted": drafted,
        "skipped_existing": skipped_existing,
        "failure_count": len(failures),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    })


if __name__ == "__main__":
    main()
