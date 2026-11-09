"""Small public question schema; diagnostics stay in drafts/ and audit/."""
import json
import os
from pathlib import Path
import tempfile


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp_", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def compact_payload(payload):
    from export_problem_jsonl import translate_auxiliary_formal_text
    required = ["ID", "Question_zh", "A_zh", "B_zh", "C_zh", "D_zh", "Answer", "Prior_Difficulty"]
    output = {key: payload[key] for key in required}
    output["SimplifiedFormalText"] = payload.get("SimplifiedFormalText", "")
    auxiliary = payload.get("AuxiliaryFormalText", "") or ""
    output["AuxiliaryFormalText"] = auxiliary
    output["Auxiliary_zh"] = payload.get("Auxiliary_zh") or translate_auxiliary_formal_text(auxiliary)
    # Every option retains its source-conclusion proof, including changed options.
    for letter in "ABCD":
        output[f"ProofSteps_{letter}"] = payload.get(f"ProofSteps_{letter}", "")
    return output
