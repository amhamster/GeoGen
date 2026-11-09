# Copyright 2023 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Run DD+AR or AlphaGeometry solver.

Please refer to README.md for detailed instructions.
"""


from translation import translate_problem_to_natural_language, translate_goals_to_natural_language, generate_wrong_answer
from display_rewrite import build_display_rewrite_plan
import problem as pr
import pretty as pt
import graph as gh
import ddar
from absl import logging
from absl import flags
from absl import app
import traceback
import drawing
import random
import os
import re
from datetime import datetime
import _paths
import json
from geometry import Point
from multiprocessing import Pool
from tqdm import tqdm
from publication import atomic_json, compact_payload

MAX_PROCESSES = 10 # 4

MODE = "ngddarOneByOne"  # another is "onlyDrawOnebyOne"
PROBLEM_START = 0
PROBLEM_END = 100 #100

DEFINITIONS = None  # contains definitions of construction actions
RULES = None  # contains rules of deductions

CHALLENGING_PROBLEM_SCORE_THRESHOLD = 54

LOG_DETAIL = False

# The original, full construction has already been solved before a target is
# selected. Re-solving the intentionally reduced question is useful only as a
# diagnostic: a human may need to add the recorded auxiliary construction.
VALIDATE_STRUCTURAL_GOAL = False


FLAGS = flags.FLAGS
flags.DEFINE_string(
    "input_dir", _paths.NEW_PROBLEMS_DIR,
    "Directory containing problems_N.txt premise files.")
flags.DEFINE_integer(
    "file_start", PROBLEM_START,
    "First numeric problems_N.txt index to process (inclusive).")
flags.DEFINE_integer(
    "file_end", PROBLEM_END,
    "Last numeric problems_N.txt index to process (exclusive).")
flags.DEFINE_string(
    "file_indices", "",
    "Optional comma-separated problems_N.txt indices; overrides --file_start/--file_end.")
flags.DEFINE_integer(
    "workers", MAX_PROCESSES,
    "Number of internal worker processes. Use 1 with the shard launcher.")
flags.DEFINE_string(
    "output_dir", "",
    "Exact directory for generated JSON/PNG files; empty creates a timestamped directory.")
flags.DEFINE_string(
    "shard_id", "",
    "Optional shard label used to isolate failure and progress logs.")
flags.DEFINE_bool(
    "resume", False,
    "Skip source files recorded as complete in this shard's progress log.")


def make_generation_failure(
        stage: str,
        error: Exception,
        problem_id: str | None = None,
        input_index: int | None = None,
        input_file: str | None = None,
) -> dict:
    """Create a serializable failure record without re-raising a worker error."""
    record = {
        "stage": stage,
        "error_type": type(error).__name__,
        "error": str(error),
        "traceback": traceback.format_exc(),
    }
    if problem_id is not None:
        record["problem_id"] = problem_id
    if input_index is not None:
        record["input_index"] = input_index
    if input_file is not None:
        record["input_file"] = input_file
    return record


def natural_language_statement(logical_statement: pr.Dependency) -> str:
    """Convert logical_statement to natural language.

  Args:
    logical_statement: pr.Dependency with .name and .args

  Returns:
    a string of (pseudo) natural language of the predicate for human reader.
  """
    names = [a.name.upper() for a in logical_statement.args]
    names = [(n[0] + '_' + n[1:]) if len(n) > 1 else n for n in names]
    return pt.pretty_nl(logical_statement.name, names)


def proof_step_string(
        proof_step: pr.Dependency, refs: dict[tuple[str, ...], int], last_step: bool
) -> str:
    """Translate proof to natural language.

  Args:
    proof_step: pr.Dependency with .name and .args
    refs: dict(hash: int) to keep track of derived predicates
    last_step: boolean to keep track whether this is the last step.

  Returns:
    a string of (pseudo) natural language of the proof step for human reader.
  """
    premises, [conclusion] = proof_step

    premises_nl = ' & '.join(
        [
            natural_language_statement(p) + ' [{:02}]'.format(refs[p.hashed()])
            for p in premises
        ]
    )

    if not premises:
        premises_nl = 'similarly'

    refs[conclusion.hashed()] = len(refs)

    conclusion_nl = natural_language_statement(conclusion)
    if not last_step:
        conclusion_nl += ' [{:02}]'.format(refs[conclusion.hashed()])

    return f'{premises_nl} \u21d2 {conclusion_nl}'


def get_clauses_txt(clauses):
    # 得到problem全部的内容
    clauses_txt = []
    for clause in clauses:
        clause_txt = " ".join(clause.points)
        clause_txt += " = "
        constructions_txt = []
        for construction in clause.constructions:
            construction_txt = construction.name
            if construction.args:
                construction_txt += " " + " ".join(construction.args)
            constructions_txt.append(construction_txt)
        constructions_txt = ", ".join(constructions_txt)
        clause_txt += constructions_txt
        clauses_txt.append(clause_txt)
    clauses_txt = "; ".join(clauses_txt)

    return clauses_txt


def get_structural_points(g: gh.Graph, goal: pr.Construction) -> set[str]:
    """Return the construction ancestors of the points named in ``goal``.

    This is intentionally independent from a proof traceback.  ``Point.rely_on``
    is populated while the numerical construction is built, so it describes
    which earlier points are needed to construct a point, not which points a
    particular proof happened to mention.
    """
    points = set()
    queue = []
    for arg in goal.args:
        point = g._name2point.get(arg)
        if point is not None:
            points.add(point)
            queue.append(point)

    index = 0
    while index < len(queue):
        point = queue[index]
        index += 1
        for parent in getattr(point, "rely_on", set()):
            if isinstance(parent, Point) and parent not in points:
                points.add(parent)
                queue.append(parent)

    return {point.name for point in points}


def get_clause_dependency_slice(
        p: pr.Problem,
        seed_points: set[str],
) -> list[int]:
    """Return clause indices needed to define ``seed_points``.

    The initial seeds come from the graph's structural dependency relation.
    The additional backwards closure over construction arguments is a safety
    guard: every point named by a retained construction must itself be defined
    by the retained question, even if a definition's numeric ``rely`` field is
    deliberately weaker than its textual construction arguments.
    """
    point_to_clause = {
        point: index
        for index, clause in enumerate(p.clauses)
        for point in clause.points
    }
    required = set(seed_points)
    retained = set()
    queue = list(seed_points)

    index = 0
    while index < len(queue):
        point = queue[index]
        index += 1
        clause_index = point_to_clause.get(point)
        if clause_index is None or clause_index in retained:
            continue

        retained.add(clause_index)
        clause = p.clauses[clause_index]
        for construction in clause.constructions:
            for arg in construction.args:
                if arg in point_to_clause and arg not in required:
                    required.add(arg)
                    queue.append(arg)

    return sorted(retained)


def clauses_to_problem_text(
        p: pr.Problem,
        clause_indices: list[int],
) -> str:
    """Serialize a clause slice together with the unchanged target."""
    clauses = [p.clauses[index] for index in clause_indices]
    return f"{get_clauses_txt(clauses)} ? {p.goal.txt()}"


def problem_point_names(p: pr.Problem) -> list[str]:
    """Return every point explicitly introduced by a problem's clauses."""
    return sorted({point for clause in p.clauses for point in clause.points})


