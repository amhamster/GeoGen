import problem as pr
from pretty import pretty_angle
import random


def get_used_three_intersection(
    args: tuple,
    used: tuple,
    language: str
):
    separator = "、" if language == "zh" else ", "
    if not any(used[0:3]):
        return None, None
    added_edges = ""
    added_points = ""
    for i in range(0, 3):
        if used[i]:
            added_edges += separator
            added_points += separator
            for j in range(0, 3):
                if j != i:
                    added_edges += args[j+4]
            added_points += args[i]
    return added_edges.lstrip(separator), added_points.lstrip(separator)


def translate_construction_to_chinese(
    construction: pr.Construction,
    idx: int,
    used_points: list[str],
) -> str:
    name = construction[idx].name
    args = tuple(arg.upper() for arg in construction[idx].args)
    used = tuple(arg in (point.upper() for point in used_points)
                 for arg in args if arg.isalpha())

    if not used[0] and name not in ['s_angle', 'incenter2', 'excenter2', 'centroid', 'ninepoints']:
        return None
    if not any(used[1:]):
        if used[0]:
            return f"{args[0]}是平面内任意一点"
        else:
            return None

    if name in ['incenter2', 'excenter2', 'centroid', 'ninepoints']:
        edges_list, points_list = get_used_three_intersection(args, used, "zh")
    else:
        edges_list, points_list = None, None

    if name == "angle_bisector":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"{args[2]}{args[0]}平分∠{args[1]}{args[2]}{args[3]}"
    elif name == "angle_mirror":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"{args[2]}{args[3]}平分∠{args[1]}{args[2]}{args[0]}"
    elif name == "circle" or name == "circumcenter":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}是△{args[1]}{args[2]}{args[3]}的外心"
    elif name == "eq_quadrangle":
        return f"在四边形{args[0]}{args[1]}{args[2]}{args[3]}中，{args[0]}{args[3]}={args[1]}{args[2]}"
    elif name == "eq_trapezoid":
        return f"在等腰梯形{args[0]}{args[1]}{args[2]}{args[3]}中，{args[0]}{args[1]}∥{args[2]}{args[3]}，{args[0]}{args[3]}={args[1]}{args[2]}"
    elif name == "eq_triangle":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"△{args[0]}{args[1]}{args[2]}是等边三角形"
    elif name == "eqangle2":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"∠{args[2]}{args[1]}{args[0]}=∠{args[0]}{args[3]}{args[2]}"
    elif name == "eqdia_quadrangle":
        return f"在四边形{args[0]}{args[1]}{args[2]}{args[3]}中，{args[0]}{args[2]}={args[1]}{args[3]}"
    elif name == "eqdistance":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"{args[0]}{args[1]}={args[2]}{args[3]}"
    elif name == "foot":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"过点{args[1]}作{args[2]}{args[3]}的垂线，垂足为{args[0]}"
    elif name == "free":
        return f"{args[0]}是平面内任意一点"
    elif name == "incenter":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}是△{args[1]}{args[2]}{args[3]}的内心"
    elif name == "incenter2":
        if edges_list is None:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的内心圆⊙{args[3]}"
            else:
                return None
        else:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的内心圆⊙{args[3]}，与{edges_list}相切于{points_list}"
            else:
                return f"△{args[4]}{args[5]}{args[6]}的内心圆与{edges_list}相切于{points_list}"
    elif name == "excenter":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"作△{args[1]}{args[2]}{args[3]}的{args[1]}-旁心圆⊙{args[0]}"
    elif name == "excenter2":
        if edges_list is None:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的{args[4]}-旁心圆⊙{args[3]}"
            else:
                return None
        else:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的{args[4]}-旁心圆⊙{args[3]}，与{edges_list}相切于{points_list}"
            else:
                return f"△{args[4]}{args[5]}{args[6]}的{args[4]}-旁心圆与{edges_list}相切于{points_list}"
    elif name == "centroid":
        if edges_list is None:
            if used[3]:
                return f"点{args[3]}是△{args[4]}{args[5]}{args[6]}的质心"
            else:
                return None
        else:
            if used[3]:
                return f"点{args[3]}是△{args[4]}{args[5]}{args[6]}的质心，{points_list}是{edges_list}的中点"
            else:
                return f"{points_list}是{edges_list}的中点"
    elif name == "ninepoints":
        if edges_list is None:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的九点圆⊙{args[3]}"
            else:
                return None
        else:
            if used[3]:
                return f"作△{args[4]}{args[5]}{args[6]}的九点圆⊙{args[3]}，与{edges_list}相交于{points_list}"
            else:
                # return f"△{args[4]}{args[5]}{args[6]}的九点圆与{edges_list}相交于{points_list}"
                return f"{points_list}是{edges_list}的中点"
    elif name == "intersection_cc":
        return f"点{args[0]}和点{args[3]}关于直线{args[1]}{args[2]}对称"
    elif name == "intersection_lc":
        return f"直线{args[1]}{args[3]}交以{args[2]}{args[3]}为半径的⊙{args[2]}于点{args[0]}、{args[3]}"
    elif name == "intersection_ll":
        if all(used[1:3]) and all(used[3:5]):
            return f"直线{args[1]}{args[2]}和{args[3]}{args[4]}相交于点{args[0]}"
        elif not all(used[1:3]):
            return f"点{args[0]}在直线{args[3]}{args[4]}上"
        elif not all(used[3:5]):
            return f"点{args[0]}在直线{args[1]}{args[2]}上"
        else:
            return None
    elif name == "intersection_lp":
        if all(used[1:3]) and all(used[3:6]):
            return f"过点{args[3]}作{args[4]}{args[5]}的平行线交直线{args[1]}{args[2]}于{args[0]}"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"过点{args[3]}作{args[4]}{args[5]}的平行线{args[3]}{args[0]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"点{args[0]}在直线{args[1]}{args[2]}上"
        else:
            return None
    elif name == "intersection_lt":
        if all(used[1:3]) and all(used[3:6]):
            return f"过点{args[3]}作{args[4]}{args[5]}的垂线交直线{args[1]}{args[2]}于{args[0]}"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"过点{args[3]}作{args[4]}{args[5]}的垂线{args[3]}{args[0]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"点{args[0]}在直线{args[1]}{args[2]}上"
        else:
            return None
    elif name == "intersection_pp":
        if all(used[1:4]) and all(used[4:7]):
            return f"过点{args[1]}作{args[2]}{args[3]}的平行线，该直线交过点{args[4]}作{args[5]}{args[6]}的平行线于{args[0]}"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"过点{args[4]}作{args[5]}{args[6]}的平行线{args[4]}{args[0]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"过点{args[1]}作{args[2]}{args[3]}的平行线{args[1]}{args[0]}"
        else:
            return None
    elif name == "intersection_tt":
        if all(used[1:4]) and all(used[4:7]):
            return f"过点{args[1]}作{args[2]}{args[3]}的垂线，该直线交过点{args[4]}作{args[5]}{args[6]}的垂线于{args[0]}"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"过点{args[4]}作{args[5]}{args[6]}的垂线{args[4]}{args[0]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"过点{args[1]}作{args[2]}{args[3]}的垂线{args[1]}{args[0]}"
        else:
            return None
    elif name == "iso_triangle":
        return f"在△{args[0]}{args[1]}{args[2]}中，{args[0]}{args[1]}={args[0]}{args[2]}"
    elif name == "lc_tangent":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"{args[1]}{args[2]}⊥{args[1]}{args[0]}"
    elif name == "midpoint":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}是{args[1]}{args[2]}的中点"
    elif name == "mirror":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}、{args[1]}关于点{args[2]}对称"
    elif name == "nsquare" or name == "psquare":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"以{args[1]}{args[2]}为直角边、∠{args[1]}为直角作等腰Rt△{args[1]}{args[2]}{args[0]}"
    elif name == "on_aline":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"∠{args[0]}{args[1]}{args[2]}=∠{args[3]}{args[4]}{args[5]}"
    elif name == "on_aline2":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"∠{args[1]}{args[0]}{args[2]}=∠{args[3]}{args[4]}{args[5]}"
    elif name == "on_bline":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}在{args[1]}{args[2]}的垂直平分线上"
    elif name == "on_circle":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}在以{args[1]}{args[2]}为半径的⊙{args[1]}上"
    elif name == "on_line" or name == "on_opline":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}在直线{args[1]}{args[2]}上"
    elif name == "on_pline":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"过点{args[1]}作{args[2]}{args[3]}的平行线{args[0]}{args[1]}"
    elif name == "on_tline":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"过点{args[1]}作{args[2]}{args[3]}的垂线{args[0]}{args[1]}"
    elif name == "orthocenter":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}是△{args[1]}{args[2]}{args[3]}的垂心"
    elif name == "parallelogram":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"四边形{args[0]}{args[1]}{args[2]}{args[3]}是平行四边形"
    elif name == "pentagon":
        return f"在五边形{args[0]}{args[1]}{args[2]}{args[3]}{args[4]}中"
    elif name == "quadrangle":
        return f"在四边形{args[0]}{args[1]}{args[2]}{args[3]}中"
    elif name == "r_trapezoid":
        return f"在直角梯形{args[0]}{args[1]}{args[2]}{args[3]}中，{args[0]}{args[1]}∥{args[2]}{args[3]}，∠{args[0]}为直角"
    elif name == "r_triangle":
        if all(used[0:3]):
            return f"在Rt△{args[0]}{args[1]}{args[2]}中，{args[0]}{args[1]}⊥{args[0]}{args[2]}"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"给定线段{args[1]}{args[2]}"
            elif not used[1]:
                return f"给定线段{args[0]}{args[2]}"
            elif not used[2]:
                return f"给定线段{args[0]}{args[1]}"
        else:
            return None
    elif name == "rectangle":
        return f"在矩形{args[0]}{args[1]}{args[2]}{args[3]}中"
    elif name == "reflect":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}、{args[1]}关于直线{args[2]}{args[3]}对称"
    elif name == "risos":
        if all(used[0:3]):
            return f"在等腰Rt△{args[0]}{args[1]}{args[2]}中，∠{args[0]}为直角"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"给定线段{args[1]}{args[2]}"
            elif not used[1]:
                return f"给定线段{args[0]}{args[2]}"
            elif not used[2]:
                return f"给定线段{args[0]}{args[1]}"
        else:
            return None
    elif name == "s_angle":
        return f"∠{args[0]}{args[1]}{args[2]}={args[3]}°"
    elif name == "segment":
        return f"在直线{args[0]}{args[1]}中"
    elif name == "shift":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"四边形{args[0]}{args[1]}{args[3]}{args[2]}是平行四边形"
        # return f"{args[0]}{args[1]}={args[2]}{args[3]}，{args[0]}{args[2]}={args[1]}{args[3]}"
    elif name == "square":
        if used[2] and used[3]:
            return f"以{args[0]}{args[1]}为边构造正方形{args[0]}{args[1]}{args[2]}{args[3]}"
        elif used[2] and not used[3]:
            return f"以{args[0]}{args[1]}为边、∠{args[1]}为直角，构造等腰Rt△{args[0]}{args[1]}{args[2]}"
        elif not used[2] and used[3]:
            return f"以{args[0]}{args[1]}为边、∠{args[1]}为直角，构造等腰Rt△{args[1]}{args[0]}{args[3]}"
        else:
            return None

    elif name == "isquare":
        return f"在正方形{args[0]}{args[1]}{args[2]}{args[3]}中"
    elif name == "trapezoid":
        return f"在梯形{args[0]}{args[1]}{args[2]}{args[3]}中，{args[0]}{args[1]}∥{args[2]}{args[3]}"
    elif name == "triangle":
        if all(used[0:3]):
            return f"在△{args[0]}{args[1]}{args[2]}中"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"给定线段{args[1]}{args[2]}"
            elif not used[1]:
                return f"给定线段{args[0]}{args[2]}"
            elif not used[2]:
                return f"给定线段{args[0]}{args[1]}"
        else:
            return None
    elif name == "triangle12":
        return f"在△{args[0]}{args[1]}{args[2]}中，{args[0]}{args[1]}:{args[0]}{args[2]}=1:2"
    elif name == "2l1c":
        return f"作⊙{args[3]}，使其分别与直线{args[4]}{args[6]}、{args[5]}{args[6]}相切于{args[0]}、{args[1]}，且与以{args[7]}{args[4]}为半径的⊙{args[7]}相切于{args[2]}"
    elif name == "e5128":
        return f"无效构造"
    elif name == "3peq":
        return f"点{args[0]}、{args[1]}、{args[2]}分别在△{args[3]}{args[4]}{args[5]}三边上，且{args[1]}是{args[0]}{args[2]}的中点"
    elif name == "trisect":
        return f"∠{args[2]}{args[3]}{args[4]}的三等分线交{args[2]}{args[4]}于{args[0]}和{args[1]}"
    elif name == "trisegment":
        return f"点{args[0]}、{args[1]}三等分线段{args[2]}{args[3]}"
    elif name == "on_dia":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"{args[1]}{args[0]}⊥{args[2]}{args[0]}"
    elif name == "ieq_triangle":
        return f"在等边△{args[0]}{args[1]}{args[2]}中"
    elif name == "cc_tangent0":
        return f"直线{args[0]}{args[1]}是以{args[2]}{args[3]}为半径的⊙{args[2]}和以{args[4]}{args[5]}为半径的⊙{args[4]}的公切线，切点分别为{args[0]}、{args[1]}"
    elif name == "cc_tangent":
        return f"直线{args[0]}{args[1]}和直线{args[2]}{args[3]}是以{args[4]}{args[5]}为半径的⊙{args[4]}和以{args[6]}{args[7]}为半径的⊙{args[6]}的公切线，切点分别为{args[0]}、{args[1]}、{args[2]}、{args[3]}"
    elif name == "eqangle3":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"∠{args[1]}{args[0]}{args[2]}=∠{args[4]}{args[3]}{args[5]}"
    elif name == "tangent":
        if used[0] and used[1]:
            return f"过点{args[2]}引以{args[3]}{args[4]}为半径的⊙{args[3]}的两条切线{args[2]}{args[0]}和{args[2]}{args[1]}，切点为{args[0]}、{args[1]}"
        elif used[0] and not used[1]:
            return f"过点{args[2]}引以{args[3]}{args[4]}为半径⊙{args[3]}的切线{args[2]}{args[0]}，切点为{args[0]}"
        elif not used[0] and used[1]:
            return f"过点{args[2]}引以{args[3]}{args[4]}为半径⊙{args[3]}的切线{args[2]}{args[1]}，切点为{args[1]}"
        else:
            return None
    elif name == "on_circum":
        if not all(used[1:]):
            return f"{args[0]}是平面内任意一点"
        return f"点{args[0]}在以点{args[1]}、{args[2]}、{args[3]}确定的圆上"
    else:
        return None


