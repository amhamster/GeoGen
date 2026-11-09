"""Presentation-only rewrites for generated geometry questions.

The canonical ``Problem`` remains the source of truth for construction,
deduction and option selection.  This module only produces an equivalent
problem description for natural-language rendering and a list of circle arcs
that may be omitted from the diagram.
"""

from dataclasses import dataclass

import problem as pr


ConstructionId = tuple[int, int]


@dataclass
class DisplayRewritePlan:
    """A display representation derived from an unchanged canonical problem."""

    display_problem: pr.Problem
    suppressed_circle_construction_ids: set[ConstructionId]
    records: list[dict]


def _copy_clause_with_constructions(
        clause: pr.Clause,
        constructions: list[pr.Construction],
) -> pr.Clause:
    """Copy a clause without mutating the canonical construction objects."""
    copied = pr.Clause(list(clause.points), constructions)
    copied.nums = list(clause.nums)
    return copied


def _circumcircle_has_visible_use(
        problem: pr.Problem,
        source_id: ConstructionId,
        center: str,
        vertices: tuple[str, str, str],
) -> bool:
    """Whether the circumcircle must remain visible after P0/P1 rewrites.

    ``on_circle`` and ``intersection_lc`` do not keep a circle alive: they
    are always shown as equal-length conditions.  The remaining checks are
    conservative; retaining an arc is preferable to hiding a circle needed
    to understand a non-rewritten circular construction.
    """
    vertex_set = frozenset(vertices)
    for clause_index, clause in enumerate(problem.clauses):
        for construction_index, construction in enumerate(clause.constructions):
            if (clause_index, construction_index) == source_id:
                continue
            args = construction.args
            name = construction.name

            if name == "on_circum" and len(args) >= 4:
                if frozenset(args[1:4]) == vertex_set:
                    return True
            elif name == "intersection_cc" and len(args) >= 4:
                if (args[1] == center or args[2] == center) and args[3] in vertex_set:
                    return True
            elif name == "lc_tangent" and len(args) >= 3:
                if args[2] == center and args[1] in vertex_set:
                    return True
            elif name == "tangent" and len(args) >= 5:
                if args[3] == center and args[4] in vertex_set:
                    return True
            elif name == "2l1c" and len(args) >= 8:
                if args[7] == center and frozenset(args[4:7]) == vertex_set:
                    return True
            elif name == "cc_tangent0" and len(args) >= 6:
                if args[2] == center and args[3] in vertex_set:
                    return True
                if args[4] == center and args[5] in vertex_set:
                    return True
            elif name == "cc_tangent" and len(args) >= 8:
                if args[4] == center and args[5] in vertex_set:
                    return True
                if args[6] == center and args[7] in vertex_set:
                    return True
    return False


def build_display_rewrite_plan(problem: pr.Problem) -> DisplayRewritePlan:
    """Build P0/P1/P3 display rewrites without changing ``problem``.

    P0: ``on_circle X O A`` is displayed as ``XO = OA``.
    P1: ``intersection_lc X A O B`` is displayed as collinearity on ``AB``
        and ``OX = OB``.
    P3: a ``circle O A B C`` construction is not drawn when no other
        non-rewritten construction visibly uses that circumcircle.
    """
    records = []
    suppressed = set()
    display_clauses = []

    for clause_index, clause in enumerate(problem.clauses):
        display_constructions = []
        for construction_index, construction in enumerate(clause.constructions):
            source_id = (clause_index, construction_index)
            name = construction.name
            args = list(construction.args)

            if name == "on_circle" and len(args) >= 3:
                point, center, radius_point = args[:3]
                display_constructions.append(
                    pr.Construction("eqdistance", [point, center, center, radius_point]))
                suppressed.add(source_id)
                records.append({
                    "rule": "on_circle_to_equal_length",
                    "source": construction.txt(),
                    "display_formal": (
                        f"eqdistance {point} {center} {center} {radius_point}"),
                    "display_zh": (
                        f"{point.upper()}{center.upper()}={center.upper()}{radius_point.upper()}"),
                    "suppressed_circle": {
                        "kind": "center_radius",
                        "center": center,
                        "radius_point": radius_point,
                    },
                })
                continue

            if name == "intersection_lc" and len(args) >= 4:
                point, line_a, center, line_b = args[:4]
                display_constructions.extend([
                    pr.Construction("on_line", [point, line_a, line_b]),
                    pr.Construction("eqdistance", [point, center, center, line_b]),
                ])
                suppressed.add(source_id)
                records.append({
                    "rule": "intersection_lc_to_collinear_equal_length",
                    "source": construction.txt(),
                    "display_formal": (
                        f"on_line {point} {line_a} {line_b}, "
                        f"eqdistance {point} {center} {center} {line_b}"),
                    "display_zh": (
                        f"点{point.upper()}在直线{line_a.upper()}{line_b.upper()}上，且"
                        f"{point.upper()}{center.upper()}={center.upper()}{line_b.upper()}"),
                    "suppressed_circle": {
                        "kind": "center_radius",
                        "center": center,
                        "radius_point": line_b,
                    },
                })
                continue

            display_constructions.append(
                pr.Construction(name, args))

            if name == "circle" and len(args) >= 4:
                center = args[0]
                vertices = tuple(args[1:4])
                if not _circumcircle_has_visible_use(
                        problem, source_id, center, vertices):
                    suppressed.add(source_id)
                    records.append({
                        "rule": "circumcircle_arc_hidden_for_circumcenter",
                        "source": construction.txt(),
                        "display_formal": construction.txt(),
                        "display_zh": (
                            f"点{center.upper()}是△{''.join(x.upper() for x in vertices)}的外心"),
                        "suppressed_circle": {
                            "kind": "circumcircle",
                            "center": center,
                            "vertices": list(vertices),
                        },
                    })

        display_clauses.append(
            _copy_clause_with_constructions(clause, display_constructions))

    display_problem = pr.Problem(problem.url, display_clauses, problem.goal)
    return DisplayRewritePlan(display_problem, suppressed, records)