def save_validation_failure(
        save_path: str,
        source_problem: pr.Problem,
        structural_problem: pr.Problem,
        solution_info: dict,
        failure_stage: str,
        candidates: list[tuple[pr.Construction, bool, str, pr.Construction]],
        answer: str,
) -> None:
    """Persist a structurally simplified problem that cannot be built.

    The original full construction is already known to be solvable.  Keeping
    these cases makes malformed structural slices inspectable instead of
    silently reducing the generated dataset. The two comparable question
    statements are the construction-dependency slice and the proof-point
    slice. A slice that merely needs an auxiliary construction is valid and
    must not reach this function.
    """
    failure_path = os.path.join(save_path, "validation_failed")
    os.makedirs(failure_path, exist_ok=True)
    proof_slice_text = clauses_to_problem_text(
        source_problem, solution_info["proof_clause_indices"])
    proof_slice_problem = pr.Problem.from_txt(proof_slice_text, translate=False)
    payload = {
        "ID": source_problem.url,
        "ValidationStatus": "failed",
        "FailureStage": failure_stage,
        "Target": source_problem.goal.txt(),
        "StructuralFormalText": structural_problem.txt(),
        "ProofSliceFormalText": proof_slice_text,
        "OriginalFormalText": source_problem.txt(),
        "StructuralQuestion_zh": translate_problem_to_natural_language(
            structural_problem, "zh", solution_info["structural_points"]),
        "ProofSliceQuestion_zh": translate_problem_to_natural_language(
            proof_slice_problem, "zh", problem_point_names(proof_slice_problem)),
        "StructuralPoints": solution_info["structural_points"],
        "StructuralDependencyPoints": solution_info[
            "structural_dependency_points"],
        "ProofUsedPoints": solution_info["used_points"],
        "AuxiliaryPoints": solution_info["auxiliary_points"],
        "StructuralClauseIndices": solution_info["structural_clause_indices"],
        "ProofClauseIndices": solution_info["proof_clause_indices"],
        "AuxiliaryClauseIndices": solution_info["auxiliary_clause_indices"],
        "AuxiliaryFormalText": solution_info["auxiliary_formal_text"],
        "Answer": answer,
        "ProofSteps": solution_info["proof_steps"],
        "Options": [
            {
                "formal": candidate.txt(),
                "is_correct": is_correct,
                "source_proof": proof_steps,
                "source_conclusion": source.txt(),
            }
            for candidate, is_correct, proof_steps, source in candidates
        ],
    }
    with open(
            os.path.join(failure_path, f"{source_problem.url}.json"),
            "w",
            encoding="utf-8",
    ) as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