def translate_construction_to_english(
    construction: pr.Construction,
    idx: int,
    used_points: list[str],
) -> str:
    name = construction[idx].name
    args = tuple(arg.upper() for arg in construction[idx].args)
    used = tuple(arg in (point.upper() for point in used_points)
                 for arg in args if arg.isalpha())

    if not used[0] and name not in ['s_angle', 'incenter2', 'excenter2', 'centroid', 'ninepoints']:
        return None
    if not any(used[1:]):
        if used[0]:
            return f"{args[0]} is a free point"
        else:
            return None

    if name in ['incenter2', 'excenter2', 'centroid', 'ninepoints']:
        edges_list, points_list = get_used_three_intersection(args, used, "en")
    else:
        edges_list, points_list = None, None

    if name == "angle_bisector":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[2]}{args[0]} bisects ∠{args[1]}{args[2]}{args[3]}"
    elif name == "angle_mirror":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[2]}{args[3]} bisects ∠{args[1]}{args[2]}{args[0]}"
    elif name == "circle" or name == "circumcenter":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} is the circumcenter of △{args[1]}{args[2]}{args[3]}"
    elif name == "eq_quadrangle":
        return f"Given quadrilateral {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[3]}={args[1]}{args[2]}"
    elif name == "eq_trapezoid":
        return f"Given isosceles trapezoid {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[1]}∥{args[2]}{args[3]}, {args[0]}{args[3]}={args[1]}{args[2]}"
    elif name == "eq_triangle":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"△{args[0]}{args[1]}{args[2]} is an equilateral triangle"
    elif name == "eqangle2":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"∠{args[2]}{args[1]}{args[0]}=∠{args[0]}{args[3]}{args[2]}"
    elif name == "eqdia_quadrangle":
        return f"Given quadrilateral {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[2]}={args[1]}{args[3]}"
    elif name == "eqdistance":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[0]}{args[1]}={args[2]}{args[3]}"
    elif name == "foot":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Draw a perpendicular from {args[1]} to {args[2]}{args[3]}, meeting {args[2]}{args[3]} at {args[0]}"
    elif name == "free":
        return f"{args[0]} is a free point"
    elif name == "incenter":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} is the incenter of △{args[1]}{args[2]}{args[3]}"
    elif name == "incenter2":
        if edges_list is None:
            if used[3]:
                return f"Construct the incircle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}"
            else:
                return None
        else:
            if used[3]:
                return f"Construct the incircle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}, tangent to {edges_list} at {points_list}, respectively"
            else:
                return f"Construct the incircle of △{args[4]}{args[5]}{args[6]}, tangent to {edges_list} at {points_list}, respectively"
    elif name == "excenter":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Construct the {args[1]}-excircle ⊙{args[0]} of △{args[1]}{args[2]}{args[3]}"
    elif name == "excenter2":
        if edges_list is None:
            if used[3]:
                return f"Construct the {args[4]}-excircle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}"
            else:
                return None
        else:
            if used[3]:
                return f"Construct the {args[4]}-excircle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}, tangent to {edges_list} at {points_list}, respectively"
            else:
                return f"Construct the {args[4]}-excircle of △{args[4]}{args[5]}{args[6]}, tangent to {edges_list} at {points_list}, respectively"
    elif name == "centroid":
        if edges_list is None:
            if used[3]:
                return f"Point {args[3]} is the centroid of △{args[4]}{args[5]}{args[6]}"
            else:
                return None
        else:
            if used[3]:
                return f"Point {args[3]} is the centroid of △{args[4]}{args[5]}{args[6]}. {points_list} are the midpoints of {edges_list}, respectively"
            else:
                return f"{points_list} are the midpoints of {edges_list}, respectively"
    elif name == "ninepoints":
        if edges_list is None:
            if used[3]:
                return f"Construct the nine-point circle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}"
            else:
                return None
        else:
            if used[3]:
                return f"Construct the nine-point circle ⊙{args[3]} of △{args[4]}{args[5]}{args[6]}, intersecting {edges_list} at {points_list}, respectively"
            else:
                return f"{points_list} are the midpoints of {edges_list}, respectively"
    elif name == "intersection_cc":
        return f"Points {args[0]} and {args[3]} are symmetric with respect to line {args[1]}{args[2]}"
    elif name == "intersection_lc":
        return f"Line {args[1]}{args[3]} intersects the circle ⊙{args[2]} with radius {args[2]}{args[3]} at points {args[0]} and {args[3]}"
    elif name == "intersection_ll":
        if all(used[1:3]) and all(used[3:5]):
            return f"Lines {args[1]}{args[2]} and {args[3]}{args[4]} intersect at point {args[0]}"
        elif not all(used[1:3]):
            return f"Point {args[0]} lies on line {args[3]}{args[4]}"
        elif not all(used[3:5]):
            return f"Point {args[0]} lies on line {args[1]}{args[2]}"
        else:
            return None
    elif name == "intersection_lp":
        if all(used[1:3]) and all(used[3:6]):
            return f"Through point {args[3]}, draw a line parallel to {args[4]}{args[5]}, intersecting line {args[1]}{args[2]} at {args[0]}"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"Through point {args[3]}, draw a line {args[3]}{args[0]} parallel to {args[4]}{args[5]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"Point {args[0]} lies on line {args[1]}{args[2]}"
        else:
            return None
    elif name == "intersection_lt":
        if all(used[1:3]) and all(used[3:6]):
            return f"Through point {args[3]}, draw a line perpendicular to {args[4]}{args[5]}, intersecting line {args[1]}{args[2]} at {args[0]}"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"Through point {args[3]}, draw a line {args[3]}{args[0]} perpendicular to {args[4]}{args[5]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"Point {args[0]} lies on line {args[1]}{args[2]}"
        else:
            return None
    elif name == "intersection_pp":
        if all(used[1:4]) and all(used[4:7]):
            return f"Through point {args[1]}, draw a line parallel to {args[2]}{args[3]}, intersecting the line through {args[4]} parallel to {args[5]}{args[6]} at {args[0]}"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"Through point {args[4]}, draw a line {args[4]}{args[0]} parallel to {args[5]}{args[6]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"Through point {args[1]}, draw a line {args[1]}{args[0]} parallel to {args[2]}{args[3]}"
        else:
            return None
    elif name == "intersection_tt":
        if all(used[1:4]) and all(used[4:7]):
            return f"Through point {args[1]}, draw a line perpendicular to {args[2]}{args[3]}, intersecting the line through {args[4]} perpendicular to {args[5]}{args[6]} at {args[0]}"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"Through point {args[4]}, draw a line {args[4]}{args[0]} perpendicular to {args[5]}{args[6]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"Through point {args[1]}, draw a line {args[1]}{args[0]} perpendicular to {args[2]}{args[3]}"
        else:
            return None
    elif name == "iso_triangle":
        return f"Given triangle {args[0]}{args[1]}{args[2]} with {args[0]}{args[1]}={args[0]}{args[2]}"
    elif name == "lc_tangent":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[1]}{args[2]}⊥{args[1]}{args[0]}"
    elif name == "midpoint":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[0]} is the midpoint of {args[1]}{args[2]}"
    elif name == "mirror":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Points {args[0]} and {args[1]} are symmetric with respect to point {args[2]}"
    elif name == "nsquare" or name == "psquare":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Construct an isosceles right triangle {args[1]}{args[2]}{args[0]} with {args[1]}{args[2]} as one side and ∠{args[1]} as the right angle"
    elif name == "on_aline":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"∠{args[0]}{args[1]}{args[2]}=∠{args[3]}{args[4]}{args[5]}"
    elif name == "on_aline2":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"∠{args[1]}{args[0]}{args[2]}=∠{args[3]}{args[4]}{args[5]}"
    elif name == "on_bline":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} lies on the perpendicular bisector of {args[1]}{args[2]}"
    elif name == "on_circle":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} lies on the circle ⊙{args[1]} with radius {args[1]}{args[2]}"
    elif name == "on_line" or name == "on_opline":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} lies on line {args[1]}{args[2]}"
    elif name == "on_pline":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Through point {args[1]}, draw a line {args[0]}{args[1]} parallel to {args[2]}{args[3]}"
    elif name == "on_tline":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Through point {args[1]}, draw a line {args[0]}{args[1]} perpendicular to {args[2]}{args[3]}"
    elif name == "orthocenter":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} is the orthocenter of △{args[1]}{args[2]}{args[3]}"
    elif name == "parallelogram":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Quadrilateral {args[0]}{args[1]}{args[2]}{args[3]} is a parallelogram"
    elif name == "pentagon":
        return f"Given pentagon {args[0]}{args[1]}{args[2]}{args[3]}{args[4]}"
    elif name == "quadrangle":
        return f"Given quadrilateral {args[0]}{args[1]}{args[2]}{args[3]}"
    elif name == "r_trapezoid":
        return f"Given a right trapezoid {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[1]}∥{args[2]}{args[3]}, and ∠{args[0]} as the right angle"
    elif name == "r_triangle":
        if all(used[0:3]):
            return f"Given right triangle {args[0]}{args[1]}{args[2]} with {args[0]}{args[1]}⊥{args[0]}{args[2]}"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"Given segment {args[1]}{args[2]}"
            elif not used[1]:
                return f"Given segment {args[0]}{args[2]}"
            elif not used[2]:
                return f"Given segment {args[0]}{args[1]}"
        else:
            return None
    elif name == "rectangle":
        return f"Given rectangle {args[0]}{args[1]}{args[2]}{args[3]}"
    elif name == "reflect":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Points {args[0]} and {args[1]} are symmetric with respect to line {args[2]}{args[3]}"
    elif name == "risos":
        if all(used[0:3]):
            return f"Given isosceles right triangle {args[0]}{args[1]}{args[2]} with ∠{args[0]} as the right angle"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"Given segment {args[1]}{args[2]}"
            elif not used[1]:
                return f"Given segment {args[0]}{args[2]}"
            elif not used[2]:
                return f"Given segment {args[0]}{args[1]}"
        else:
            return None
    elif name == "s_angle":
        return f"∠{args[0]}{args[1]}{args[2]}={args[3]}°"
    elif name == "segment":
        return f"Given segment {args[0]}{args[1]}"
    elif name == "shift":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Quadrilateral {args[0]}{args[1]}{args[3]}{args[2]} is a parallelogram"
    elif name == "square":
        if used[2] and used[3]:
            return f"Construct a square {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[1]} as one side"
        elif used[2] and not used[3]:
            return f"Construct an isosceles right triangle {args[0]}{args[1]}{args[2]} with {args[0]}{args[1]} as one side and ∠{args[1]} as the right angle"
        elif not used[2] and used[3]:
            return f"Construct an isosceles right triangle {args[1]}{args[0]}{args[3]} with {args[0]}{args[1]} as one side and ∠{args[1]} as the right angle"
        else:
            return None

    elif name == "isquare":
        return f"Given square {args[0]}{args[1]}{args[2]}{args[3]}"
    elif name == "trapezoid":
        return f"Given trapezoid {args[0]}{args[1]}{args[2]}{args[3]} with {args[0]}{args[1]}∥{args[2]}{args[3]}"
    elif name == "triangle":
        if all(used[0:3]):
            return f"Given triangle {args[0]}{args[1]}{args[2]}"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"Given segment {args[1]}{args[2]}"
            elif not used[1]:
                return f"Given segment {args[0]}{args[2]}"
            elif not used[2]:
                return f"Given segment {args[0]}{args[1]}"
        else:
            return None
    elif name == "triangle12":
        return f"Given triangle {args[0]}{args[1]}{args[2]} with {args[0]}{args[1]}:{args[0]}{args[2]}=1:2"
    elif name == "2l1c":
        return f"Construct circle ⊙{args[3]}, tangent to lines {args[4]}{args[6]} and {args[5]}{args[6]} at {args[0]} and {args[1]}, respectively, and tangent to circle ⊙{args[7]} with radius {args[7]}{args[4]} at {args[2]}"
    elif name == "e5128":
        return f"invalid"
    elif name == "3peq":
        return f"Points {args[0]}, {args[1]}, {args[2]} lie on the three sides of triangle {args[3]}{args[4]}{args[5]}, respectively, with {args[1]} being the midpoint of {args[0]}{args[2]}"
    elif name == "trisect":
        return f"The trisectors of ∠{args[2]}{args[3]}{args[4]} intersect {args[2]}{args[4]} at points {args[0]} and {args[1]}"
    elif name == "trisegment":
        return f"Points {args[0]} and {args[1]} trisect segment {args[2]}{args[3]}"
    elif name == "on_dia":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"{args[1]}{args[0]}⊥{args[2]}{args[0]}"
    elif name == "ieq_triangle":
        return f"Given equilateral triangle {args[0]}{args[1]}{args[2]}"
    elif name == "cc_tangent0":
        return f"Line {args[0]}{args[1]} is a common tangent to the circle ⊙{args[2]} with radius {args[2]}{args[3]} and the circle ⊙{args[4]} with radius {args[4]}{args[5]}, with points of tangency {args[0]} and {args[1]}, respectively"
    elif name == "cc_tangent":
        return f"Line {args[0]}{args[1]} and {args[2]}{args[3]} are common tangents to the circle ⊙{args[4]} with radius {args[4]}{args[5]} and the circle ⊙{args[6]} with radius {args[6]}{args[7]}, with points of tangency {args[0]}, {args[1]}, {args[2]} and {args[3]} respectively"
    elif name == "eqangle3":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"∠{args[1]}{args[0]}{args[2]}=∠{args[4]}{args[3]}{args[5]}"
    elif name == "tangent":
        if used[0] and used[1]:
            return f"Through point {args[2]}, two tangents {args[2]}{args[0]} and {args[2]}{args[1]} are drawn to the circle ⊙{args[3]} with radius {args[3]}{args[4]}, with the point of tangency at {args[0]} and {args[1]}, respectively"
        elif used[0] and not used[1]:
            return f"Through point {args[2]}, a tangent {args[2]}{args[0]} is drawn to the circle ⊙{args[3]} with radius {args[3]}{args[4]}, with the point of tangency at {args[0]}"
        elif not used[0] and used[1]:
            return f"Through point {args[2]}, a tangent {args[2]}{args[1]} is drawn to the circle ⊙{args[3]} with radius {args[3]}{args[4]}, with the point of tangency at {args[1]}"
        else:
            return None
    elif name == "on_circum":
        if not all(used[1:]):
            return f"{args[0]} is a free point"
        return f"Point {args[0]} lies on the circle determined by points {args[1]}, {args[2]}, and {args[3]}"
    else:
        return None


