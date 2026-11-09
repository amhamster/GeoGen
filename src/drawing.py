import graph as gh
from geometry import Circle
import numericals as nm
from matplotlib.transforms import Affine2D
import numpy as np
import problem as pr






def is_letter(char: str):
    return 'a' <= char <= 'z'


class ProblemDrawing:
    """绘图相关"""

    def __init__(self, p, g, suppressed_circle_construction_ids=None):
        self.g = g
        self.p = p
        self.suppressed_circle_construction_ids = set(
            suppressed_circle_construction_ids or [])
        # name_to_point dict
        self.n2p = {point.name: point for point in g.type2nodes[gh.Point]}

    def clear(self):
        # 清空
        self.g.type2nodes[gh.Circle] = []
        self.g._pair2line = {}
        self.g._triplet2circle = {}
        self.g.type2nodes[gh.Line] = []

    def draw_line_and_circle(
            self,
            name,
            args,
            used_points: list[str],
            suppress_circle: bool = False,
    ):
        # 主体函数: get_line_thru_pair, get_circle_thru_triplet
        n2p = self.n2p
        g = self.g
        used = tuple(arg.upper() in (point.upper() for point in used_points)
                     for arg in args if arg.isalpha())
        # 两个点
        if name == "segment":
            p1, p2 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
        # 三个点
        if name in [
            "midpoint",
            "on_line",
            "triangle",
            "eq_triangle",
            "iso_triangle",
            "mirror",
            "r_triangle",
            "risos",
            "triangle12",
            "ieq_triangle",
            "nsquare",
            "psquare",
        ]:
            p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p1, p3)
        elif name in ["lc_tangent"]:
            p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
        elif name in ["on_circle"]:
            if not suppress_circle:
                center, point = [n2p[n] for n in args[-2:] if is_letter(n)]
                circle = g.new_node(Circle, f"({center.name},{point.name})")
                circle.num = nm.Circle(center.num, p1=point.num)
                circle.points = center, point
        elif name in ["on_bline", "on_dia"]:
            p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
        elif name == "on_opline":
            p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p2, p3)
        elif name in ['incenter', 'excenter', 'incenter2', 'excenter2']:
            d, a, b, c = [n2p[n] for n in args[-4:] if is_letter(n)]
            g.get_line_thru_pair(a, b)
            g.get_line_thru_pair(a, c)
            g.get_line_thru_pair(b, c)
            a, b, c = sorted([a, b, c], key=lambda x: x.name.lower())
            circle = g.new_node(Circle, f'({d.name},h.{a.name}{b.name})')
            p = d.num.foot(nm.Line(a.num, b.num))
            circle.num = nm.Circle(d.num, p1=p)
            circle.points = d, a, b, c
        elif name in ['circle']:
            center, p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            if not suppress_circle:
                circle = g.new_node(Circle, f'({center.name},{p1.name})')
                circle.num = nm.Circle(center.num, p1=p1.num)
                circle.points = center, p1
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p3)
        # 四个点
        elif name in ["angle_bisector", "angle_mirror"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p4, p3)
        elif name in [
            "eq_quadrangle",
            "eq_trapezoid",
            "eqangle2",
            "parallelogram",
            "quadrangle",
            "r_trapezoid",
            "rectangle",
            "square",
            "isquare",
            "trapezoid",
        ]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p4, p1)
        elif name in ["eqdia_quadrangle"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p4, p1)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p4)
            g.get_line_thru_pair(p3, p4)
        elif name in ["intersection_lc"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p4, p1)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p4)
            g.get_line_thru_pair(p3, p4)
            if not suppress_circle:
                center, point = [n2p[n] for n in args[-2:] if is_letter(n)]
                circle = g.new_node(Circle, f"({center.name},{point.name})")
                circle.num = nm.Circle(center.num, p1=point.num)
                circle.points = center, point
        elif name in ["eqdistance", "on_pline", "on_tline"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p3, p4)
        elif name in ["foot"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p3, p4)
        elif name in ["intersection_cc", "shift"]:
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p4)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p3, p4)
        elif name == "reflect":
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p3, p4)
        elif name == "s_angle":
            p1, p2, p3 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
        elif name == "trisegment":
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p3, p4)
        elif name == "on_circum":
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p2, p3, p4)
        elif name == "orthocenter":
            p1, p2, p3, p4 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p2, p4)
            g.get_line_thru_pair(p3, p4)
        # 五个点
        elif name == "intersection_ll":
            p1, p2, p3, p4, p5 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p1, p4)
            g.get_line_thru_pair(p1, p5)
            g.get_line_thru_pair(p4, p5)
        elif name == "pentagon":
            p1, p2, p3, p4, p5 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p5, p1)
        elif name == "trisect":
            p1, p2, p3, p4, p5 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p3, p5)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p1, p4)
            g.get_line_thru_pair(p2, p4)
        elif name == "tangent":
            p1, p2, p3, p4, p5 = [n2p[n] for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p1, p2, p5)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p3)
        # 六个点
        elif name in ["intersection_lp", "intersection_lt"]:
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p1, p4)
            g.get_line_thru_pair(p5, p6)
        elif name == "on_aline":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p5, p6)
        elif name == "on_aline2":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p5, p6)
        elif name == "e5128":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p1, p4, p6)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p3, p6)
            g.get_line_thru_pair(p1, p2)
        elif name == "3peq":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p4, p6)
            g.get_line_thru_pair(p5, p6)
            g.get_line_thru_pair(p2, p4)
            g.get_line_thru_pair(p2, p6)
            g.get_line_thru_pair(p3, p6)
            g.get_line_thru_pair(p3, p5)
            g.get_line_thru_pair(p1, p4)
            g.get_line_thru_pair(p1, p5)
        elif name == "cc_tangent0":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            circle = g.new_node(Circle, f"({p3.name},{p4.name})")
            circle.num = nm.Circle(p3.num, p4.num)
            circle.points = p3, p4
            circle = g.new_node(Circle, f"({p5.name},{p6.name})")
            circle.num = nm.Circle(p5.num, p6.num)
            circle.points = p5, p6
        elif name == "eqangle3":
            p1, p2, p3, p4, p5, p6 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p4, p6)
        # 七个点
        elif name == "centroid":
            p1, p2, p3, p4, p5, p6, p7 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p5, p6)
            g.get_line_thru_pair(p5, p7)
            g.get_line_thru_pair(p6, p7)
        elif name == "ninepoints":
            p1, p2, p3, p4, p5, p6, p7 = [n2p[n] for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p1, p2, p3)
            g.get_line_thru_pair(p5, p6)
            g.get_line_thru_pair(p5, p7)
            g.get_line_thru_pair(p6, p7)
        elif name in ["intersection_pp", "intersection_tt"]:
            p1, p2, p3, p4, p5, p6, p7 = [n2p[n] for n in args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p1, p5)
            g.get_line_thru_pair(p6, p7)
        # 八个点
        elif name == "2l1c":
            p1, p2, p3, p4, p5, p6, p7, p8 = [n2p[n]
                                              for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p3, p5, p6)
            g.get_circle_thru_triplet(p1, p2, p3)
            g.get_line_thru_pair(p5, p7)
            g.get_line_thru_pair(p6, p7)
        elif name == "cc_tangent":
            p1, p2, p3, p4, p5, p6, p7, p8 = [n2p[n]
                                              for n in args if is_letter(n)]
            g.get_circle_thru_triplet(p1, p3, p6)
            g.get_circle_thru_triplet(p2, p4, p8)
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p3, p4)

    def draw_goal(self, goal: pr.Construction):
        n2p = self.n2p
        g = self.g

        if goal.name == "midp":
            p1, p2, p3 = [n2p[n] for n in goal.args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p1, p3)
        elif goal.name in ["para", "npara", "perp", "nperp", "cong", "ncong", "rconst", "aconst", "s_angle"]:
            if len(goal.args) == 3:
                goal.args.insert(1, goal.args[1])
            p1, p2, p3, p4 = [n2p[n] for n in goal.args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p3, p4)
        elif goal.name in ["simtri", "contri"]:
            p1, p2, p3, p4, p5, p6 = [n2p[n]
                                      for n in goal.args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p2, p3)
            g.get_line_thru_pair(p1, p3)
            g.get_line_thru_pair(p4, p5)
            g.get_line_thru_pair(p4, p6)
            g.get_line_thru_pair(p5, p6)
        elif goal.name in ["eqangle", "eqratio"]:
            p1, p2, p3, p4, p5, p6, p7, p8 = [n2p[n]
                                              for n in goal.args if is_letter(n)]
            g.get_line_thru_pair(p1, p2)
            g.get_line_thru_pair(p3, p4)
            g.get_line_thru_pair(p5, p6)
            g.get_line_thru_pair(p7, p8)

    def make_graph_user_friendly(self):
        first_construction = self.p.clauses[0].constructions[0]
        first_construction_name = first_construction.name
        seed_names = [
            name for name in first_construction.args if isinstance(name, str) and is_letter(name)
        ]
        points_by_name = {p.name: p for p in self.g.type2nodes[gh.Point]}
        seed_points = [points_by_name[name] for name in seed_names if name in points_by_name]
        if len(seed_points) < 3:
            fallback_points = sorted(
                self.g.type2nodes[gh.Point], key=lambda p: p.name.lower()
            )
            seed_points = (seed_points + fallback_points)[:3]
        if len(seed_points) < 2:
            return

        point_a = seed_points[0]
        point_b = seed_points[1]
        point_c = seed_points[2] if len(seed_points) > 2 else seed_points[1]

        # first, rotate the whole graph
        # if trapezoid, rectangle or isquare, then ab // bottom margain, else bc // bottom margain
        if any(name in first_construction_name for name in ["trapezoid", "rectangle", "isquare"]) or len(seed_points) < 3:
            angle = np.arctan2(point_b.num.y-point_a.num.y,
                               point_b.num.x-point_a.num.x) * 180 / np.pi
        else:
            angle = np.arctan2(point_c.num.y-point_b.num.y,
                               point_c.num.x-point_b.num.x) * 180 / np.pi
        rotation = Affine2D().rotate_deg(-angle)

        for p in self.g.type2nodes[gh.Point]:
            p.num.x, p.num.y = rotation.transform_point((p.num.x, p.num.y))
        for c in self.g.type2nodes[gh.Circle]:
            c.num.a, c.num.b = rotation.transform_point((c.num.a, c.num.b))
            c.num.center = nm.Point(c.num.a, c.num.b)

        # second, let args more ordered
        # make sure that y_a >= y_b, if not satisfied, flip the whole graph with y=y_b
        y0 = point_b.num.y
        if point_a.num.y < y0:
            for p in self.g.type2nodes[gh.Point]:
                p.num.y = 2*y0-p.num.y
            for c in self.g.type2nodes[gh.Circle]:
                c.num.b = 2*y0-c.num.b
                c.num.center = nm.Point(c.num.a, c.num.b)

    def draw_problem(self, save_path=None, used_points=None, conclusions=None):
        self.clear()

        if not used_points:
            used_points = [chr(char) for char in range(ord('a'), ord('z') + 1)]
        # 画条件
        for clause_index, clause in enumerate(self.p.clauses):
            for construction_index, construction in enumerate(clause.constructions):
                self.draw_line_and_circle(
                    construction.name,
                    construction.args,
                    used_points,
                    suppress_circle=(
                        (clause_index, construction_index)
                        in self.suppressed_circle_construction_ids),
                )

        # 不画目标
        # if self.p.goal is not None:
        #     self.draw_goal(self.p.goal)
        if conclusions:
            for conclusion in conclusions:
                self.draw_goal(conclusion[0])

        if used_points is not None:
            self.g.type2nodes[gh.Point] = [
                p for p in self.g.type2nodes[gh.Point] if self.n2p[p.name].name in used_points]
            self.g.type2nodes[gh.Line] = [l for l in self.g.type2nodes[gh.Line]
                                          if self.n2p[l.name[0]].name in used_points and self.n2p[l.name[1]].name in used_points]

        self.make_graph_user_friendly()

        gh.nm.draw(
            self.g.type2nodes[gh.Point],
            self.g.type2nodes[gh.Line],
            self.g.type2nodes[gh.Circle],
            self.g.type2nodes[gh.Segment],
            save_to=save_path,
            theme='black-and-light-blue'
        )

