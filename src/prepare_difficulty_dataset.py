"""Create difficulty reference samples and a complete three-level GeoGen dataset.

Reference samples are for manual difficulty calibration only.  They are copied
first but intentionally remain in the complete ``Geo`` split as well.
"""
import argparse
import json
import math
import os
import random
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def difficulty_levels(low, high):
    return (("简单", "easy", lambda score: score < low),
            ("中等", "medium", lambda score: low <= score < high),
            ("困难", "hard", lambda score: score >= high))


def boundary_descriptions(low, high):
    return {"简单": f"Prior_Difficulty < {low:g}",
            "中等": f"{low:g} <= Prior_Difficulty < {high:g}",
            "困难": f"Prior_Difficulty >= {high:g}"}


LEVELS = difficulty_levels(70, 90)
BOUNDARIES = boundary_descriptions(70, 90)
REQUIRED_FIELDS = {"ID", "Question_zh", "Answer", "Prior_Difficulty"}


def numeric_id(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 10 ** 30


def read_pair(json_path: Path) -> tuple[str, Path, float] | None:
    """Return only lightweight metadata for a complete published question pair."""
    png_path = json_path.with_suffix(".png")
    try:
        if not png_path.is_file() or png_path.stat().st_size == 0:
            return None
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not REQUIRED_FIELDS.issubset(payload):
            return None
        difficulty = float(payload["Prior_Difficulty"])
        if not math.isfinite(difficulty):
            return None
        return str(payload["ID"]), png_path, difficulty
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def level_for(difficulty: float) -> tuple[str, str]:
    for directory_name, key, predicate in LEVELS:
        if predicate(difficulty):
            return directory_name, key
    raise ValueError(f"Unexpected difficulty: {difficulty}")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp_", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
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


def atomic_copy(source: Path, destination: Path) -> None:
    """Copy a file without exposing a partially copied destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".tmp_", suffix=destination.suffix, dir=destination.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        shutil.copy2(source, temporary_path)
        os.replace(temporary_path, destination)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def copy_pair(item: dict, destination_dir: Path) -> bool:
    """Copy one question pair; return True only when a new copy was made."""
    name = item["json_path"].name
    destination_json = destination_dir / name
    destination_png = destination_dir / item["png_path"].name
    if destination_json.is_file() and destination_png.is_file() and destination_png.stat().st_size > 0:
        return False
    # PNG first: an interruption cannot leave a complete-looking JSON without
    # its image. Both source files were validated during the lightweight scan.
    atomic_copy(item["png_path"], destination_png)
    atomic_copy(item["json_path"], destination_json)
    return True


def select_references(items_by_level: dict[str, list[dict]], selection_path: Path,
                      seed: int, count: int) -> dict[str, list[str]]:
    """Create once, then reuse exactly the same manual reference set on reruns."""
    if selection_path.is_file():
        try:
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            if (selection.get("difficulty_boundaries") != BOUNDARIES
                    or selection.get("reference_count_per_level") != count):
                raise ValueError("Existing reference selection has different boundaries/count; use a new reference directory")
            selected = selection["selected_ids"]
            if all(isinstance(selected.get(key), list) for _, key, _ in LEVELS):
                return selected
        except (OSError, json.JSONDecodeError, KeyError, AttributeError):
            pass
    rng = random.Random(seed)
    selected = {}
    for _, key, _ in LEVELS:
        items = items_by_level[key]
        if len(items) < count:
            raise ValueError(f"{key} only has {len(items)} valid questions; cannot sample {count}")
        selected[key] = sorted(rng.sample([item["id"] for item in items], count),
                               key=lambda identifier: int(identifier.rsplit("_", 1)[1]))
    atomic_json(selection_path, {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "reference_count_per_level": count,
        "difficulty_boundaries": BOUNDARIES,
        "selected_ids": selected,
    })
    return selected


def main() -> None:
    global LEVELS, BOUNDARIES
    parser = argparse.ArgumentParser(
        description="先抽取难度参考样本，再将完整 GeoGen 数据按简单/中等/困难复制到三个子目录。")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="平铺的 merged 数据目录，含 gen_N.json 和同名 PNG")
    parser.add_argument("--reference-dir", type=Path, required=True,
                        help="每档随机难度参考样本的输出目录")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="完整三档数据集输出目录；会创建 简单/中等/困难 子目录")
    parser.add_argument("--reference-count", type=int, default=100,
                        help="每档参考样本数量，默认 100")
    parser.add_argument("--easy-upper", type=float, default=70)
    parser.add_argument("--medium-upper", type=float, default=90)
    parser.add_argument("--seed", type=int, default=2447,
                        help="首次抽样的固定随机种子")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.easy_upper) or not math.isfinite(args.medium_upper) or args.easy_upper >= args.medium_upper:
        parser.error("Difficulty boundaries must be finite and easy-upper < medium-upper")
    LEVELS = difficulty_levels(args.easy_upper, args.medium_upper)
    BOUNDARIES = boundary_descriptions(args.easy_upper, args.medium_upper)
    if args.reference_count < 1:
        parser.error("--reference-count must be positive")

    input_dir = args.input_dir.resolve()
    reference_dir = args.reference_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        parser.error(f"Input directory does not exist: {input_dir}")
    if input_dir == reference_dir or input_dir == output_dir or reference_dir == output_dir:
        parser.error("--input-dir、--reference-dir、--output-dir 必须是三个不同目录")

    items_by_level = {key: [] for _, key, _ in LEVELS}
    invalid_pairs = []
    for json_path in sorted(input_dir.glob("gen_*.json"), key=lambda item: (numeric_id(item), item.name)):
        pair = read_pair(json_path)
        if pair is None:
            invalid_pairs.append(json_path.name)
            continue
        identifier, png_path, difficulty = pair
        directory_name, key = level_for(difficulty)
        items_by_level[key].append({
            "id": identifier,
            "json_path": json_path,
            "png_path": png_path,
            "difficulty": difficulty,
            "directory_name": directory_name,
        })
    total = sum(len(items) for items in items_by_level.values())
    counts = {key: len(items_by_level[key]) for _, key, _ in LEVELS}
    print(json.dumps({
        "input_valid_pairs": total,
        "invalid_or_incomplete_pairs": len(invalid_pairs),
        "difficulty_counts": counts,
        "reference_count_per_level": args.reference_count,
    }, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    reference_dir.mkdir(parents=True, exist_ok=True)
    selection_path = reference_dir / "difficulty_reference_selection.json"
    selected_ids = select_references(items_by_level, selection_path, args.seed, args.reference_count)
    item_by_id = {
        key: {item["id"]: item for item in items}
        for key, items in items_by_level.items()
    }
    reference_copied = {key: 0 for _, key, _ in LEVELS}
    # This precedes the complete split by design: these copies are the stable
    # manual calibration material, not a held-out test set.
    for directory_name, key, _ in LEVELS:
        for identifier in selected_ids[key]:
            try:
                item = item_by_id[key][identifier]
            except KeyError as error:
                raise ValueError(f"Reference selection contains unavailable {key} question: {identifier}") from error
            reference_copied[key] += copy_pair(item, reference_dir / directory_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    split_copied = {key: 0 for _, key, _ in LEVELS}
    for directory_name, key, _ in LEVELS:
        for item in items_by_level[key]:
            split_copied[key] += copy_pair(item, output_dir / directory_name)

    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "reference_dir": str(reference_dir),
        "output_dir": str(output_dir),
        "difficulty_boundaries": BOUNDARIES,
        "total_valid_pairs": total,
        "difficulty_counts": counts,
        "invalid_or_incomplete_pairs": invalid_pairs,
        "reference_count_per_level": args.reference_count,
        "reference_selection_file": selection_path.name,
        "reference_copied_this_run": reference_copied,
        "complete_split_copied_this_run": split_copied,
        "reference_samples_are_also_in_complete_split": True,
    }
    atomic_json(output_dir / "difficulty_split_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
