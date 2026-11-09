import traceback
import problem as pr
import random
import copy
import graph as gh
from tqdm import tqdm

import itertools
import pretty as pt
import matplotlib.pyplot as plt
from absl import app
from absl import flags
from absl import logging
import os
import shutil
import ast
import json
import tempfile
import structure_templates as st
from typing import Optional


import _paths
DEFS_FILE_PATH = _paths.DEFS_PATH
STRUCTURE_TEMPLATES_FILE_PATH = _paths.STRUCTURE_TEMPLATES_PATH
CACHE_PATH = os.path.join(_paths.PROJECT_ROOT, 'problems', 'generate_cache')
OUTPUT_FILE_PATH = os.path.join(_paths.PROJECT_ROOT, 'problems', 'problems') + '/'
DEFAULT_OUTPUT_FILE_PATH = OUTPUT_FILE_PATH
ALPHABET_DICT = [chr(char) for char in range(ord('a'), ord('z') + 1)]
CHUNK_SIZE = 10

FLAGS = flags.FLAGS
flags.DEFINE_enum(
    "run_mode", "resume", ["new", "resume", "finalize", "validate"],
    "new: start an empty cache; resume: continue BFS; finalize: export an existing cache depth; validate: inspect a completed cache depth.")
flags.DEFINE_string("run_dir", CACHE_PATH, "Cache directory to validate, resume, or create.")
flags.DEFINE_string("output_dir", OUTPUT_FILE_PATH, "Directory for exported raw premise files.")
flags.DEFINE_integer(
    "target_depth", 6,
    "Inclusive final depth (target_depth=8 produces depth_0 through depth_8).")
flags.DEFINE_integer(
    "assume_complete_depth", -1,
    "Trust this existing depth as complete without validation; resume rebuilds later incomplete depths from it.")
flags.DEFINE_integer(
    "export_depth", -1,
    "Depth to export in finalize/validate mode; finalize with -1 selects the deepest existing depth.")

# Initial roots are deliberately kept separate from the dependent-construction
# BFS below.  ``mixed`` makes the generator cover both curated competition
# structures and basic figures, while the other modes remain useful for
# controlled comparisons.
INITIAL_SEED_MODE = "mixed"
INITIAL_SEED_MODES = {"templates_only", "simple_only", "mixed"}
SIMPLE_INITIAL_CONSTRUCTIONS = (
    "eq_quadrangle",
    "eq_trapezoid",
    "eqdia_quadrangle",
    "ieq_triangle",
    "iso_triangle",
    "isquare",
    "r_trapezoid",
    "r_triangle",
    "rectangle",
    "risos",
    "segment",
    "trapezoid",
    "triangle",
)


def random_sample(input_list: list, select_count: int) -> list:
    """
    Randomly select select_count elements from the input_list, -1 for all elements

    Examples:
        input_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        select_count = 2
        return = ['d', 'b']
    """
    if select_count <= 0:
        return input_list
    actual_count = min(select_count, len(input_list))
    return random.sample(input_list, actual_count)


def select_unused_args(alphabet: list, select_count: int, strategy: str = "order") -> list:
    """
    Select select_count unused letters from the alphabet, "order" for alphabetic order, "random" for random select

    Examples:
        alphabet = [True, True, True, True, True, False, False, False, False, False, False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False]
        select_count = 1
        strategy = "order"

        return 1 = ['f']
        return 2 = [True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    """
    unused_indexes = [index for index,
                      value in enumerate(alphabet) if not value]
    new_alphabet = copy.deepcopy(alphabet)

    # Check if the length of unused_indexes is sufficient
    if len(unused_indexes) < select_count:
        return None, None

    if strategy == 'order':
        # select in alphabetic order
        start = alphabet.index(False)
        selected_indexes = [idx for idx in range(start, start+select_count)]
        for idx in selected_indexes:
            new_alphabet[idx] = True
    elif strategy == 'random':
        # select randomly
        selected_indexes = random_sample(unused_indexes, select_count)
        for idx in selected_indexes:
            new_alphabet[idx] = True
    else:
        raise ValueError("unknown select strategy at select_unused_args")

    return [ALPHABET_DICT[idx] for idx in selected_indexes], new_alphabet


def select_args_permutations(alphabet: list, permutation_length: int, select_count: int) -> list:
    """
    Select select_count permutations in alphabet with a length of permeation_length

    Examples:
        alphabet = [True, True, True, True, False, False, False, False, False, False, False, False, False,
            False, False, False, False, False, False, False, False, False, False, False, False, False]
        permutation_length = 2
        select_count = 3

        return = [('a', 'c'), ('d', 'b'), ('c', 'd')]
    """
    exist_letter = [ALPHABET_DICT[index]
                    for index, value in enumerate(alphabet) if value]
    if len(exist_letter) < permutation_length:
        return None

    all_permutations = list(itertools.permutations(
        exist_letter, permutation_length))
    return random_sample(all_permutations, select_count)