def translate_construction_to_chinese_two(
    construction: pr.Construction,
    used_points: list[str],
) -> str:
    name1 = construction[0].name
    args1 = tuple(arg.upper() for arg in construction[0].args)
    used1 = tuple(arg in (point.upper() for point in used_points)
                  for arg in args1 if arg.isalpha())

    name2 = construction[1].name
    args2 = tuple(arg.upper() for arg in construction[1].args)
    used2 = tuple(arg in (point.upper() for point in used_points)
                  for arg in args2 if arg.isalpha())

    if not all(used1) and not all(used2):
        if used1[0] and used2[0]:
            return f"{args1[0]}是平面内任意一点"
        else:
            return None
    elif not all(used1):
        return translate_construction_to_chinese(construction, 1, used_points)
    elif not all(used2):
        return translate_construction_to_chinese(construction, 0, used_points)

    special_phrase = ["angle_bisector", "on_bline", "on_circle",
                      "on_circum", "on_line", "on_pline", "on_tline"]
    # "eqdistance", "s_angle", "on_dia"

    def special_phrase_translation(name, args):
        if name == "angle_bisector":
            return f"∠{args[1]}{args[2]}{args[3]}的角平分线{args[2]}{args[0]}"
        elif name == "on_bline":
            return f"{args[1]}{args[2]}的垂直平分线"
        elif name == "on_circle":
            return f"以{args[1]}{args[2]}为半径的⊙{args[1]}"
        elif name == "on_circum":
            return f"点{args[1]}、{args[2]}、{args[3]}确定的圆"
        elif name == "on_line":
            return f"直线{args[1]}{args[2]}"
        elif name == "on_pline":
            return f"过点{args[1]}作{args[2]}{args[3]}的平行线"
        elif name == "on_tline":
            return f"过点{args[1]}作{args[2]}{args[3]}的垂线"
        else:
            return None
    if name2 in ["on_pline", "on_tline"]:
        if name1 in special_phrase:
            return f"{special_phrase_translation(name2,args2)}，该直线交{special_phrase_translation(name1,args1)}于{args1[0]}"
        else:
            return f"{translate_construction_to_chinese(construction,1,used_points)}，且{translate_construction_to_chinese(construction,0,used_points)}"

    elif name1 in special_phrase and name2 in special_phrase:
        if name1 in ["on_pline", "on_tline"]:
            return f"{special_phrase_translation(name1,args1)}，该直线交{special_phrase_translation(name2,args2)}于{args1[0]}"
        else:
            return f"{special_phrase_translation(name1,args1)}交{special_phrase_translation(name2,args2)}于{args1[0]}"
    elif name1 not in special_phrase and name2 in special_phrase:
        return f"{translate_construction_to_chinese(construction,1,used_points)}，且{translate_construction_to_chinese(construction,0,used_points)}"
    elif name1 in special_phrase and name2 not in special_phrase:
        return f"{translate_construction_to_chinese(construction,0,used_points)}，且{translate_construction_to_chinese(construction,1,used_points)}"
    else:
        return f"{translate_construction_to_chinese(construction,0,used_points)}，{translate_construction_to_chinese(construction,1,used_points)}"


