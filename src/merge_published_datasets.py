"""Merge complete GeoGen published-question directories without ID collisions.

Each input may be either a fast run directory (containing ``published/``) or
the ``published`` directory itself.  The output is a flat directory of
``gen_N.json`` / ``gen_N.png`` pairs so existing filtering and JSONL-export
tools can consume it directly.
"""
import argparse
import json
import math
import os
import shutil
import statistics
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from publication import compact_payload


REQUIRED_FIELDS = {"ID", "Question_zh", "Answer", "Prior_Difficulty"}


def numeric_id(path: Path) -> int:
    """Sort conventional gen_N files numerically, with a stable name fallback."""
    stem = path.stem
    try:
        return int(stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 10 ** 30


def resolve_published_dir(source: Path) -> Path:
    """Accept both a run directory and an already-flat publication directory."""
    nested = source / "published"
    if nested.is_dir():
        return nested
    return source


def read_published_pair(json_path: Path) -> tuple[dict, Path] | None:
    """Return a valid payload and matching non-empty PNG, otherwise None."""
    image_path = json_path.with_suffix(".png")
    if not image_path.is_file():
        return None
    try:
        if image_path.stat().st_size == 0:
            return None
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not REQUIRED_FIELDS.issubset(payload):
        return None
    return payload, image_path


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
    """Copy an image without exposing a partially copied final file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp_", suffix=destination.suffix, dir=destination.parent)
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


def source_key(source_dir: Path, source_id: str) -> tuple[str, str]:
    return str(source_dir.resolve()), source_id


def load_existing_output(output_dir: Path) -> tuple[set[tuple[str, str]], set[int], int]:
    """Find resumable source mappings and never reuse an occupied number."""
    merged_sources: set[tuple[str, str]] = set()
    occupied_ids: set[int] = set()
    for json_path in output_dir.glob("gen_*.json"):
        identifier = numeric_id(json_path)
        if identifier < 10 ** 30:
            occupied_ids.add(identifier)
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            provenance = payload.get("MergeProvenance", {})
            if not provenance:
                audit_path = output_dir / "audit" / json_path.name
                if audit_path.is_file():
                    provenance = json.loads(audit_path.read_text(encoding="utf-8")).get("MergeProvenance", {})
            source_dir = provenance.get("source_published_dir")
            source_id = provenance.get("source_id")
            if isinstance(source_dir, str) and isinstance(source_id, str):
                merged_sources.add((source_dir, source_id))
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
    next_id = max(occupied_ids, default=-1) + 1
    return merged_sources, occupied_ids, next_id


def next_available_id(next_id: int, occupied_ids: set[int]) -> int:
    while next_id in occupied_ids:
        next_id += 1
    return next_id


def difficulty_value(payload: dict) -> float | None:
    value = payload.get("Prior_Difficulty")
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def distribution(values: list[float], bin_width: int) -> dict:
    if not values:
        return {"valid_count": 0, "invalid_or_missing_count": 0, "bins": {}}
    bins: Counter[str] = Counter()
    for value in values:
        lower = math.floor(value / bin_width) * bin_width
        upper = lower + bin_width
        bins[f"[{lower:g}, {upper:g})"] += 1
    return {
        "valid_count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.fmean(values), 6),
        "median": statistics.median(values),
        "bin_width": bin_width,
        "bins": dict(sorted(bins.items(), key=lambda item: float(item[0].split(",", 1)[0][1:]))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="汇总多个已发布 GeoGen 数据集，重新编号并输出难度分布。")
    parser.add_argument("--input-dir", type=Path, action="append", required=True,
                        help="输入运行目录或其 published 子目录；可重复指定，顺序决定默认编号顺序")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="合并后的平铺 gen_N.json / gen_N.png 输出目录")
    parser.add_argument("--start-index", type=int, default=0,
                        help="新编号起点；已有输出会自动从最大已有编号之后继续")
    parser.add_argument("--sort-by", choices=("source", "difficulty_asc", "difficulty_desc"), default="source",
                        help="source 保持输入目录与原编号顺序；也可按 Prior_Difficulty 排序")
    parser.add_argument("--bin-width", type=int, default=10,
                        help="难度分布的区间宽度，默认 10")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.start_index < 0 or args.bin_width < 1:
        parser.error("--start-index 必须非负，--bin-width 必须为正")

    output_dir = args.output_dir.resolve()
    sources = []
    for source_order, input_dir in enumerate(args.input_dir):
        published_dir = resolve_published_dir(input_dir.resolve())
        if not published_dir.is_dir():
            parser.error(f"发布目录不存在：{published_dir}")
        sources.append((source_order, published_dir))

    existing_sources, occupied_ids, existing_next_id = load_existing_output(output_dir) if output_dir.is_dir() else (set(), set(), args.start_index)
    start_id = max(args.start_index, existing_next_id)
    candidates = []
    skipped_missing_pair = []
    skipped_existing = []
    seen_source_keys = set(existing_sources)
    for source_order, published_dir in sources:
        for json_path in sorted(published_dir.glob("gen_*.json"), key=lambda item: (numeric_id(item), item.name)):
            pair = read_published_pair(json_path)
            if pair is None:
                skipped_missing_pair.append({"source_published_dir": str(published_dir), "file": json_path.name})
                continue
            payload, image_path = pair
            key = source_key(published_dir, str(payload["ID"]))
            if key in seen_source_keys:
                skipped_existing.append({"source_published_dir": key[0], "source_id": key[1]})
                continue
            seen_source_keys.add(key)
            candidates.append({
                "source_order": source_order,
                "source_dir": published_dir,
                "source_json": json_path,
                "source_png": image_path,
                "payload": payload,
                "difficulty": difficulty_value(payload),
            })

    if args.sort_by == "difficulty_asc":
        candidates.sort(key=lambda item: (item["difficulty"] is None, item["difficulty"], item["source_order"], numeric_id(item["source_json"])))
    elif args.sort_by == "difficulty_desc":
        candidates.sort(key=lambda item: (item["difficulty"] is None,
                                          -(item["difficulty"] or 0), item["source_order"], numeric_id(item["source_json"])))

    summary_before = {
        "input_published_dirs": [str(published_dir) for _, published_dir in sources],
        "existing_merged_questions": len(existing_sources),
        "candidates": len(candidates),
        "skipped_existing": len(skipped_existing),
        "skipped_missing_or_invalid_pair": len(skipped_missing_pair),
        "output_dir": str(output_dir),
        "start_index": start_id,
        "sort_by": args.sort_by,
    }
    print(json.dumps(summary_before, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "merge_manifest.jsonl"
    merged = []
    next_id = start_id
    for item in candidates:
        new_id = next_available_id(next_id, occupied_ids)
        new_name = f"gen_{new_id}"
        payload = dict(item["payload"])
        old_id = str(payload["ID"])
        payload["ID"] = new_name
        provenance = {
            "source_published_dir": str(item["source_dir"]),
            "source_json": item["source_json"].name,
            "source_png": item["source_png"].name,
            "source_id": old_id,
            "merged_at": datetime.now().isoformat(timespec="seconds"),
        }
        destination_json = output_dir / f"{new_name}.json"
        destination_png = output_dir / f"{new_name}.png"
        # IDs are selected from the occupied set before either file is written;
        # a merge never replaces a different existing question.
        atomic_copy(item["source_png"], destination_png)
        # Keep provenance outside the public question, but commit it before
        # JSON so interrupted merges can resume without duplicating sources.
        atomic_json(output_dir / "audit" / destination_json.name,
                    {"ID": new_name, "MergeProvenance": provenance})
        atomic_json(destination_json, compact_payload(payload))
        entry = {
            "merged_id": new_name,
            **provenance,
            "Prior_Difficulty": item["difficulty"],
        }
        merged.append(entry)
        occupied_ids.add(new_id)
        next_id = new_id + 1

    with manifest_path.open("a", encoding="utf-8") as file:
        for entry in merged:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    values = []
    invalid_difficulty_count = 0
    for json_path in output_dir.glob("gen_*.json"):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid_difficulty_count += 1
            continue
        value = difficulty_value(payload)
        if value is None:
            invalid_difficulty_count += 1
        else:
            values.append(value)
    difficulty_summary = distribution(values, args.bin_width)
    difficulty_summary["invalid_or_missing_count"] = invalid_difficulty_count
    atomic_json(output_dir / "difficulty_distribution.json", difficulty_summary)
    atomic_json(output_dir / "merge_summary.json", {
        **summary_before,
        "merged_this_run": len(merged),
        "total_merged_questions": len(values) + invalid_difficulty_count,
        "difficulty_distribution_file": "difficulty_distribution.json",
        "manifest_file": "merge_manifest.jsonl",
        "skipped_missing_or_invalid_pairs": skipped_missing_pair,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    })
    print(json.dumps({
        "merged_this_run": len(merged),
        "total_merged_questions": len(values) + invalid_difficulty_count,
        "difficulty_distribution": difficulty_summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