def combine_args_name(base_args: list, new_args: list, exist_args: list, new_args_name: list, exist_args_name: list) -> list:
    """
    Combine args by rule

    Examples:
        base_args = ['x', 'y', 'a', 'o', 'b']
        new_args = ['x', 'y']
        exist_args = ['a', 'o', 'b']
        new_args_name = ['h', 'i']
        exist_args_name = ('f', 'e', 'a')

        return = ['h', 'i', 'f', 'e', 'a']
    """
    args_name = []
    for arg in base_args:
        arg_name = None
        if arg in new_args:
            arg_name = new_args_name[new_args.index(arg)]
        elif arg in exist_args:
            arg_name = exist_args_name[exist_args.index(arg)]
        else:
            raise ValueError(
                "args not match, please make sure that base_args = new_args + exist_args")
        args_name.append(arg_name)
    assert len(args_name) == len(base_args)

    return args_name


def init_defs(defs_file: str = DEFS_FILE_PATH):
    """
    Read definitions from files, default to "./defs.txt"

    Examples:
        defs_file = _paths.DEFS_PATH

        return = ['h', 'i', 'f', 'e', 'a']
    """

    # definitions of terms used in our domain-specific language.
    DEFINITIONS = pr.Definition.from_txt_file(defs_file, to_dict=True)
    INDEPENDENT_CONSTRUCTION = {}
    DEPENDENT_CONSTRUCTION = {}
    for name, cdef in DEFINITIONS.items():
        cons_args = cdef.construction.args
        basic_args = list(map(lambda x: x[0], cdef.basics))
        basic_args = sum([args for args in basic_args if args], [])
        # logging.info(f"cons_args {cons_args} basic_args{basic_args}")
        if len(cons_args) == len(basic_args):
            INDEPENDENT_CONSTRUCTION[name] = cdef
        else:
            DEPENDENT_CONSTRUCTION[name] = cdef
    # logging.info(INDEPENDENT_CONSTRUCTION.keys())
    # logging.info(DEPENDENT_CONSTRUCTION_CONSTRUCTION.keys())

    independent_constructions_name = list(INDEPENDENT_CONSTRUCTION.keys())
    dependent_constructions_name = list(DEPENDENT_CONSTRUCTION.keys())
    # some constructions can be used to create like: a = f(), g()
    dependent_non_unique_constructions_name = [
        "angle_bisector",
        "eqdistance",
        "on_bline",
        "on_circle",
        "on_circum",
        "on_dia",
        "on_line",
        "on_pline",
        "on_tline",
        "s_angle"
    ]
    # exclude_constructions = ['e5128', 'trisect', 'trisegment', 'cc_tangent0', 'tangent', '3peq', 'incenter2', 'excenter2', 'centroid', 'ninepoints', '2l1c', 'cc_tangent', 'on_aline2',
    #                      'pentagon', 'free', 'quadrangle', 'triangle12', 's_angle', 'on_circum', 'intersection_pp', 'intersection_ll', 'intersection_lp', 'intersection_lt']
    exclude_constructions = ['circumcenter', 'on_opline', 'psquare', 'intersection_cc', '2l1c', 'e5128', 'free',
                             '3peq', 'pentagon', 'triangle12', 'quadrangle', 'cc_tangent', 'trisect', 'trisegment', 'incenter2', 'excenter2', 'cc_tangent0', 'on_aline2']
    # repeated：circumcenter, on_opline, psquare, intersection_cc
    # unkown：2l1c, e5128,
    # no conclusion contribution：free, 3peq, pentagon, triangle12, quadrangle, cc_tangent
    # drawing error：trisect, trisegment, incenter2, excenter2
    # build problem error：cc_tangent0, on_aline2
    independent_constructions = [
        i for i in independent_constructions_name if i not in exclude_constructions]
    dependent_constructions = [
        i for i in dependent_constructions_name if i not in exclude_constructions]
    dependent_non_unique_constructions = [
        i for i in dependent_constructions if i in dependent_non_unique_constructions_name]

    return DEFINITIONS, independent_constructions, dependent_constructions, dependent_non_unique_constructions


def generate_constructions(name2: str, this_construction: pr.Definition, a: list, expand_args: int):
    """
    Generate expand_args constructions from the given alphabet a. If name2 is "s_angle", add angle value

    Examples:
        name2 = "orthocenter"
        this_construction = pr.Definition called orthocenter
        a = [True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
        expand_args = 2

        return = [
        (['g'],['g', 'c', 'd', 'b'],[True, True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]),
        (['g'],['g', 'e', 'b', 'a'],[True, True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False])
        ]
    """
    all_args = this_construction.construction.args

    # Construct new points and name them
    new_args = [arg for arg in sum(
        map(lambda x: x[0], this_construction.basics), []) if arg]
    new_args_name, new_alphabet = select_unused_args(
        a, len(new_args))

    # A deep BFS branch can already consume all 26 point names.  In that
    # case ``select_unused_args`` deliberately returns ``(None, None)``;
    # there is no valid instantiation of a construction that introduces new
    # points, so this branch must simply contribute no children.  Previously
    # it reached ``combine_args_name`` and indexed ``None``.
    if new_args_name is None:
        return []

    # find exist args
    exist_args = list(
        filter(lambda x: x not in new_args, all_args))
    exist_args_namelist = select_args_permutations(
        a, len(exist_args), expand_args)

    if exist_args_namelist is None:
        return None, None, None

    constructions_list = []

    for exist_args_name in exist_args_namelist:
        all_args_name = None
        # get new name
        # numeric!!
        if name2 == "s_angle":
            all_args_name = combine_args_name(
                all_args, new_args, exist_args, new_args_name, exist_args_name[:-1] + (random.choice(['30', '45', '60']),))
        else:
            all_args_name = combine_args_name(
                all_args, new_args, exist_args, new_args_name, exist_args_name)

        constructions_list.append((new_args_name, all_args_name, new_alphabet))

    return constructions_list