def translate_construction_to_english_two(
    construction: pr.Construction,
    used_points: list[str],
) -> str:
    name1 = construction[0].name
    args1 = tuple(arg.upper() for arg in construction[0].args)
    used1 = tuple(arg in (point.upper() for point in used_points)
                  for arg in args1 if arg.isalpha())

    name2 = construction[1].name
    args2 = tuple(arg.upper() for arg in construction[1].args)
    used2 = tuple(arg in (point.upper() for point in used_points)
                  for arg in args2 if arg.isalpha())

    if not all(used1) and not all(used2):
        if used1[0] and used2[0]:
            return f"{args1[0]} is a free point"
        else:
            return None
    elif not all(used1):
        return translate_construction_to_chinese(construction, 1, used_points)
    elif not all(used2):
        return translate_construction_to_chinese(construction, 0, used_points)

    special_phrase = ["angle_bisector", "on_bline", "on_circle",
                      "on_circum", "on_line", "on_pline", "on_tline"]
    # "eqdistance", "s_angle", "on_dia"

    def special_phrase_translation(name, args):
        if name == "angle_bisector":
            return f"the angle bisector {args[2]}{args[0]} of ∠{args[1]}{args[2]}{args[3]}"
        elif name == "on_bline":
            return f"the perpendicular bisector of {args[1]}{args[2]}"
        elif name == "on_circle":
            return f"circle ⊙{args[1]} with radius {args[1]}{args[2]}"
        elif name == "on_circum":
            return f"circle determined by points {args[1]}, {args[2]}, and {args[3]}"
        elif name == "on_line":
            return f"line {args[1]}{args[2]}"
        elif name == "on_pline":
            return f"through point {args[1]}, draw a line parallel to {args[2]}{args[3]}"
        elif name == "on_tline":
            return f"through point {args[1]}, draw a line perpendicular to {args[2]}{args[3]}"
        else:
            return None
    if name2 in ["on_pline", "on_tline"]:
        if name1 in special_phrase:
            return f"{special_phrase_translation(name2,args2)}, and this line intersects {special_phrase_translation(name1,args1)} at {args1[0]}"
        else:
            return f"{translate_construction_to_english(construction,1,used_points)}, and {translate_construction_to_english(construction,0,used_points)}"

    elif name1 in special_phrase and name2 in special_phrase:
        if name1 in ["on_pline", "on_tline"]:
            return f"{special_phrase_translation(name1,args1)}, and this line intersects {special_phrase_translation(name2,args2)} at {args1[0]}"
        else:
            return f"{special_phrase_translation(name1,args1)} intersects {special_phrase_translation(name2,args2)} at {args1[0]}"
    elif name1 not in special_phrase and name2 in special_phrase:
        return f"{translate_construction_to_english(construction,1,used_points)}, and {translate_construction_to_english(construction,0,used_points)}"
    elif name1 in special_phrase and name2 not in special_phrase:
        return f"{translate_construction_to_english(construction,0,used_points)}, and {translate_construction_to_english(construction,1,used_points)}"
    else:
        return f"{translate_construction_to_english(construction,0,used_points)}, {translate_construction_to_english(construction,1,used_points)}"


