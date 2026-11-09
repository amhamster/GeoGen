"""Copy generated GeoGen questions above a difficulty threshold to a new folder.

Examples:
    conda run -n geogen python src/filter_problems_by_difficulty.py \
        problems/20261011_15_44_49 --min-difficulty 60

    conda run -n geogen python src/filter_problems_by_difficulty.py \
        problems/20261011_15_44_49 --min-difficulty 60 \
        --output-dir problems/20261011_15_44_49_difficulty_gt_60 \

Only direct ``gen_*.json`` files are treated as generated questions.  Each
selected JSON and its same-stem PNG are copied without changing their names.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable


def _question_sort_key(path: Path) -> tuple[int, str]:
    """Order gen_9 before gen_100, with a deterministic fallback."""
    suffix = path.stem.removeprefix("gen_")
    return (int(suffix), path.name) if suffix.isdigit() else (sys.maxsize, path.name)


def _difficulty(payload: dict[str, Any]) -> float | None:
    """Return a finite numeric Prior_Difficulty, or None for unusable input."""
    value = payload.get("Prior_Difficulty")
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _default_output_dir(input_dir: Path, threshold: float, inclusive: bool) -> Path:
    comparator = "ge" if inclusive else "gt"
    threshold_text = format(threshold, "g").replace("-", "neg_").replace(".", "_")
    return input_dir.parent / f"{input_dir.name}_difficulty_{comparator}_{threshold_text}"


def _eligible(difficulty: float, threshold: float, inclusive: bool) -> bool:
    return difficulty >= threshold if inclusive else difficulty > threshold


def select_questions(
        input_dir: Path,
        threshold: float,
        inclusive: bool,
) -> tuple[list[tuple[Path, dict[str, Any], float]], dict[str, Any]]:
    """Read direct generated-question JSONs and return the selected records."""
    selected: list[tuple[Path, dict[str, Any], float]] = []
    stats: dict[str, Any] = {
        "source_question_json_count": 0,
        "invalid_json_files": [],
        "missing_or_invalid_difficulty_files": [],
    }
    for json_path in sorted(input_dir.glob("gen_*.json"), key=_question_sort_key):
        stats["source_question_json_count"] += 1
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            stats["invalid_json_files"].append({"file": json_path.name, "error": str(error)})
            continue
        if not isinstance(payload, dict):
            stats["invalid_json_files"].append({"file": json_path.name, "error": "JSON root is not an object"})
            continue
        difficulty = _difficulty(payload)
        if difficulty is None:
            stats["missing_or_invalid_difficulty_files"].append(json_path.name)
            continue
        if _eligible(difficulty, threshold, inclusive):
            selected.append((json_path, payload, difficulty))
    return selected, stats


def _prepare_output_dir(output_dir: Path, input_dir: Path) -> None:
    if output_dir == input_dir:
        raise ValueError("输出目录不能与输入目录相同")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"输出目录非空，拒绝覆盖：{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, content: Any) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_selected_questions(
        selected: Iterable[tuple[Path, dict[str, Any], float]],
        input_dir: Path,
        output_dir: Path,
        threshold: float,
        inclusive: bool,
        stats: dict[str, Any],
) -> dict[str, Any]:
    """Copy JSON/PNG pairs and return a machine-readable selection summary."""
    selected_list = list(selected)
    missing_images: list[str] = []
    manifest_path = output_dir / "selection_manifest.jsonl"

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for index, (json_path, payload, difficulty) in enumerate(selected_list, 1):
            image_path = json_path.with_suffix(".png")
            shutil.copy2(json_path, output_dir / json_path.name)
            image_copied = image_path.is_file()
            if image_copied:
                shutil.copy2(image_path, output_dir / image_path.name)
            else:
                missing_images.append(image_path.name)
            manifest.write(json.dumps({
                "筛选后序号": index,
                "题目ID": payload.get("ID", json_path.stem),
                "原文件": json_path.name,
                "Prior_Difficulty": difficulty,
                "题图文件": image_path.name,
                "题图已复制": image_copied,
            }, ensure_ascii=False) + "\n")

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "difficulty_field": "Prior_Difficulty",
        "comparison": ">=" if inclusive else ">",
        "threshold": threshold,
        **stats,
        "selected_question_count": len(selected_list),
        "copied_image_count": len(selected_list) - len(missing_images),
        "missing_image_files": missing_images,
        "manifest": manifest_path.name,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="筛选 Prior_Difficulty 超过阈值的 GeoGen 题目，并复制 JSON 与同名 PNG 到新目录。")
    parser.add_argument("input_dir", type=Path, help="题目目录，例如 problems/20261011_15_44_49")
    parser.add_argument("--min-difficulty", type=float, required=True,
                        help="难度阈值；默认仅保留 Prior_Difficulty 严格大于该值的题目")
    parser.add_argument("--inclusive", action="store_true",
                        help="改为保留难度大于或等于阈值的题目")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="新目录；默认是输入目录同级的 <名称>_difficulty_gt_<阈值>")
    parser.add_argument("--dry-run", action="store_true",
                        help="只统计和打印筛选结果，不创建或复制文件")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        parser.error(f"输入目录不存在：{input_dir}")
    if not math.isfinite(args.min_difficulty):
        parser.error("--min-difficulty 必须是有限数字")

    output_dir = (args.output_dir.resolve() if args.output_dir else
                  _default_output_dir(input_dir, args.min_difficulty, args.inclusive).resolve())
    selected, stats = select_questions(input_dir, args.min_difficulty, args.inclusive)
    result = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "comparison": ">=" if args.inclusive else ">",
        "threshold": args.min_difficulty,
        **stats,
        "selected_question_count": len(selected),
    }
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    try:
        _prepare_output_dir(output_dir, input_dir)
        result = copy_selected_questions(
            selected, input_dir, output_dir, args.min_difficulty,
            args.inclusive, stats)
        _write_json(output_dir / "selection_summary.json", result)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"筛选失败：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