def write_solution2(g: gh.Graph, p: pr.Problem) -> dict:
    """Output the solution to out_file.

    Args:
      g: gh.Graph object, containing the proof state.
      p: pr.Problem object, containing the theorem.
      out_file: file to write to, empty string to skip writing to file.
    """
    # setup 题目条件
    # aux 辅助条件
    # proof_steps 证明步骤
    # refs 证明编号编号
    setup, aux, proof_steps, refs = ddar.get_proof_steps(
        g, p.goal, merge_trivials=False
    )

    solution_dict = {}

    premises_nl = []
    proof_setup_points = []
    for premises, [points] in setup:
        proof_setup_points += [point.name.lower() for point in points]
        if not premises:
            continue
        premises_nl += [
            natural_language_statement(p) + " [{:02}]".format(refs[p.hashed()])
            for p in premises
        ]

    # ``aux`` is the part of the shortest proof whose construction points are
    # outside the goal's own construction ancestry. Omitting it here made the
    # proof slice look identical to the structural slice and prevented helper
    # constructions from being identified.
    proof_auxiliary_points = []
    for _, [points] in aux:
        proof_auxiliary_points += [point.name.lower() for point in points]

    proof_slice_points = proof_setup_points + proof_auxiliary_points
    if p.goal is not None:
        proof_slice_points += [arg for arg in p.goal.args if len(
            arg) == 1 and arg.isalpha()]
    proof_setup_points = sorted(set(proof_setup_points))
    proof_auxiliary_points = sorted(set(proof_auxiliary_points))
    proof_slice_points = sorted(set(proof_slice_points))

    structural_points = get_structural_points(g, p.goal)
    structural_clause_indices = get_clause_dependency_slice(
        p, structural_points)
    # A retained clause is displayed as a whole construction.  Therefore all
    # of its output points belong to the visible structural question, even if
    # only one of them was the direct ancestor of the goal.
    displayed_structural_points = {
        point
        for index in structural_clause_indices
        for point in p.clauses[index].points
    }
    proof_clause_indices = get_clause_dependency_slice(
        p, set(proof_slice_points))
    auxiliary_clause_indices = sorted(
        set(proof_clause_indices) - set(structural_clause_indices))

    solution_dict["problem_content"] = clauses_to_problem_text(
        p, structural_clause_indices)
    solution_dict["theorem_premises"] = premises_nl
    # ``used_points`` is retained for compatibility. New fields make the
    # three distinct point roles explicit.
    solution_dict["used_points"] = proof_slice_points
    solution_dict["proof_setup_points"] = proof_setup_points
    solution_dict["proof_auxiliary_points"] = proof_auxiliary_points
    solution_dict["proof_slice_points"] = proof_slice_points
    solution_dict["structural_dependency_points"] = sorted(structural_points)
    solution_dict["structural_points"] = sorted(displayed_structural_points)
    solution_dict["auxiliary_points"] = sorted(
        set(proof_slice_points) - displayed_structural_points)
    solution_dict["structural_clause_indices"] = structural_clause_indices
    solution_dict["proof_clause_indices"] = proof_clause_indices
    solution_dict["auxiliary_clause_indices"] = auxiliary_clause_indices
    solution_dict["auxiliary_formal_text"] = get_clauses_txt(
        [p.clauses[index] for index in auxiliary_clause_indices]
    )

    # 辅助条件
    aux_premises_nl = []
    aux_points = []
    for premises, [points] in aux:
        aux_points += [p.name.upper() for p in points]
        aux_premises_nl += [
            natural_language_statement(p) + " [{:02}]".format(refs[p.hashed()])
            for p in premises
        ]
    solution_dict["aux_points"] = aux_points
    solution_dict["aux_premises"] = aux_premises_nl

    # some special case where the deduction rule has a well known name.
    r2name = {
        "r32": "(SSS)",
        "r33": "(SAS)",
        "r34": "(Similar Triangles)",
        "r35": "(Similar Triangles)",
        "r36": "(ASA)",
        "r37": "(ASA)",
        "r38": "(Similar Triangles)",
        "r39": "(Similar Triangles)",
        "r40": "(Congruent Triangles)",
        "a00": "(Distance chase)",
        "a01": "(Ratio chase)",
        "a02": "(Angle chase)",
    }

    # 证明步骤
    pf_steps = ""
    for i, step in enumerate(proof_steps):
        _, [con] = step
        nl = proof_step_string(step, refs, last_step=i == len(proof_steps) - 1)
        rule_name = r2name.get(con.rule_name, "")
        nl = nl.replace("\u21d2", f"{rule_name}\u21d2 ")
        pf_steps += "{:03}. ".format(i + 1) + nl + "\n"

    solution_dict["proof_steps"] = pf_steps

    return solution_dict


def get_raw_difficulty(detailed_info: dict, search_level: int, proof_steps: int):
    # Mainly used to find the most challenging conclusion in same question

    description_difficulty = 1.5 * (detailed_info["problem_content"].count(
        ';') + detailed_info["problem_content"].count(',') + 1)

    premise_difficulty = 2.5 * len(detailed_info["theorem_premises"])

    # The displayed question is determined by construction ancestry, not by
    # the incidental points traversed in one proof.
    element_difficulty = 2 * len(detailed_info["structural_points"])

    proof_difficulty = 4 * search_level + proof_steps

    return description_difficulty + premise_difficulty + element_difficulty + proof_difficulty


TOP4_OPTION_TYPES = frozenset({
    "coll", "cong", "circle", "cyclic", "midp", "para", "perp",
})


def canonical_goal_key(goal: pr.Construction) -> tuple:
    """Canonicalize symmetric goal syntax before Top-4 ranking.

    DD+AR normally stores predicates canonically, but the explicit key keeps
    equivalent endpoint/order permutations from occupying multiple Top-4
    positions should a construction emit a non-canonical form.
    """
    args = tuple(goal.args)
    if goal.name in {"coll", "cyclic"}:
        return goal.name, tuple(sorted(args))
    if goal.name == "circle":
        return goal.name, args[0], tuple(sorted(args[1:]))
    if goal.name == "midp":
        return goal.name, args[0], tuple(sorted(args[1:]))
    if goal.name == "cong":
        segments = sorted((tuple(sorted(args[:2])), tuple(sorted(args[2:4]))))
        return goal.name, tuple(segments)
    if goal.name in {"para", "perp"}:
        segments = sorted((tuple(sorted(args[:2])), tuple(sorted(args[2:4]))))
        return goal.name, tuple(segments)
    return goal.name, args