def save_list_to_txt(
        problem_list: list[list[tuple]],
        alphabet_list: list[bool],
        depth: int,
        file_idx: int,
        source_list: Optional[list[str]] = None,
):
    """
    save problem and alphabet list to f'{CACHE_PATH}/depth_{depth-1}'

    Examples:
        problem_list = [[(['a', 'b', 'c'], 'triangle', ['a', 'b', 'c']), (['d'], 'on_pline', ['d', 'a', 'b', 'c'], 'on_circle', ['d', 'b', 'a'])],
                        [(['a', 'b', 'c'], 'triangle', ['a', 'b', 'c']), (['d'], 'on_pline', ['d', 'a', 'c', 'b'], 'on_circle', ['d', 'a', 'b'])]]
        alphabet_list = [[True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False],
[True, True, True, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]]
        depth = 2
        file_idx = 27

        problem_list will be written to f'{CACHE_PATH}/depth_1/problem_chunk_27.txt'
        alphabet_list will be written to f'{CACHE_PATH}/depth_1/alphabet_chunk_27.txt'
    """
    if not os.path.exists(f'{CACHE_PATH}/depth_{depth}/'):
        os.makedirs(f'{CACHE_PATH}/depth_{depth}/')
    num_chunks = (len(problem_list) + CHUNK_SIZE - 1) // CHUNK_SIZE

    if source_list is not None and len(source_list) != len(problem_list):
        raise ValueError("source_list must have one entry for every generated problem")

    problem_idx = file_idx
    alphabet_idx = file_idx
    source_idx = file_idx
    for i in range(num_chunks):
        start_index = i * CHUNK_SIZE
        end_index = min((i + 1) * CHUNK_SIZE, len(problem_list))
        chunk = problem_list[start_index:end_index]

        with open(f'{CACHE_PATH}/depth_{depth}/problem_chunk_{problem_idx}.txt', 'w') as f:
            for item in chunk:
                f.write(f"{item}\n")
        problem_idx += 1
        file_idx += 1

    for i in range(num_chunks):
        start_index = i * CHUNK_SIZE
        end_index = min((i + 1) * CHUNK_SIZE, len(problem_list))
        chunk = alphabet_list[start_index:end_index]

        with open(f'{CACHE_PATH}/depth_{depth}/alphabet_chunk_{alphabet_idx}.txt', 'w') as f:
            for item in chunk:
                f.write(f"{item}\n")
        alphabet_idx += 1
        # file_ix += 1 # no need, problem and alphabet share same length
    if source_list is not None:
        for i in range(num_chunks):
            start_index = i * CHUNK_SIZE
            end_index = min((i + 1) * CHUNK_SIZE, len(source_list))
            chunk = source_list[start_index:end_index]
            with open(f'{CACHE_PATH}/depth_{depth}/source_chunk_{source_idx}.txt', 'w') as f:
                for item in chunk:
                    f.write(f"{item}\n")
            source_idx += 1
    return file_idx


def read_list_from_txt(file_path: str):
    """
    read problem and alphabet list from file_path

    Examples:
        file_path = ./problems/generate_cache/depth_1/problem_chunk_0.txt

        return the file content
    """
    list_object = []
    try:
        with open(file_path, 'r') as f:
            list_object.extend([ast.literal_eval(line.strip())
                               for line in f.readlines()])
    except FileNotFoundError:
        print(f"No file at {file_path}")
    except Exception as e:
        print(
            f"While reading file at {file_path}, an error occured: {traceback.format_exc()}")
    return list_object