def translate_goals_to_chinese(this_goal: tuple, used_points: list) -> str:
    name = this_goal[0]
    args = tuple(arg.upper() for arg in this_goal[1:])

    if name == "aconst":
        frac = args[4].split("PI/")
        degree = int(frac[0])*180/int(frac[1])
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} = {degree}°"
    elif name == "coll":
        return '' + '、'.join(args) + '共线'
    elif name == "cong":
        return f"{args[0]}{args[1]} = {args[2]}{args[3]}"
    elif name == "circle":
        return f"{args[1]}、{args[2]}、{args[3]}在⊙{args[0]}上"
    elif name == "cyclic":
        return '' + '、'.join(args) + '共圆'
    elif name == "eqangle":
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} = {pretty_angle(args[4],args[5],args[6],args[7])}"
    elif name == "eqratio":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} = {args[4]}{args[5]}:{args[6]}{args[7]}"
    elif name == "neqangle":
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} ≠ {pretty_angle(args[4],args[5],args[6],args[7])}"
    elif name == "neqratio":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} ≠ {args[4]}{args[5]}:{args[6]}{args[7]}"
    elif name == "midp":
        return f"{args[0]}是{args[1]}{args[2]}的中点"
    elif name == "ncoll":
        return '' + '、'.join(args) + '不共线'
    elif name == "npara":
        return f"{args[0]}{args[1]}和{args[2]}{args[3]}不平行"
    elif name == "nperp":
        return f"{args[0]}{args[1]}和{args[2]}{args[3]}不垂直"
    elif name == "ncong":
        return f"{args[0]}{args[1]} ≠ {args[2]}{args[3]}"
    elif name == "para":
        return f"{args[0]}{args[1]}和{args[2]}{args[3]}平行"
    elif name == "perp":
        return f"{args[0]}{args[1]}和{args[2]}{args[3]}垂直"
    elif name == "rconst":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} = {args[4]}"
    elif name == "sameside":
        return f"线段{args[2]}{args[3]}、{args[4]}{args[5]}在直线{args[0]}{args[1]}同侧"
    elif name == "simtri":
        return f"△{args[0]}{args[1]}{args[2]}与△{args[3]}{args[4]}{args[5]}相似"
    elif name == "contri":
        return f"△{args[0]}{args[1]}{args[2]}与△{args[3]}{args[4]}{args[5]}全等"
    else:
        raise ValueError(f"unrecognized goal {name}")