def select_global_top_four(candidate_records: list[dict]) -> list[dict] | None:
    """Return the four globally highest-scored usable source conclusions.

    The previous selector first discarded every candidate whose proof points
    fell outside the main goal's structural points, then sampled one maximum
    per predicate type.  This selector deliberately performs neither action:
    every retained record competes in one global difficulty ordering.
    """
    best_by_key = {}
    for record in candidate_records:
        goal = record["goal"]
        if goal.name not in TOP4_OPTION_TYPES:
            continue
        key = record["canonical_key"]
        previous = best_by_key.get(key)
        if previous is None or record["difficulty"] > previous["difficulty"]:
            best_by_key[key] = record

    ranked = sorted(
        best_by_key.values(),
        key=lambda record: (-record["difficulty"], record["canonical_key"]),
    )
    if len(ranked) < 4:
        return None
    return ranked[:4]


def build_option_union_plan(
        p: pr.Problem,
        selected_records: list[dict],
) -> dict:
    """Build the minimal displayed clause closure for all four source goals."""
    seed_points = set().union(*(
        set(record["structural_points"]) for record in selected_records))
    clause_indices = get_clause_dependency_slice(p, seed_points)
    displayed_points = sorted({
        point
        for index in clause_indices
        for point in p.clauses[index].points
    })
    return {
        "seed_points": sorted(seed_points),
        "clause_indices": clause_indices,
        "displayed_points": displayed_points,
        "problem_content": clauses_to_problem_text(p, clause_indices),
    }


def option_point_names(
        candidates: list[tuple], all_problem_point_names: set[str],
) -> set[str]:
    """Extract only real point arguments from final option constructions."""
    return {
        arg
        for candidate in candidates
        for arg in candidate[0].args
        if arg in all_problem_point_names
    }


def run_ddar_nogoal(g: gh.Graph, p: pr.Problem, ignore_point: list = []) -> tuple:
    ddar.solve(g, RULES, p, max_level=10, timeout=120,verbose=LOG_DETAIL)
    candidate_records = []
    all_conclusion_name = ["coll", "cong", "circle", "cyclic", "midp", "para",
                           "perp", "aconst", "eqangle", "eqratio", "rconst", "s_angle", "ncoll", "simtri", "contri", "neqangle", "neqratio"]

    for point, dep in g.cache.items():
        # if point[0] in ['cong', 'coll', 'para', 'perp', 'midp']:
        if (
            # point[0] in ['eqangle', 'eqratio', 'ncoll',
            #              'npara', 'sameside', 'aconst', 'rconst']
            point[0] not in all_conclusion_name
        ) \
            or (
            point[0] in ['cong', 'para']
            and (
                point[1] == point[3] and point[2] == point[4]
                or
                point[1] == point[4] and point[2] == point[3]
            )
        ) \
            or (
            point[0] in ['eqangle']
            and (
                {point[1], point[2]} == {point[5], point[6]} and {
                    point[3], point[4]} == {point[7], point[8]}
                or {point[1], point[2]} == {point[7], point[8]} and {point[3], point[4]} == {point[5], point[6]}
            )
        ):
            continue

        # if point[0] == 'eqangle':
        #     angle1 = pt.pretty_angle(point[1], point[2], point[3], point[4])
        #     angle2 = pt.pretty_angle(point[5], point[6], point[7], point[8])
        #     if "-" in angle1 or "-" in angle2 or angle1 == angle2:
        #         continue
        #     if angle1[2] == angle2[2] and {angle1[1], angle1[3]} == {angle2[1], angle2[3]}:
        #         continue

        for ig_point in ignore_point:
            if ig_point in point:
                continue

        setup, aux, proof_steps, refs = ddar.get_proof_steps(
            g, pr.Construction(point[0], list(point[1:])), merge_trivials=False
        )
        shortest_dep = g.shortest_dependency(
            pr.Dependency(point[0], g.names2nodes(list(point[1:])), None, None)
        )

        if len(proof_steps) == 0:
            continue

        # setup 题目条件
        # aux 辅助条件
        # proof_steps 证明步骤
        # refs 证明编号编号
        # logging.info("setup:", setup)
        # logging.info("aux:", aux)
        # logging.info("proof_steps:", proof_steps)
        # logging.info("refs:", refs)

        # logging.info(f"调用bfs次数:{dep.level}\t证明需要步数:{len(proof_steps)}\t结论:{point}")

        p.goal = pr.Construction(point[0], list(point[1:]))
        detailed_info = write_solution2(g, p)
        used_points = set(detailed_info["used_points"])
        beautiful_proof_steps = detailed_info["proof_steps"]

        # Score the same shortest recorded witness that is emitted as the
        # solution, rather than the first cache entry that discovered it.
        difficulty = get_raw_difficulty(
            detailed_info, shortest_dep.level or dep.level, len(proof_steps))
        goal = pr.Construction(point[0], list(point[1:]))
        candidate_records.append({
            "goal": goal,
            "difficulty": difficulty,
            "proof_used_points": sorted(used_points),
            "proof_steps": beautiful_proof_steps,
            "structural_points": sorted(detailed_info["structural_points"]),
            "search_level": shortest_dep.level or dep.level,
            "proof_step_count": len(proof_steps),
            "canonical_key": canonical_goal_key(goal),
        })

    selected_records = select_global_top_four(candidate_records)
    if not selected_records:
        return None, None, None, None

    target_record = selected_records[0]
    if target_record["difficulty"] < CHALLENGING_PROBLEM_SCORE_THRESHOLD:
        return None, None, None, None

    # ``clauses_to_problem_text`` serializes ``p.goal``.  Reset it before
    # building the union slice because the cache scan temporarily assigned a
    # different goal for each scored candidate.
    p.goal = target_record["goal"]
    union_plan = build_option_union_plan(p, selected_records)
    three_candidates = [
        (record["goal"], record["proof_steps"])
        for record in selected_records[1:]
    ]

    # list[tuple(pr.Construction,bool,str)]
    attempts = 0
    while True:
        if attempts >= 10:
            return None, None, None, None
        mixed_candidates = generate_wrong_answer(
            three_candidates, union_plan["displayed_points"])
        if len(set([i[0].txt() for i in mixed_candidates])) == 3 and len(mixed_candidates) == 3:
            break
        attempts += 1

    all_problem_point_names = {
        point for clause in p.clauses for point in clause.points
    }
    final_candidates = [(target_record["goal"], True, "", target_record["goal"])] + mixed_candidates
    if not option_point_names(final_candidates, all_problem_point_names).issubset(
            set(union_plan["displayed_points"])):
        return None, None, None, None

    if LOG_DETAIL:
        logging.info("全局 Top-4 源结论")
        logging.info([(record["goal"].txt(), record["difficulty"])
                      for record in selected_records])
        logging.info("三个可能错的选项")
        logging.info([(i[0].txt(), i[1], i[3].txt())
                     for i in mixed_candidates])
        logging.info(target_record["goal"].txt())

    return (
        (target_record["goal"].name,) + tuple(target_record["goal"].args),
        target_record["difficulty"],
        mixed_candidates,
        {
            "selected_records": selected_records,
            "union_plan": union_plan,
            "all_problem_point_names": sorted(all_problem_point_names),
        },
    )
    # return False