def read_text_lines(file_path: str) -> list[str]:
    """Read one plain-text source tag per line from a generator cache file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.rstrip("\n") for line in f]
    except FileNotFoundError:
        print(f"No file at {file_path}")
    return []


def _chunk_ids(depth_dir: str, kind: str) -> set[int]:
    """Return numeric chunk ids without accepting unrelated cache files."""
    if not os.path.isdir(depth_dir):
        return set()
    prefix = f"{kind}_chunk_"
    suffix = ".txt"
    result = set()
    for filename in os.listdir(depth_dir):
        if filename.startswith(prefix) and filename.endswith(suffix):
            number = filename[len(prefix):-len(suffix)]
            if number.isdigit():
                result.add(int(number))
    return result


def _strict_cache_chunk(depth_dir: str, chunk_id: int) -> tuple[list, list, list[str]]:
    """Read a cache triplet strictly; unlike legacy readers, never hide corruption."""
    paths = {
        kind: os.path.join(depth_dir, f"{kind}_chunk_{chunk_id}.txt")
        for kind in ("problem", "alphabet", "source")
    }
    with open(paths["problem"], "r", encoding="utf-8") as f:
        problems = [ast.literal_eval(line.strip()) for line in f if line.strip()]
    with open(paths["alphabet"], "r", encoding="utf-8") as f:
        alphabets = [ast.literal_eval(line.strip()) for line in f if line.strip()]
    with open(paths["source"], "r", encoding="utf-8") as f:
        sources = [line.rstrip("\n") for line in f if line.rstrip("\n")]
    if not problems or not (len(problems) == len(alphabets) == len(sources)):
        raise ValueError(
            f"invalid cache triplet: problems={len(problems)}, alphabets={len(alphabets)}, "
            f"sources={len(sources)}")
    if len(problems) > CHUNK_SIZE:
        raise ValueError(f"cache chunk has {len(problems)} records (limit is {CHUNK_SIZE})")
    if any(":" not in source for source in sources):
        raise ValueError("cache source tag must have '<kind>:<id>' format")
    return problems, alphabets, sources


def validate_cache_depth(depth: int, cache_dir: str = CACHE_PATH) -> dict:
    """Validate every triplet in one depth and return a serializable report."""
    depth_dir = os.path.join(cache_dir, f"depth_{depth}")
    ids_by_kind = {kind: _chunk_ids(depth_dir, kind) for kind in ("problem", "alphabet", "source")}
    all_ids = set().union(*ids_by_kind.values())
    common_ids = set.intersection(*ids_by_kind.values()) if all(ids_by_kind.values()) else set()
    report = {
        "depth": depth,
        "chunk_count": len(all_ids),
        "valid_chunk_count": 0,
        "missing_triplets": sorted(all_ids - common_ids),
        "invalid_chunks": [],
        "record_count": 0,
    }
    for chunk_id in sorted(common_ids):
        try:
            problems, _, _ = _strict_cache_chunk(depth_dir, chunk_id)
        except Exception as exc:
            report["invalid_chunks"].append({
                "chunk_id": chunk_id,
                "error_type": type(exc).__name__,
                "message": str(exc),
            })
            continue
        report["valid_chunk_count"] += 1
        report["record_count"] += len(problems)
    report["valid"] = bool(all_ids) and not report["missing_triplets"] and not report["invalid_chunks"]
    return report


def available_cache_depths(cache_dir: str = CACHE_PATH) -> list[int]:
    if not os.path.isdir(cache_dir):
        return []
    result = []
    for name in os.listdir(cache_dir):
        if name.startswith("depth_") and name[6:].isdigit() and os.path.isdir(os.path.join(cache_dir, name)):
            result.append(int(name[6:]))
    return sorted(result)


def _depth_dir(depth: int, cache_dir: str = CACHE_PATH) -> str:
    return os.path.join(cache_dir, f"depth_{depth}")


def _completion_path(depth: int, cache_dir: str = CACHE_PATH) -> str:
    return os.path.join(_depth_dir(depth, cache_dir), ".complete.json")


def mark_depth_complete(depth: int, cache_dir: str = CACHE_PATH, assumed: bool = False) -> None:
    """Mark a fully processed layer; marker is separate from cache chunk files."""
    ids = _chunk_ids(_depth_dir(depth, cache_dir), "problem")
    if not ids:
        raise ValueError(f"Cannot mark empty depth_{depth} as complete")
    _atomic_write_text(_completion_path(depth, cache_dir), json.dumps({
        "depth": depth,
        "chunk_count": len(ids),
        "assumed": assumed,
    }, ensure_ascii=False, indent=2) + "\n")


def completed_cache_depths(cache_dir: str = CACHE_PATH) -> list[int]:
    return [depth for depth in available_cache_depths(cache_dir)
            if os.path.isfile(_completion_path(depth, cache_dir))]


def layer_chunk_count(depth: int, cache_dir: str = CACHE_PATH) -> int:
    """Return a contiguous chunk count without fully parsing a trusted input depth."""
    ids = _chunk_ids(_depth_dir(depth, cache_dir), "problem")
    if not ids or ids != set(range(max(ids) + 1)):
        raise ValueError(f"depth_{depth} has non-contiguous or empty problem chunks")
    return len(ids)


def archive_incomplete_depths(first_depth: int, target_depth: int, cache_dir: str = CACHE_PATH) -> list[str]:
    """Preserve incomplete layers by renaming, never deleting them."""
    from datetime import datetime
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived = []
    for depth in range(first_depth, target_depth + 1):
        source = _depth_dir(depth, cache_dir)
        if not os.path.isdir(source) or os.path.isfile(_completion_path(depth, cache_dir)):
            continue
        destination = f"{source}.incomplete_{suffix}"
        os.replace(source, destination)
        archived.append(destination)
    return archived


def _atomic_write_text(path: str, text: str) -> None:
    """Commit one text file atomically in the target directory."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix=".tmp_", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def _format_problem(problem: list[tuple]) -> str:
    text = ""
    for line in problem:
        if len(line) == 3:
            cons, name, args = line
            text += f"{' '.join(cons)} = {name} {' '.join(args)}; "
        else:
            cons, name1, args1, name2, args2 = line
            text += (f"{' '.join(cons)} = {name1} {' '.join(args1)}, "
                     f"{name2} {' '.join(args2)}; ")
    return text.rstrip("; ") + "\n"


EXPORT_CHUNKS_PER_FILE = 100