def translate_goals_to_english(this_goal: tuple, used_points: list) -> str:
    name = this_goal[0]
    args = tuple(arg.upper() for arg in this_goal[1:])

    if name == "aconst":
        frac = args[4].split("PI/")
        degree = int(frac[0])*180/int(frac[1])
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} = {degree}°"
    elif name == "coll":
        return '' + ','.join(args) + ' are collinear'
    elif name == "cong":
        return f"{args[0]}{args[1]} = {args[2]}{args[3]}"
    elif name == "circle":
        return f'{args[0]} is the circumcenter of △{args[1]}{args[2]}{args[3]}'
    elif name == "cyclic":
        return '' + ','.join(args) + ' are concyclic'
    elif name == "eqangle":
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} = {pretty_angle(args[4],args[5],args[6],args[7])}"
    elif name == "eqratio":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} = {args[4]}{args[5]}:{args[6]}{args[7]}"
    elif name == "neqangle":
        return f"{pretty_angle(args[0],args[1],args[2],args[3])} ≠ {pretty_angle(args[4],args[5],args[6],args[7])}"
    elif name == "neqratio":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} ≠ {args[4]}{args[5]}:{args[6]}{args[7]}"
    elif name == "midp":
        return f"{args[0]} is midpoint of {args[1]}{args[2]}"
    elif name == "ncoll":
        return '' + ','.join(args) + ' are not collinear'
    elif name == "npara":
        return f"{args[0]}{args[1]} is not parallel to {args[2]}{args[3]}"
    elif name == "nperp":
        return f"{args[0]}{args[1]} is not perpendicular to {args[2]}{args[3]}"
    elif name == "ncong":
        return f"{args[0]}{args[1]} ≠ {args[2]}{args[3]}"
    elif name == "para":
        return f"{args[0]}{args[1]} is parallel to {args[2]}{args[3]}"
    elif name == "perp":
        return f"{args[0]}{args[1]} is perpendicular to {args[2]}{args[3]}"
    elif name == "rconst":
        return f"{args[0]}{args[1]}:{args[2]}{args[3]} = {args[4]}"
    elif name == "sameside":
        return f"{args[2]}{args[3]} and {args[4]}{args[5]} are on the same side of {args[0]}{args[1]}"
    elif name == "simtri":
        return f"△{args[0]}{args[1]}{args[2]} is similar to △{args[3]}{args[4]}{args[5]}"
    elif name == "contri":
        return f"△{args[0]}{args[1]}{args[2]} is congruent to △{args[3]}{args[4]}{args[5]}"
    else:
        raise ValueError(f"unrecognized goal {name}")


