"""Optional aesthetic search BEFORE DDAR and coordinate snapshot capture."""
import math
import random

import numpy as np

from aestheticsEvaluator import GeometryAestheticsEvaluator
from display_rewrite import build_display_rewrite_plan
from drawing import ProblemDrawing
from free_params import build_registry_for_problem
from geometry_snapshot import capture_graph, restore_graph
import graph as gh
import problem as pr


def layout_loss(graph, problem):
    formal = problem.txt()
    snapshot = capture_graph(graph, formal)
    points = list(snapshot["points"])
    shown = restore_graph(snapshot, formal, points)
    plan = build_display_rewrite_plan(problem)
    drawer = ProblemDrawing(problem, shown, plan.suppressed_circle_construction_ids)
    drawer.clear()
    for i, clause in enumerate(problem.clauses):
        for j, construction in enumerate(clause.constructions):
            drawer.draw_line_and_circle(construction.name, construction.args, points,
                                       suppress_circle=(i, j) in plan.suppressed_circle_construction_ids)
    coords = {p.name: np.array([p.num.x, p.num.y]) for p in shown.all_points()}
    lines = [tuple(p.name for p in line.points) for line in shown.type2nodes[gh.Line]]
    circles = [(c.num.center.x, c.num.center.y, c.num.radius) for c in shown.type2nodes[gh.Circle]]
    return float(GeometryAestheticsEvaluator(coords, lines, "auto", circles=circles).compute_total_loss())


def choose_layout(problem, definitions, original_graph, trials, seed):
    """Search valid free-parameter layouts, never moving individual points arbitrarily.

    The selected COMPLETE construction is solved by DDAR afterwards. Failed
    candidates do not discard the already successful original layout.
    """
    record = {"enabled": bool(trials), "requested_trials": trials, "valid_trials": 0,
              "failed_trials": 0, "selected": "original"}
    if not trials:
        return original_graph, record
    registry = build_registry_for_problem(problem)
    if not registry.total_size():
        record["reason"] = "no_registered_free_parameters"
        return original_graph, record
    try:
        initial_loss = layout_loss(original_graph, problem)
    except Exception as error:
        record["reason"] = "initial_layout_cannot_be_scored: " + str(error)
        return original_graph, record
    if not math.isfinite(initial_loss):
        record["reason"] = "nonfinite_initial_loss"
        return original_graph, record
    best_graph, best_loss = original_graph, initial_loss
    rng = np.random.default_rng(seed)
    for trial in range(trials):
        parameters = [float(rng.uniform(low, high)) for low, high in registry.bounds()]
        random.seed((seed + trial * 104729) % (2 ** 32))
        np.random.seed((seed + trial * 104729) % (2 ** 32))
        candidate_problem = pr.Problem.from_txt(problem.txt(), translate=False)
        candidate_problem.goal = None
        try:
            candidate, _ = gh.Graph.build_problem(candidate_problem, definitions, verbose=False,
                                                  free_params_iter=registry.iter_slices(parameters))
            loss = layout_loss(candidate, candidate_problem)
            if not math.isfinite(loss):
                raise ValueError("Nonfinite aesthetic loss")
            record["valid_trials"] += 1
            if loss < best_loss:
                best_graph, best_loss = candidate, loss
                record["selected"] = trial
        except Exception:
            record["failed_trials"] += 1
    record.update(initial_loss=initial_loss, selected_loss=best_loss)
    return best_graph, record
