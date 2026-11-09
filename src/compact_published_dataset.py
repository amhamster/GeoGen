"""Copy an existing dataset to compact JSON+PNG; keep old metadata in audit/."""
import argparse
import json
from pathlib import Path

from prepare_difficulty_dataset import atomic_copy
from publication import atomic_json, compact_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source, output = args.input_dir.resolve(), args.output_dir.resolve()
    if not source.is_dir() or source == output or source in output.parents or output in source.parents:
        parser.error("Input must exist; source and output must be separate, non-nested directories")
    copied = skipped = 0
    for path in sorted(source.rglob("gen_*.json")):
        if any(part in {"drafts", "audit", "validation_failed"} for part in path.relative_to(source).parts[:-1]):
            continue
        image = path.with_suffix(".png")
        if not image.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        compact = compact_payload(payload)
        relative = path.relative_to(source)
        dest_json, dest_png = output / relative, (output / relative).with_suffix(".png")
        if dest_json.exists():
            if json.loads(dest_json.read_text(encoding="utf-8")) != compact:
                parser.error(f"Conflicting output, not overwritten: {dest_json}")
            if dest_png.is_file() and dest_png.stat().st_size == image.stat().st_size:
                skipped += 1
                continue
        if not args.dry_run:
            atomic_json(output / "audit" / relative, payload)
            atomic_copy(image, dest_png)
            atomic_json(dest_json, compact)
        copied += 1
    print(json.dumps({"copied_or_planned": copied, "skipped_existing": skipped, "dry_run": args.dry_run}, ensure_ascii=False))


if __name__ == "__main__":
    main()