def translate_problem_to_natural_language(
    this_problem: pr.Problem,
    language: str,
    used_points: list[str],
) -> str:
    if language == "zh":
        chinese_text = ""
        for clause in this_problem.clauses:
            if len(clause.constructions) == 1:
                this_text = translate_construction_to_chinese(
                    clause.constructions, 0, used_points)
                if this_text:
                    chinese_text += this_text+"，"
            elif len(clause.constructions) == 2:
                this_text = translate_construction_to_chinese_two(
                    clause.constructions, used_points)
                if this_text:
                    chinese_text += this_text+"，"
            else:
                pass
        if chinese_text.endswith("，"):
            chinese_text = chinese_text[:-1] + "。"
        return chinese_text
    elif language == "en":
        english_text = ""
        for clause in this_problem.clauses:
            if len(clause.constructions) == 1:
                this_text = translate_construction_to_english(
                    clause.constructions, 0, used_points)
                if this_text:
                    english_text += this_text[0].upper()+this_text[1:]+". "
            elif len(clause.constructions) == 2:
                this_text = translate_construction_to_english_two(
                    clause.constructions, used_points)
                if this_text:
                    english_text += this_text[0].upper()+this_text[1:]+". "
            else:
                pass
        if english_text.endswith(". "):
            english_text = english_text[:-2] + "."
        return english_text
    else:
        print("unknown language:"+language)


def translate_goals_to_natural_language(
    this_goal: tuple,
    language: str,
    used_points: list[str],
) -> str:
    # This is similar to the function pretty_nl() in pretty.py
    if language == "zh":
        return translate_goals_to_chinese(this_goal, used_points)
    elif language == "en":
        return translate_goals_to_english(this_goal, used_points)
    else:
        raise ValueError(f"unknown language {language}")