def handle_one_problem(this_problem: pr.Problem, save_path: str):
    try:
        g, _ = gh.Graph.build_problem(
            this_problem, DEFINITIONS, verbose=LOG_DETAIL)
    except gh.BuildProblemFailError:
        if LOG_DETAIL:
            logging.info(
                f"{this_problem.url} couldn't be create in 10 rebuilds.")
        return {"status": "skipped", "problem_id": this_problem.url,
                "stage": "initial_build_failed"}
    except Exception as error:
        failure = make_generation_failure(
            "initial_build", error, problem_id=this_problem.url)
        logging.error("%s failed during initial build: %s",
                      this_problem.url, failure["error"])
        return {"status": "error", "failure": failure}
    try:
        target_conclusion, proof_score, mixed_candiates, selection_info = run_ddar_nogoal(
            g, this_problem)

        if target_conclusion is None:
            return

        # if proof_score >= GOOD_PROBLEM_SCORE_THRESHOLD:
        this_problem.goal = pr.Construction.from_txt(
            ' '.join(target_conclusion))
        old_url_of_problem = this_problem.url
        source_problem = this_problem

        pr_dict = write_solution2(g, this_problem)
        option_union_plan = selection_info["union_plan"]
        # The published question must define every point used by all four
        # source conclusions, not only the main target.  Rebase the displayed
        # slice and the target's helper-construction difference on that union.
        pr_dict["problem_content"] = option_union_plan["problem_content"]
        pr_dict["structural_clause_indices"] = option_union_plan[
            "clause_indices"]
        pr_dict["structural_points"] = option_union_plan["displayed_points"]
        pr_dict["option_union_structural_points"] = option_union_plan[
            "seed_points"]
        pr_dict["option_union_clause_indices"] = option_union_plan[
            "clause_indices"]
        pr_dict["auxiliary_clause_indices"] = sorted(
            set(pr_dict["proof_clause_indices"])
            - set(option_union_plan["clause_indices"]))
        pr_dict["auxiliary_formal_text"] = get_clauses_txt([
            source_problem.clauses[index]
            for index in pr_dict["auxiliary_clause_indices"]
        ])
        pr_dict["auxiliary_points"] = sorted(
            set(pr_dict["proof_slice_points"])
            - set(option_union_plan["displayed_points"]))
        target_record = selection_info["selected_records"][0]
        proof_score = get_raw_difficulty(
            pr_dict,
            target_record["search_level"],
            target_record["proof_step_count"],
        )
        if LOG_DETAIL:
            for k, v in pr_dict.items():
                logging.info(k)
                logging.info(v)

        four_candidates = [
            (this_problem.goal, True, pr_dict["proof_steps"], this_problem.goal)]
        for info in mixed_candiates:

            four_candidates.append(info)
            # (goal[0], goal[1], temp_pr_dict["proof_steps"]))
        random.shuffle(four_candidates)

        true_answer = ""
        letters = ['A', 'B', 'C', 'D']
        for i in range(4):
            if four_candidates[i][1]:
                true_answer += letters[i]
        # logging.info(true_answer)

        # independent construct must be used
        # INDEPENDENT_CONSTRUCT_ALL_USED = True
        # for arg in this_problem.clauses[0].constructions[0].args:
        #     if arg not in pr_dict["used_points"]:
        #         logging.info(
        #             f"{this_problem.url} is good, but independent construct not used.")
        #         INDEPENDENT_CONSTRUCT_ALL_USED = False
        #         break
        # if not INDEPENDENT_CONSTRUCT_ALL_USED:
        #     continue
        proof_used_points = sorted(set(pr_dict["used_points"]))
        used_points = pr_dict["structural_points"]
        simplified_content = pr_dict["problem_content"]

        this_problem = pr.Problem.from_txt(
            simplified_content, translate=False)
        this_problem.url = old_url_of_problem
        try:
            g, _ = gh.Graph.build_problem(
                this_problem, DEFINITIONS, verbose=LOG_DETAIL)
        except gh.BuildProblemFailError:
            if LOG_DETAIL:
                logging.info(
                    f"{this_problem.url} first success, but failed after deleting.")
            save_validation_failure(
                save_path,
                source_problem,
                this_problem,
                pr_dict,
                "structural_build_failed",
                four_candidates,
                true_answer,
            )
            return

        # The full source construction was already solved to select the goal.
        # The structural question intentionally hides proof-only clauses, so a
        # direct DD+AR proof here would reject exactly the questions that need
        # an auxiliary construction. The clause-set difference, rather than
        # this solver outcome, defines that property.
        needs_auxiliary_construction = bool(
            pr_dict["auxiliary_clause_indices"])
        structural_goal_proved = None
        if VALIDATE_STRUCTURAL_GOAL:
            ddar.solve(g, RULES, this_problem, max_level=10,
                       timeout=120, verbose=LOG_DETAIL)
            structural_goal_proved = g.check(
                this_problem.goal.name,
                g.names2points(this_problem.goal.args),
            )

        # drawer = drawing.ProblemDrawing(this_problem, g.copy())
        display_plan = build_display_rewrite_plan(this_problem)
        question_zh = translate_problem_to_natural_language(
            display_plan.display_problem, "zh", used_points=used_points)
        option_points = option_point_names(
            four_candidates, set(selection_info["all_problem_point_names"]))
        missing_formal_points = sorted(option_points - set(used_points))
        missing_question_points = sorted(
            point for point in option_points
            if point.upper() not in question_zh
        )
        if missing_formal_points or missing_question_points:
            failure = {
                "stage": "option_point_visibility_validation",
                "problem_id": this_problem.url,
                "missing_formal_points": missing_formal_points,
                "missing_question_points": missing_question_points,
            }
            logging.error("%s failed option-point visibility validation: %s",
                          this_problem.url, failure)
            return {"status": "skipped", "problem_id": this_problem.url,
                    "stage": failure["stage"], "failure": failure}
        try:
            drawer = drawing.ProblemDrawing(
                this_problem,
                g,
                suppressed_circle_construction_ids=(
                    display_plan.suppressed_circle_construction_ids),
            )
            drawer.draw_problem(
                save_path=save_path+"/"+this_problem.url+".png",
                used_points=used_points.copy(),
                conclusions=four_candidates)
        except gh.BuildProblemFailError:
            if LOG_DETAIL:
                logging.info(
                    f"{this_problem.url} failed when initing drawer.")
            return

        simplified_content = simplified_content.split('?')[0].rstrip()

        # final_problem = this_problem.txt()+" ? "+" ".join(target_conclusion)
        if LOG_DETAIL:
            logging.info(f"ID：{this_problem.url}\n")
            logging.info(f"问题：{simplified_content}\n")
            logging.info(f'用点：{used_points}\n')
            logging.info(
                f'翻译：{question_zh}'
                f'则下列选项中正确的有：\n'
                f'A. {translate_goals_to_natural_language((four_candidates[0][0].name,) + tuple(four_candidates[0][0].args), "zh", used_points=used_points)}\n'
                f'B. {translate_goals_to_natural_language((four_candidates[1][0].name,) + tuple(four_candidates[1][0].args), "zh", used_points=used_points)}\n'
                f'C. {translate_goals_to_natural_language((four_candidates[2][0].name,) + tuple(four_candidates[2][0].args), "zh", used_points=used_points)}\n'
                f'D. {translate_goals_to_natural_language((four_candidates[3][0].name,) + tuple(four_candidates[3][0].args), "zh", used_points=used_points)}'
            )
            logging.info(f"难度：{proof_score}\n")
            logging.info(f"答案：{true_answer}\n")

        gen_problem_txt = {
            "ID": this_problem.url,
            "Question_zh": question_zh,
            "A_zh": translate_goals_to_natural_language((four_candidates[0][0].name,) + tuple(four_candidates[0][0].args), "zh", used_points=used_points),
            "B_zh": translate_goals_to_natural_language((four_candidates[1][0].name,) + tuple(four_candidates[1][0].args), "zh", used_points=used_points),
            "C_zh": translate_goals_to_natural_language((four_candidates[2][0].name,) + tuple(four_candidates[2][0].args), "zh", used_points=used_points),
            "D_zh": translate_goals_to_natural_language((four_candidates[3][0].name,) + tuple(four_candidates[3][0].args), "zh", used_points=used_points),
            "Question_en": "",
            "A_en": translate_goals_to_natural_language((four_candidates[0][0].name,) + tuple(four_candidates[0][0].args), "en", used_points=used_points),
            "B_en": translate_goals_to_natural_language((four_candidates[1][0].name,) + tuple(four_candidates[1][0].args), "en", used_points=used_points),
            "C_en": translate_goals_to_natural_language((four_candidates[2][0].name,) + tuple(four_candidates[2][0].args), "en", used_points=used_points),
            "D_en": translate_goals_to_natural_language((four_candidates[3][0].name,) + tuple(four_candidates[3][0].args), "en", used_points=used_points),
            "Answer": true_answer,
            "Prior_Difficulty": proof_score,
            "Posterior_Difficulty": 0,
            "SimplifiedFormalText": simplified_content,
            "DisplayFormalText": display_plan.display_problem.txt().split(
                '?')[0].rstrip(),
            "DisplayRewriteRecords": display_plan.records,
            "UsedPoints": used_points,
            "ProofUsedPoints": proof_used_points,
            "ProofSetupPoints": pr_dict["proof_setup_points"],
            "ProofAuxiliaryPoints": pr_dict["proof_auxiliary_points"],
            "ProofSlicePoints": pr_dict["proof_slice_points"],
            "StructuralPoints": pr_dict["structural_points"],
            "StructuralDependencyPoints": pr_dict[
                "structural_dependency_points"],
            "AuxiliaryPoints": pr_dict["auxiliary_points"],
            "StructuralClauseIndices": pr_dict["structural_clause_indices"],
            "ProofClauseIndices": pr_dict["proof_clause_indices"],
            "AuxiliaryClauseIndices": pr_dict["auxiliary_clause_indices"],
            "AuxiliaryFormalText": pr_dict["auxiliary_formal_text"],
            "SuggestedAuxiliaryFormalText": pr_dict[
                "auxiliary_formal_text"],
            "AuxiliaryConstructionCount": len(
                pr_dict["auxiliary_clause_indices"]),
            "StructuralGoalProved": structural_goal_proved,
            "StructuralGoalValidationStatus": (
                "checked" if VALIDATE_STRUCTURAL_GOAL else "not_checked"),
            "NeedsAuxiliaryConstruction": needs_auxiliary_construction,
            "OptionSelectionMode": "global_top4",
            "TargetSourceDifficulty": target_record["difficulty"],
            "OptionSourceCandidates": [
                {
                    "rank": index + 1,
                    "formal": record["goal"].txt(),
                    "source_difficulty": record["difficulty"],
                    "structural_points": record["structural_points"],
                    "proof_used_points": record["proof_used_points"],
                }
                for index, record in enumerate(
                    selection_info["selected_records"])
            ],
            "OptionUnionStructuralPoints": pr_dict[
                "option_union_structural_points"],
            "OptionUnionClauseIndices": pr_dict[
                "option_union_clause_indices"],
            "OptionPointNames": sorted(option_points),
            "OptionPointVisibilityValidation": "passed",
            "premises": pr_dict["theorem_premises"],
            "ProofSteps_A": four_candidates[0][2],
            "ProofSteps_B": four_candidates[1][2],
            "ProofSteps_C": four_candidates[2][2],
            "ProofSteps_D": four_candidates[3][2],
        }
        atomic_json(os.path.join(save_path, "audit", this_problem.url + ".json"), gen_problem_txt)
        atomic_json(os.path.join(save_path, this_problem.url + ".json"), compact_payload(gen_problem_txt))
        return {"status": "generated", "problem_id": this_problem.url}

    except Exception as error:
        failure = make_generation_failure(
            "handle_problem", error, problem_id=this_problem.url)
        logging.error("%s failed while generating: %s",
                      this_problem.url, failure["error"])
        return {"status": "error", "failure": failure}


