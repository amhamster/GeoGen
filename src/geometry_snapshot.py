"""Persist successful numerical points; restore drawing state without construction."""
import hashlib
import math

import graph as gh
import numericals as nm
import problem as pr


def formal_digest(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def capture_graph(graph, formal_text):
    points = {}
    for point in graph.all_points():
        xy = [float(point.num.x), float(point.num.y)]
        if not all(math.isfinite(value) for value in xy):
            raise ValueError(f"Nonfinite coordinate: {point.name}")
        points[point.name] = xy
    return {"format": "geogen_points_v1", "formal_sha256": formal_digest(formal_text), "points": points}


def restore_graph(snapshot, formal_text, required_names=()):
    """Restore only points. ProblemDrawing reconstructs visible lines/circles.

    This is deliberately not a proof graph. Never run DDAR on this object.
    No Graph.build_problem(), Graph.copy(), numerical sketch or resampling.
    """
    if snapshot.get("format") != "geogen_points_v1":
        raise ValueError("Unsupported coordinate snapshot format")
    if snapshot.get("formal_sha256") != formal_digest(formal_text):
        raise ValueError("Coordinate snapshot does not match original construction")
    problem = pr.Problem.from_txt(formal_text, translate=False)
    expected = {name for clause in problem.clauses for name in clause.points}
    points = snapshot.get("points", {})
    if set(points) != expected or not set(required_names).issubset(expected):
        raise ValueError("Coordinate snapshot has missing/extra point names")
    graph = gh.Graph()
    for point in graph.add_points(sorted(expected)):
        xy = points[point.name]
        if (not isinstance(xy, (list, tuple)) or len(xy) != 2
                or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in xy)):
            raise ValueError(f"Invalid coordinate: {point.name}")
        point.num = nm.Point(float(xy[0]), float(xy[1]))
    graph.url = problem.url
    return graph