def generate_wrong_answer(three_candidates: list[tuple[pr.Construction, str]], used_points: list[str]) -> list[tuple[pr.Construction, bool, str, pr.Construction]]:
    # logging.info(type(three_candidates[0]))
    # assert type(three_candidates[0]) == pr.Construction
    answer_state = [True, True, True]
    # num_to_change = random.randint(0, 3)
    num_to_change = random.choices(
        [0, 1, 2, 3], weights=[1/10, 1/10, 4/10, 4/10], k=1)[0]
    indexes_to_change = random.sample(range(3), num_to_change)
    for index in indexes_to_change:
        answer_state[index] = False

    mixed_answer = []
    for i in range(3):
        if answer_state[i]:
            ori_candidate = three_candidates[i][0]
            name = ori_candidate.name
            args = ori_candidate.args
            correct_text = None
            ori_text = ori_candidate.txt()
            # ["coll", "cong", "circle", "cyclic", "midp", "para",
            #  "perp", "aconst", "eqangle", "eqratio", "rconst", "s_angle", "ncoll", "ncong", "npara", "nperp"]
            if name in ["coll", "midp"]:
                correct_text = random.choice([
                    ori_text,
                    f"nperp {args[0]} {args[1]} {args[1]} {args[2]}",
                    f"nperp {args[0]} {args[1]} {args[0]} {args[2]}",
                    f"nperp {args[0]} {args[2]} {args[1]} {args[2]}"
                ])
            elif name == "para":
                correct_text = random.choice([
                    ori_text,
                    f"nperp {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            elif name == "perp":
                correct_text = random.choice([
                    ori_text,
                    f"npara {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            if correct_text:
                mixed_answer.append((pr.Construction.from_txt(
                    correct_text), True, three_candidates[i][1], ori_candidate))

            mixed_answer.append(
                (three_candidates[i][0], True, three_candidates[i][1], three_candidates[i][0]))
        else:
            ori_candidate = three_candidates[i][0]
            name = ori_candidate.name
            args = ori_candidate.args
            unused_args = list(set(used_points)-set(args))
            wrong_text = None
            # ["coll", "cong", "circle", "cyclic", "midp", "para",
            #  "perp", "aconst", "eqangle", "eqratio", "rconst", "s_angle", "ncoll", "ncong", "npara", "nperp"]
            if name in ["coll"]:
                random_angle = random.choice(["15", "30", "45", "60", "75"])
                wrong_text = random.choice([
                    f"perp {args[0]} {args[1]} {args[1]} {args[2]}",
                    f"ncoll {args[0]} {args[1]} {args[2]}",
                    f"circle {random.choice(unused_args)} {args[0]} {args[1]} {args[2]}",
                    f"cyclic {args[0]} {args[1]} {args[2]} {random.choice(unused_args)}",
                    f"aconst {args[0]} {args[1]} {args[1]} {args[2]} {random_angle}"
                ])
            elif name == "cong":
                wrong_text = random.choice([
                    f"ncong {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            elif name == "circle":
                wrong_text = random.choice([
                    f"ncong {args[0]} {args[1]} {args[0]} {args[2]}",
                    f"ncong {args[0]} {args[1]} {args[0]} {args[3]}",
                    f"ncong {args[0]} {args[2]} {args[0]} {args[3]}",
                    f"coll {args[1]} {args[2]} {args[3]}",
                    f"eqangle {args[0]} {args[1]} {args[0]} {args[2]} {args[3]} {args[1]} {args[3]} {args[2]}",
                    f"eqangle {args[3]} {args[1]} {args[3]} {args[2]} {args[0]} {args[1]} {args[0]} {args[2]}",
                    f"cyclic {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            elif name == "cyclic":
                wrong_text = random.choice([
                    f"coll {args[0]} {args[1]} {args[2]}",
                    f"coll {args[0]} {args[1]} {args[3]}",
                    f"coll {args[0]} {args[2]} {args[3]}",
                    f"coll {args[1]} {args[2]} {args[3]}"])
            elif name in ["midp"]:
                random_angle = random.choice(["15", "30", "45", "60", "75"])
                wrong_text = random.choice([
                    f"perp {args[0]} {args[1]} {args[1]} {args[2]}",
                    f"ncoll {args[0]} {args[1]} {args[2]}",
                    f"circle {random.choice(unused_args)} {args[0]} {args[1]} {args[2]}",
                    f"cyclic {args[0]} {args[1]} {args[2]} {random.choice(unused_args)}",
                    f"aconst {args[0]} {args[1]} {args[2]} {random_angle}"
                    f"midp {args[1]} {args[0]} {args[2]}",
                    f"midp {args[2]} {args[0]} {args[1]}"
                ])
            elif name == "para":
                wrong_text = random.choice([
                    f"perp {args[0]} {args[1]} {args[2]} {args[3]}",
                    f"npara {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            elif name == "perp":
                wrong_text = random.choice([
                    f"para {args[0]} {args[1]} {args[2]} {args[3]}",
                    f"nperp {args[0]} {args[1]} {args[2]} {args[3]}"
                ])
            elif name in ["aconst", "s_angle"]:
                idx = -1
                a, b = args[idx].split("pi/")
                a, b = int(a), int(b)
                if b == 2:  # 1/2
                    three_candidates[i][0].args[idx] = random.choice(
                        ["1pi/4", "3pi/4"])
                elif b % 2 == 0:
                    b = b // 2
                    a = a % b
                    three_candidates[i][0].args[idx] = f"{a}pi/{b}"
                else:
                    b *= 2
                    three_candidates[i][0].args[idx] = f"{a}pi/{b}"
                mixed_answer.append(
                    (three_candidates[i][0], False, three_candidates[i][1], ori_candidate))
            elif name == "rconst":
                a, b = args[4].split("/")
                a, b = int(a), int(b)
                three_candidates[i][0].args[4] = f"{a//2}/{b}" if a % 2 == 0 else f"{a}/{b*2}"
                mixed_answer.append(
                    (three_candidates[i][0], False, three_candidates[i][1], ori_candidate))
            elif name == "ncoll":
                wrong_text = random.choice([
                    f"coll {args[0]} {args[1]} {args[2]}"
                ])
            elif name == "eqratio":
                wrong_text = random.choice([
                    f"neqratio {args[0]} {args[1]} {args[2]} {args[3]} {args[4]} {args[5]} {args[6]} {args[7]}"
                ])
            elif name == "eqangle":
                wrong_text = random.choice([
                    f"neqangle {args[0]} {args[1]} {args[2]} {args[3]} {args[4]} {args[5]} {args[6]} {args[7]}"
                ])
            else:
                raise ValueError(f"unknown conclusion {name}")
            if wrong_text:
                mixed_answer.append((pr.Construction.from_txt(
                    wrong_text), False, three_candidates[i][1], ori_candidate))
    return mixed_answer

def main(txt : str):
    # print(get_used_three_intersection(args=('e','f','g','h','a','d','b'),used=(False,True,False,False,True,True,True)))
    p = pr.Problem.from_txt(txt, translate=False)
    # this_used_points = ["a",
    #                     "b",
    #                     "c",
    #                     "d",
    #                     "f",
    #                     "g"]
    this_used_points = [chr(char) for char in range(ord('a'), ord('z') + 1)]

    for language in ["zh", "en"]:
        text = translate_problem_to_natural_language(
            p, language, this_used_points)
        if p.goal:
            text_2 = translate_goals_to_natural_language(
                (p.goal.name,) + tuple(p.goal.args), language, this_used_points)
            print(text+text_2)
        else:
            print(text)



if __name__ == "__main__":
    # print(get_used_three_intersection(args=('e','f','g','h','a','d','b'),used=(False,True,False,False,True,True,True)))

    txt = "o a = segment o a; p = on_circle p a o; q = intersection_cc q a o p; r = lc_tangent r p a, on_circle r o p"
    main(txt)