def draw_one_problem(this_problem: pr.Problem, save_path: str):
    try:
        logging.info(translate_problem_to_natural_language(this_problem, "zh", [
            chr(char) for char in range(ord('a'), ord('z') + 1)]))

        try:
            g, _ = gh.Graph.build_problem(
                this_problem, DEFINITIONS, verbose=LOG_DETAIL)
        except gh.BuildProblemFailError:
            logging.info(
                f"{this_problem.url} couldn't be create in 10 rebuilds.")
            return

        drawer = drawing.ProblemDrawing(this_problem, g.copy())
        drawer.draw_problem(save_path=save_path+"/"+this_problem.url+".png",
                            used_points=[chr(char) for char in range(ord('a'), ord('z') + 1)])
    except Exception:
        return


def pre_handle_one_problem(args):
    idx, save_problem_path, input_dir = args
    file_path = os.path.join(input_dir, f'problems_{idx}.txt')
    summary = {
        "input_index": idx,
        "input_file": file_path,
        "input_read_succeeded": False,
        "processed": 0,
        "generated": 0,
        "failures": [],
    }

    try:
        problems = pr.Problem.from_txt_file(
            file_path, to_dict=True, translate='ddar' not in MODE
        )
    except Exception as error:
        summary["failures"].append(make_generation_failure(
            "read_input_file", error, input_index=idx, input_file=file_path))
        return summary

    summary["input_read_succeeded"] = True

    for this_problem in problems.values():
        summary["processed"] += 1
        try:
            if MODE == 'ngddarOneByOne':
                result = handle_one_problem(this_problem, save_problem_path)
                if result and result.get("status") == "generated":
                    summary["generated"] += 1
                if result and result.get("status") == "error":
                    summary["failures"].append(result["failure"])
            elif MODE == 'onlyDrawOneByOne':
                draw_one_problem(this_problem, save_problem_path)
            else:
                raise ValueError(f"Unknown FLAGS.mode: {MODE}")
        except Exception as error:
            # This is a final task-boundary guard. A malformed one-off
            # question must not escape the worker and abort Pool.imap.
            summary["failures"].append(make_generation_failure(
                "process_problem",
                error,
                problem_id=this_problem.url,
                input_index=idx,
                input_file=file_path,
            ))
    return summary