def export_cache_depth(
        depth: int,
        cache_dir: str = CACHE_PATH,
        out_dir: str = OUTPUT_FILE_PATH,
        validate: bool = True,
) -> dict:
    """Idempotently export a validated cache depth, resuming after an interrupted export."""
    if validate:
        report = validate_cache_depth(depth, cache_dir)
        if not report["valid"]:
            raise ValueError(f"depth_{depth} is not exportable: {json.dumps(report, ensure_ascii=False)}")
    depth_dir = os.path.join(cache_dir, f"depth_{depth}")
    normalized_out_dir = os.path.abspath(out_dir)
    chunk_ids = sorted(_chunk_ids(depth_dir, "problem"))
    os.makedirs(out_dir, exist_ok=True)
    state_path = os.path.join(cache_dir, f"export_state_depth_{depth}.json")
    state = {
        "format_version": 3,
        "depth": depth,
        "output_dir": normalized_out_dir,
        "chunks_per_output_file": EXPORT_CHUNKS_PER_FILE,
        "next_batch": 0,
        "next_problem_id": 1,
        "complete": False,
    }
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            old_state = json.load(f)
        if old_state.get("depth") != depth:
            raise ValueError(f"export state {state_path} belongs to another depth")
        # A checkpoint is valid only for the exact same output directory.
        # Older versions did not store it, and would incorrectly skip output
        # batches after the caller selected a new directory.
        if (old_state.get("format_version") == 3
                and old_state.get("chunks_per_output_file") == EXPORT_CHUNKS_PER_FILE
                and old_state.get("output_dir") == normalized_out_dir):
            state = old_state
        else:
            logging.info("Resetting export checkpoint for depth_%d because its output directory changed or uses an old format", depth)
    batches = [chunk_ids[i:i + EXPORT_CHUNKS_PER_FILE]
               for i in range(0, len(chunk_ids), EXPORT_CHUNKS_PER_FILE)]
    start = int(state.get("next_batch", 0))
    next_problem_id = int(state.get("next_problem_id", 1))
    if start < 0 or start > len(batches):
        raise ValueError(f"invalid export checkpoint position {start}")

    for batch_index in range(start, len(batches)):
        raw_lines, source_lines = [], []
        for chunk_id in batches[batch_index]:
            problems, _, sources = _strict_cache_chunk(depth_dir, chunk_id)
            for problem, source in zip(problems, sources):
                problem_id = f"gen_{next_problem_id}"
                raw_lines.extend((problem_id + "\n", _format_problem(problem)))
                source_kind, source_id = source.split(":", maxsplit=1)
                source_lines.append(json.dumps({
                    "problem_id": problem_id,
                    "initial_seed_source": source_kind,
                    "initial_seed_id": source_id,
                }, ensure_ascii=False) + "\n")
                next_problem_id += 1
        _atomic_write_text(os.path.join(out_dir, f"problems_{batch_index}.txt"), "".join(raw_lines))
        _atomic_write_text(os.path.join(out_dir, f"initial_seed_sources_{batch_index}.jsonl"), "".join(source_lines))
        state = {
            "format_version": 3,
            "depth": depth,
            "output_dir": normalized_out_dir,
            "chunks_per_output_file": EXPORT_CHUNKS_PER_FILE,
            "next_batch": batch_index + 1,
            "next_problem_id": next_problem_id,
            "complete": False,
        }
        _atomic_write_text(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    manifest_parts = []
    for batch_index in range(len(batches)):
        with open(os.path.join(out_dir, f"initial_seed_sources_{batch_index}.jsonl"), "r", encoding="utf-8") as f:
            manifest_parts.append(f.read())
    _atomic_write_text(os.path.join(out_dir, "initial_seed_sources.jsonl"), "".join(manifest_parts))
    state["complete"] = True
    _atomic_write_text(state_path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return {"depth": depth, "chunk_count": len(chunk_ids), "output_file_count": len(batches), "problem_count": next_problem_id - 1,
            "output_dir": out_dir}


def _simple_construction_seed(defs: dict, name: str) -> tuple[list[tuple], list[bool]]:
    """Build the one-clause root formerly used by the no-template fallback."""
    construction = defs[name]
    alphabet = [False] * len(ALPHABET_DICT)
    new_args = [arg for arg in sum(
        map(lambda x: x[0], construction.basics), []) if arg]
    new_args_name, alphabet = select_unused_args(alphabet, len(new_args))
    if new_args_name is None:
        raise ValueError(f"Cannot allocate initial points for simple construction {name}")
    return [(new_args_name, construction.construction.name, new_args_name)], alphabet


def build_initial_seeds(
        defs: dict,
        independent_constructions: list[str],
        structure_templates: Optional[list[dict]],
        initial_seed_mode: str = INITIAL_SEED_MODE,
) -> tuple[list[list[tuple]], list[list[bool]], list[str]]:
    """Return deterministic initial roots selected from template/simple sources.

    A simple root is a standalone basic figure.  It is never appended to an
    existing template root, so every generated premise remains one connected
    construction lineage before the normal dependent BFS expansion begins.
    """
    if initial_seed_mode not in INITIAL_SEED_MODES:
        supported = ", ".join(sorted(INITIAL_SEED_MODES))
        raise ValueError(
            f"Unknown initial_seed_mode {initial_seed_mode!r}; expected one of {supported}")

    seeds: list[tuple[list[tuple], list[bool], str]] = []
    include_templates = initial_seed_mode in {"templates_only", "mixed"}
    include_simple = initial_seed_mode in {"simple_only", "mixed"}

    if include_templates:
        if not structure_templates:
            if initial_seed_mode == "templates_only":
                raise ValueError(
                    "initial_seed_mode='templates_only' requires at least one structure template")
        else:
            for template in sorted(structure_templates, key=lambda item: item["id"]):
                problem, alphabet = st.template_seed(template)
                seeds.append((problem, alphabet, f"template:{template['id']}"))

    if include_simple:
        available = set(independent_constructions)
        selected_simple = [
            name for name in SIMPLE_INITIAL_CONSTRUCTIONS if name in available]
        if not selected_simple:
            raise ValueError("No configured simple initial constructions are available")
        for name in selected_simple:
            problem, alphabet = _simple_construction_seed(defs, name)
            seeds.append((problem, alphabet, f"simple:{name}"))

    # Shuffle the combined roots, rather than templates only, so the later
    # random choices do not give a deterministic preference to either source.
    random.shuffle(seeds)
    return (
        [problem for problem, _, _ in seeds],
        [alphabet for _, alphabet, _ in seeds],
        [source for _, _, source in seeds],
    )


def bfs_genreate(
        defs: list,
        independent_constructions: list,
        dependent_constructions: list,
        dependent_non_unique_constructions: list,
        depth: int = 4,
        expand_defs: list[int] = [4, 1, 1, 1, 1],
        expand_args: list[int] = [0, 2, 1, 1, 1],
        structure_templates: Optional[list[dict]] = None,
        initial_seed_mode: str = INITIAL_SEED_MODE,
        start_depth: int = 0,
):
    """
    Generate constructions based on given definitions, written to f'{CACHE_PATH}/depth_{depth-1}'. return the size of generated problems

    Examples:
        defs = init_defs[0]
        independent_constructions = init_defs[1]
        dependent_constructions = init_defs[2]
        dependent_non_unique_constructions = init_defs[3]
        depth = 3
        expand_defs = [3,3,3,3]
        expand_args = [0,3,3,3]

        CHUNK_SIZE = 50

        return = [1, 1, 5], [6, 64, 726]
    """

    layer_size = [0 for _ in range(depth)]
    problem_size = [0 for _ in range(depth)]

    if start_depth < 0 or start_depth >= depth:
        raise ValueError(f"start_depth={start_depth} is outside target depths 0..{depth - 1}")
    if start_depth == 0:
        my_problems, my_alphabets, my_sources = build_initial_seeds(
            defs, independent_constructions, structure_templates, initial_seed_mode)
        source_counts = {
            "template": sum(source.startswith("template:") for source in my_sources),
            "simple": sum(source.startswith("simple:") for source in my_sources),
        }
        logging.info(
            "initial_seed_mode=%s; roots: template=%d, simple=%d, total=%d",
            initial_seed_mode,
            source_counts["template"],
            source_counts["simple"],
            len(my_problems),
        )
        layer_size[0] = save_list_to_txt(
            my_problems, my_alphabets, 0, layer_size[0], my_sources)
        problem_size[0] += len(my_problems)
        mark_depth_complete(0, CACHE_PATH)
    else:
        layer_size[start_depth] = layer_chunk_count(start_depth, CACHE_PATH)
        logging.info("Resuming BFS from trusted complete depth_%d (%d chunks)",
                     start_depth, layer_size[start_depth])

    # for each depth, select expand_defs[d] dependent_constructions
    for d in range(start_depth, depth-1):
        for idx in tqdm(range(layer_size[d]), total=layer_size[d], desc=f"Depth = {d+1}"):
            problem = read_list_from_txt(
                f'{CACHE_PATH}/depth_{d}/problem_chunk_{idx}.txt')
            alphabet = read_list_from_txt(
                f'{CACHE_PATH}/depth_{d}/alphabet_chunk_{idx}.txt')
            sources = read_text_lines(
                f'{CACHE_PATH}/depth_{d}/source_chunk_{idx}.txt')
            if not (len(problem) == len(alphabet) == len(sources)):
                logging.error(
                    "Skipping corrupt cache chunk at depth %d, chunk %d: problem=%d alphabet=%d source=%d",
                    d, idx, len(problem), len(alphabet), len(sources))
                continue

            my_problems = []
            my_alphabets = []
            my_sources = []
            # problem = problems[d]
            # alphabet = alphabets[d]
            # logging.info(f"problem:{problem} alphabet:{alphabet}")
            for (p, a, source) in tqdm(zip(problem, alphabet, sources), total=len(problem), desc=f"Depth {depth}-Process", leave=False):
                search_size = expand_defs[d+1] if expand_defs[d +
                                                              1] > 0 else len(dependent_constructions)
                chosen_dependent_constructions = random_sample(
                    dependent_constructions, search_size)

                for i in range(search_size):
                    if random.random() < 0.5:
                        name2 = chosen_dependent_constructions[i]
                        this_construction2 = defs[name2]

                        try:
                            constructions_list2 = generate_constructions(
                                name2, this_construction2, a, expand_args[d+1])
                        except Exception:
                            logging.exception(
                                "Skipping construction %s at depth %d, chunk %d", name2, d, idx)
                            continue

                        for cons2 in constructions_list2 or []:
                            # cons[0:2] = new_args_name, all_args_name, new_alphabet
                            if cons2 is None or cons2[0] is None:
                                continue
                            my_problems.append(copy.deepcopy(p)+[(cons2[0],
                                                                  this_construction2.construction.name, cons2[1])])
                            my_alphabets.append(cons2[2])
                            my_sources.append(source)
                    else:
                        chosen_dependent_non_unique_constructions = random_sample(
                            dependent_non_unique_constructions, 2)

                        name3 = chosen_dependent_non_unique_constructions[0]
                        name4 = chosen_dependent_non_unique_constructions[1]
                        this_construction3 = defs[name3]
                        this_construction4 = defs[name4]

                        try:
                            constructions_list3 = generate_constructions(
                                name3, this_construction3, a, expand_args[d+1])
                            constructions_list4 = generate_constructions(
                                name4, this_construction4, a, expand_args[d+1])
                        except Exception:
                            logging.exception(
                                "Skipping construction pair %s/%s at depth %d, chunk %d",
                                name3, name4, d, idx)
                            continue

                        for cons3, cons4 in zip(constructions_list3 or [], constructions_list4 or []):
                            # cons[0:2] = new_args_name, all_args_name, new_alphabet
                            if cons3 is None or cons3[0] is None or cons4 is None or cons4[0] is None:
                                continue

                            my_problems.append(copy.deepcopy(p)+[(cons3[0], this_construction3.construction.name,
                                                                  cons3[1], this_construction4.construction.name, cons4[1])])
                            my_alphabets.append(cons4[2])
                            my_sources.append(source)

            assert len(my_problems) == len(my_alphabets) == len(my_sources)
            indices = list(range(len(my_problems)))
            random.shuffle(indices)
            shuffled_my_problems = [my_problems[i] for i in indices]
            shuffled_my_alphabets = [my_alphabets[i] for i in indices]
            shuffled_my_sources = [my_sources[i] for i in indices]
            layer_size[d+1] = save_list_to_txt(shuffled_my_problems,
                                               shuffled_my_alphabets, d+1, layer_size[d+1],
                                               shuffled_my_sources)
            problem_size[d+1] += len(my_problems)
        mark_depth_complete(d + 1, CACHE_PATH)
    return layer_size, problem_size


def clear_output_file(out_file: str = OUTPUT_FILE_PATH):
    if not os.path.exists(out_file):
        return
    for filename in os.listdir(out_file):
        file_path = os.path.join(out_file, filename)
        try:
            os.remove(file_path)
        except OSError as e:
            raise ValueError("File delete failed")


def delete_generate_cache(cache_file: str = CACHE_PATH):
    if os.path.exists(cache_file):
        shutil.rmtree(cache_file)
        print(f"Delete generate cache successfully.")
    else:
        raise ValueError("Delete generate cache failed")


# def save_problem(problem: list, out_file: str = OUTPUT_FILE_PATH):
def save_problem(layer_size: list[int], out_file: str = OUTPUT_FILE_PATH):
    if not os.path.exists(out_file):
        os.makedirs(out_file)

    d = len(layer_size)-1
    question_count = 1
    source_manifest = []

    for idx in range(layer_size[-1]):
        # for filename in os.listdir(f'{CACHE_PATH}/depth_{d}/'):
        problems = read_list_from_txt(
            f'{CACHE_PATH}/depth_{d}/problem_chunk_{idx}.txt')
        source_file = f'{CACHE_PATH}/depth_{d}/source_chunk_{idx}.txt'
        sources = read_text_lines(source_file) if os.path.exists(source_file) else None
        if sources is not None and len(problems) != len(sources):
            raise ValueError(
                f"Mismatched final problem/source lengths at depth {d}, chunk {idx}")

        output_name = f"{out_file}problems_{idx}.txt"
        with open(output_name, 'a', encoding='utf-8') as f:
            # for ps in problem[1:]:
            #     for p in ps:
            # random.shuffle(problem[-1])
            for problem_index, p in enumerate(problems):
                txt = ""
                for line in p:
                    if len(line) == 3:
                        cons, name, args = line
                        cons_str = " ".join(cons)
                        name_str = str(name)
                        args_str = " ".join(args)
                        txt += f"{cons_str} = {name_str} {args_str}; "
                    else:
                        cons, name1, args1, name2, args2 = line
                        cons_str = " ".join(cons)
                        name_str1 = str(name1)
                        args_str1 = " ".join(args1)
                        name_str2 = str(name2)
                        args_str2 = " ".join(args2)
                        txt += f"{cons_str} = {name_str1} {args_str1}, {name_str2} {args_str2}; "
                txt = txt.rstrip("; ")+"\n"

                problem_name = f"gen_{question_count}\n"
                f.write(problem_name+txt)
                if sources is not None:
                    source_kind, source_id = sources[problem_index].split(":", maxsplit=1)
                    source_manifest.append({
                        "problem_id": f"gen_{question_count}",
                        "initial_seed_source": source_kind,
                        "initial_seed_id": source_id,
                    })
                question_count += 1
                # logging.info(f"问题文本：{txt}")

    if source_manifest:
        manifest_path = os.path.join(out_file, "initial_seed_sources.jsonl")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            for record in source_manifest:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv):
    del argv
    global CACHE_PATH, OUTPUT_FILE_PATH
    CACHE_PATH = FLAGS.run_dir
    OUTPUT_FILE_PATH = FLAGS.output_dir
    target_depth = FLAGS.target_depth
    if target_depth < 0:
        raise ValueError("target_depth must be non-negative")

    cache_depths = available_cache_depths(CACHE_PATH)
    if FLAGS.assume_complete_depth >= 0:
        assumed = FLAGS.assume_complete_depth
        if assumed > target_depth or not os.path.isdir(_depth_dir(assumed, CACHE_PATH)):
            raise ValueError(f"Cannot trust missing/out-of-range depth_{assumed}")
        mark_depth_complete(assumed, CACHE_PATH, assumed=True)

    if FLAGS.run_mode == "validate":
        completed = completed_cache_depths(CACHE_PATH)
        selected = FLAGS.export_depth if FLAGS.export_depth >= 0 else (max(completed) if completed else -1)
        if selected not in completed:
            raise ValueError(f"depth_{selected} is not marked complete; use --assume_complete_depth only when justified")
        validation = validate_cache_depth(selected, CACHE_PATH)
        _atomic_write_text(os.path.join(CACHE_PATH, f"validation_depth_{selected}.json"),
                           json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(validation, ensure_ascii=False))
        return

    if FLAGS.run_mode == "finalize":
        # Export is also useful during a long BFS run.  A completion marker
        # means "safe as a resume parent", not "eligible for extraction";
        # accept any numerically named cache layer that has already written
        # valid problem/alphabet/source triplets.
        selected = FLAGS.export_depth if FLAGS.export_depth >= 0 else (max(cache_depths) if cache_depths else -1)
        if selected not in cache_depths:
            raise ValueError(f"depth_{selected} does not exist in {CACHE_PATH}")
        validation = validate_cache_depth(selected, CACHE_PATH)
        _atomic_write_text(os.path.join(CACHE_PATH, f"validation_depth_{selected}.json"),
                           json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(validation, ensure_ascii=False))
        if not validation["valid"]:
            raise ValueError(f"Cannot export invalid depth_{selected}")
        print(json.dumps(export_cache_depth(selected, CACHE_PATH, OUTPUT_FILE_PATH, validate=False), ensure_ascii=False))
        return

    if FLAGS.run_mode == "new":
        if cache_depths or (os.path.exists(CACHE_PATH) and os.listdir(CACHE_PATH)):
            raise ValueError(f"Refusing to overwrite existing cache {CACHE_PATH}")
        start_depth = 0
    else:  # resume
        completed = [d for d in completed_cache_depths(CACHE_PATH) if d <= target_depth]
        if cache_depths and not completed:
            raise ValueError(
                "Existing cache has no completion marker; pass --assume_complete_depth=<last trusted depth>")
        start_depth = (max(completed) if completed else 0)
        if start_depth >= target_depth:
            selected = FLAGS.export_depth if FLAGS.export_depth >= 0 else target_depth
            if selected not in completed_cache_depths(CACHE_PATH):
                raise ValueError(f"depth_{selected} is not complete")
            print(json.dumps(export_cache_depth(selected, CACHE_PATH, OUTPUT_FILE_PATH), ensure_ascii=False))
            return
        archived = archive_incomplete_depths(start_depth + 1, target_depth, CACHE_PATH)
        if archived:
            logging.info("Archived incomplete layers: %s", archived)

    # A generated target depth receives a separate default output directory so
    # extracting depth_8 never overwrites a prior depth_6 export.
    if OUTPUT_FILE_PATH == DEFAULT_OUTPUT_FILE_PATH:
        OUTPUT_FILE_PATH = os.path.join(_paths.PROJECT_ROOT, "problems", f"problems_depth_{target_depth}")
    if os.path.exists(OUTPUT_FILE_PATH) and os.listdir(OUTPUT_FILE_PATH):
        raise ValueError(f"Refusing to overwrite non-empty output {OUTPUT_FILE_PATH}")

    random.seed(2447)
    defs, independent_constructions, dependent_constructions, dependent_non_unique_constructions = init_defs(DEFS_FILE_PATH)
    selected_templates = st.load_templates(
        STRUCTURE_TEMPLATES_FILE_PATH, defs, priorities={"P0", "P1", "P2", "P3"})
    count_of_bfs_expand_defs = [-1, -1, 6, 4, 2, 1, 1, 1]
    count_of_bfs_expand_args = [-1, 6, 4, 2, 1, 1, 1, 1]
    while len(count_of_bfs_expand_defs) <= target_depth:
        count_of_bfs_expand_defs.append(count_of_bfs_expand_defs[-1])
    while len(count_of_bfs_expand_args) <= target_depth:
        count_of_bfs_expand_args.append(count_of_bfs_expand_args[-1])

    layer_size, problem_size = bfs_genreate(
        defs, independent_constructions, dependent_constructions, dependent_non_unique_constructions,
        target_depth + 1, count_of_bfs_expand_defs, count_of_bfs_expand_args,
        selected_templates, INITIAL_SEED_MODE, start_depth)
    export_summary = export_cache_depth(target_depth, CACHE_PATH, OUTPUT_FILE_PATH)
    print(json.dumps(export_summary, ensure_ascii=False))
    print(layer_size)
    print(problem_size)


if __name__ == "__main__":
    app.run(main)
