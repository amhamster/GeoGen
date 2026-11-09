"""Export generated GeoGen questions into a JSONL dataset.

Example:
    conda run -n geogen python src/export_problem_jsonl.py \
        problems/20260928_14_27_56

The output defaults to ``translated_questions.jsonl`` in the input directory.
The canonical generated JSON is never modified.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import problem as pr
from display_rewrite import build_display_rewrite_plan
from translation import translate_problem_to_natural_language


OPTION_LETTERS = ("A", "B", "C", "D")


def _json_sort_key(path: Path) -> tuple[int, str]:
    """Sort ``gen_12`` before ``gen_100`` while retaining a stable fallback."""
    match = re.search(r"(\d+)$", path.stem)
    return (int(match.group(1)) if match else sys.maxsize, path.stem)


def _all_point_names(problem: pr.Problem) -> list[str]:
    """Return enough point names for natural-language translation of a slice."""
    names = set()
    for clause in problem.clauses:
        names.update(clause.points)
        for construction in clause.constructions:
            names.update(arg for arg in construction.args if arg.isalpha())
    return sorted(names)


def translate_auxiliary_formal_text(formal_text: str) -> str:
    """Translate an auxiliary-construction slice without rebuilding geometry."""
    if not formal_text or not formal_text.strip():
        return "无需额外辅助线。"

    try:
        auxiliary_problem = pr.Problem.from_txt(formal_text, translate=False)
        display_plan = build_display_rewrite_plan(auxiliary_problem)
        text = translate_problem_to_natural_language(
            display_plan.display_problem,
            "zh",
            _all_point_names(display_plan.display_problem),
        )
    except (ValueError, IndexError, KeyError) as error:
        return f"辅助线描述翻译失败（{error}）"

    return text or "无需额外辅助线。"


def build_option_proofs(
        payload: dict,
        include_source_proof_for_wrong_options: bool,
) -> list[dict]:
    """Export every option's source proof, independent of its answer label.

    The compatibility argument no longer filters false options. A source
    proof establishes the original conclusion before any option mutation.
    """
    answer = str(payload.get("Answer", ""))
    exported = []
    for letter in OPTION_LETTERS:
        is_correct = letter in answer
        source_proof = payload.get(f"ProofSteps_{letter}", "")
        item = {
            "题号": letter,
            "结论": payload.get(f"{letter}_zh", ""),
            "是否正确": is_correct,
            "证明": source_proof,
            "证明状态": "生成时来源结论的证明",
        }
        exported.append(item)
    return exported


def export_question_folder(
        input_dir: Path,
        output_path: Path,
        recursive: bool,
        include_source_proof_for_wrong_options: bool,
) -> tuple[int, int]:
    """Write one JSON object per regular generated question and return counts."""
    paths = input_dir.rglob("*.json") if recursive else input_dir.glob("*.json")
    json_paths = sorted(paths, key=_json_sort_key)
    written = 0
    skipped = 0

    with output_path.open("w", encoding="utf-8") as output_file:
        for path in json_paths:
            # Avoid treating the newly written JSONL (or non-JSON files) as
            # input when a caller chooses an unusual extension.
            if path.resolve() == output_path.resolve():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                print(f"skip unreadable JSON: {path} ({error})", file=sys.stderr)
                skipped += 1
                continue

            question = payload.get("Question_zh")
            if not question:
                print(f"skip non-published question JSON: {path}", file=sys.stderr)
                skipped += 1
                continue

            auxiliary_formal = (
                payload.get("SuggestedAuxiliaryFormalText")
                or payload.get("AuxiliaryFormalText")
                or ""
            )
            needs_auxiliary = bool(payload.get("NeedsAuxiliaryConstruction", auxiliary_formal))
            if not needs_auxiliary:
                auxiliary_formal = ""

            record = {
                "题目序号": written + 1,
                "题目ID": payload.get("ID", path.stem),
                "题图文件名": path.with_suffix(".png").name,
                "题目描述": question,
                "辅助线描述": payload.get("Auxiliary_zh") or translate_auxiliary_formal_text(auxiliary_formal),
                "是否需要辅助线": needs_auxiliary,
                "难度": payload.get("Prior_Difficulty"),
                "正确答案": payload.get("Answer", ""),
                "各问证明": build_option_proofs(
                    payload, include_source_proof_for_wrong_options),
            }
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    return written, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将一个 GeoGen 生成题目目录导出为含中文题干、辅助线和证明的 JSONL。")
    parser.add_argument("input_dir", type=Path, help="生成题目的目录，例如 problems/20260928_14_27_56")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 JSONL 路径；默认为 <input_dir>/translated_questions.jsonl",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="递归读取子目录；默认只读取目录直属 JSON，避免混入 validation_failed。",
    )
    parser.add_argument(
        "--include-source-proof-for-wrong-options",
        action="store_true",
        help="兼容旧命令；当前默认保留全部选项的来源证明，无需指定。",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        parser.error(f"输入目录不存在：{args.input_dir}")

    output_path = args.output or args.input_dir / "translated_questions.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written, skipped = export_question_folder(
        args.input_dir,
        output_path,
        args.recursive,
        args.include_source_proof_for_wrong_options,
    )
    print(f"已写入 {written} 题到 {output_path}；跳过 {skipped} 个文件。")


if __name__ == "__main__":
    main()