def _shard_label() -> str:
    """Return a filename-safe shard label for independent progress files."""
    raw_label = FLAGS.shard_id.strip()
    if not raw_label:
        raw_label = f"files_{FLAGS.file_start}_{FLAGS.file_end}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_label)


def _requested_file_indices() -> list[int]:
    """Resolve either an explicit shard list or the traditional index range."""
    explicit = FLAGS.file_indices.strip()
    if explicit:
        values = []
        seen = set()
        for token in explicit.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                index = int(token)
            except ValueError as error:
                raise ValueError(f"Invalid --file_indices item: {token!r}") from error
            if index < 0:
                raise ValueError("--file_indices cannot contain negative values")
            if index not in seen:
                values.append(index)
                seen.add(index)
        if not values:
            raise ValueError("--file_indices did not contain any valid index")
        return values
    if FLAGS.file_start < 0 or FLAGS.file_end <= FLAGS.file_start:
        raise ValueError("Require 0 <= --file_start < --file_end")
    return list(range(FLAGS.file_start, FLAGS.file_end))


def _completed_input_indices(progress_path: str) -> set[int]:
    """Read durable per-file checkpoints; malformed lines are ignored safely."""
    completed = set()
    if not os.path.isfile(progress_path):
        return completed
    with open(progress_path, "r", encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
                if record.get("status") == "completed":
                    completed.add(int(record["input_index"]))
            except (ValueError, TypeError, json.JSONDecodeError, KeyError):
                logging.warning("Ignoring malformed progress record in %s", progress_path)
    return completed


def _append_progress(progress_file, task_result: dict) -> None:
    """Checkpoint one fully read source file after its worker has returned."""
    if not task_result.get("input_read_succeeded"):
        return
    record = {
        "status": "completed",
        "input_index": task_result["input_index"],
        "input_file": task_result["input_file"],
        "processed": task_result.get("processed", 0),
        "generated": task_result.get("generated", 0),
        "failure_count": len(task_result.get("failures", [])),
    }
    progress_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    progress_file.flush()
    os.fsync(progress_file.fileno())


def main(_):
    global DEFINITIONS
    global RULES

    if FLAGS.workers < 1:
        raise ValueError("--workers must be at least 1")
    input_dir = os.path.abspath(FLAGS.input_dir)
    if not os.path.isdir(input_dir):
        raise ValueError(f"Input directory does not exist: {input_dir}")

    DEFINITIONS = pr.Definition.from_txt_file(_paths.DEFS_PATH, to_dict=True)
    RULES = pr.Theorem.from_txt_file(_paths.RULES_PATH, to_dict=True)

    save_problem_path = (os.path.abspath(FLAGS.output_dir) if FLAGS.output_dir else
                         os.path.join(_paths.OUTPUT_DIR, datetime.now().strftime('%Y%m%d_%H_%M_%S')))
    os.makedirs(save_problem_path, exist_ok=bool(FLAGS.output_dir))

    shard_label = _shard_label()
    progress_path = os.path.join(save_problem_path, f"progress_{shard_label}.jsonl")
    requested_indices = _requested_file_indices()
    completed_indices = _completed_input_indices(progress_path) if FLAGS.resume else set()
    tasks = [(idx, save_problem_path, input_dir)
             for idx in requested_indices if idx not in completed_indices]
    logging.info(
        "Shard %s: requested=%d, already completed=%d, pending=%d, workers=%d",
        shard_label, len(requested_indices), len(completed_indices), len(tasks), FLAGS.workers)

    failure_path = os.path.join(save_problem_path, f"generation_failures_{shard_label}.jsonl")
    failure_count = 0
    generated_count = 0
    processed_count = 0
    with open(progress_path, "a", encoding="utf-8") as progress_file:
        with open(failure_path, "a", encoding="utf-8") as failure_log:
            def consume_results(results):
                nonlocal failure_count, generated_count, processed_count
                for task_result in tqdm(results, total=len(tasks), desc=f"Shard {shard_label}"):
                    task_result = task_result or {}
                    generated_count += task_result.get("generated", 0)
                    processed_count += task_result.get("processed", 0)
                    failures = task_result.get("failures", [])
                    for failure in failures:
                        failure_log.write(json.dumps(failure, ensure_ascii=False) + "\n")
                        failure_log.flush()
                        failure_count += 1
                    _append_progress(progress_file, task_result)

            # A shard launcher already provides outer parallelism.  Avoid a
            # nested Pool for its normal workers=1 mode.
            if FLAGS.workers == 1:
                consume_results(map(pre_handle_one_problem, tasks))
            else:
                with Pool(processes=FLAGS.workers) as pool:
                    consume_results(pool.imap(pre_handle_one_problem, tasks))

    logging.info(
        "Shard %s completed: %d source problems, %d published questions, %d isolated failures.",
        shard_label, processed_count, generated_count, failure_count)


if __name__ == '__main__':
    app.run(main)
