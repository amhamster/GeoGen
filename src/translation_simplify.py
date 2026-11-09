import problem as pr


def get_used_three_intersection(
    args: tuple,
    used: tuple,
):
    if not any(used[0:3]):
        return None, None
    added_edges = ""
    added_points = ""
    for i in range(0, 3):
        if used[i]:
            added_edges += "、"
            added_points += "、"
            for j in range(0, 3):
                if j != i:
                    added_edges += args[j+4]
            added_points += args[i]
    return added_edges.lstrip('、'), added_points.lstrip('、')


def simplify_construction(
    construction: pr.Construction,
    idx: int,
    used_points: list[str],
) -> str:
    name = construction[idx].name
    args = tuple(arg.lower() for arg in construction[idx].args)
    used = tuple(arg in (point.lower() for point in used_points)
                 for arg in args if arg.isalpha())
    # print(name)
    # print(args)
    # print(used)
    if not used[0] and name not in ['s_angle', 'incenter2', 'excenter2', 'centroid', 'ninepoints']:
        return None
    if not any(used[1:]):
        if used[0]:
            return f"{args[0]} = free {args[0]}"
        else:
            return None
    if name in ['incenter2', 'excenter2', 'centroid', 'ninepoints']:
        edges_list, points_list = get_used_three_intersection(args, used)
        if edges_list:
            new_txt = ""
            for p,e in zip(points_list.lower().split("、"),edges_list.lower().split("、")):
                new_txt += f"{p} = midpoint {p} {e[0]} {e[1]}; "
            if new_txt.endswith("; "):
                new_txt = new_txt[:-2]
    else:
        edges_list, points_list = None, None

    if name == "angle_bisector":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "angle_mirror":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "circle" or name == "circumcenter":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "eq_quadrangle":
        return "NO_REDUNDANT"
    elif name == "eq_trapezoid":
        return "NO_REDUNDANT"
    elif name == "eq_triangle":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "eqangle2":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "eqdia_quadrangle":
        return "NO_REDUNDANT"
    elif name == "eqdistance":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "foot":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "free":
        return f"{args[0]} = free {args[0]}"
    elif name == "incenter":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "incenter2":
        if edges_list is None:
            if used[3]:
                return f"{args[3]} = incenter {args[4]} {args[5]} {args[6]}"
            else:
                return None
        else:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return "NO_REDUNDANT"
    elif name == "excenter":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "excenter2":
        if edges_list is None:
            if used[3]:
                return f"{args[3]} = excenter {args[4]} {args[5]} {args[6]}"
            else:
                return None
        else:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return "NO_REDUNDANT"
    elif name == "centroid":
        if edges_list is None:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return None
        else:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return new_txt
    elif name == "ninepoints":
        if edges_list is None:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return None
        else:
            if used[3]:
                return "NO_REDUNDANT"
            else:
                return new_txt
    elif name == "intersection_cc":
        return "NO_REDUNDANT"
    elif name == "intersection_lc":
        return "NO_REDUNDANT"
    elif name == "intersection_ll":
        if all(used[1:3]) and all(used[3:5]):
            return "NO_REDUNDANT"
        elif not all(used[1:3]):
            return f"{args[0]} = on_line {args[0]} {args[3]} {args[4]}"
        elif not all(used[3:5]):
            return f"{args[0]} = on_line {args[0]} {args[1]} {args[2]}"
        else:
            return None
    elif name == "intersection_lp":
        if all(used[1:3]) and all(used[3:6]):
            return "NO_REDUNDANT"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"{args[0]} = on_pline {args[0]} {args[3]} {args[4]} {args[5]}"
            return f"过点{args[3]}作{args[4]}{args[5]}的平行线{args[3]}{args[0]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"{args[0]} = on_line {args[0]} {args[1]} {args[2]}"
        else:
            return None
    elif name == "intersection_lt":
        if all(used[1:3]) and all(used[3:6]):
            return "NO_REDUNDANT"
        elif not all(used[1:3]) and all(used[3:6]):
            return f"{args[0]} = on_tline {args[0]} {args[3]} {args[4]} {args[5]}"
            return f"过点{args[3]}作{args[4]}{args[5]}的垂线{args[3]}{args[0]}"
        elif all(used[1:3]) and not all(used[3:6]):
            return f"{args[0]} = on_line {args[0]} {args[1]} {args[2]}"
        else:
            return None
    elif name == "intersection_pp":
        if all(used[1:4]) and all(used[4:7]):
            return "NO_REDUNDANT"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"{args[0]} = on_pline {args[0]} {args[4]} {args[5]} {args[6]}"
            return f"过点{args[4]}作{args[5]}{args[6]}的平行线{args[4]}{args[0]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"{args[0]} = on_pline {args[0]} {args[1]} {args[2]} {args[3]}"
            return f"过点{args[1]}作{args[2]}{args[3]}的平行线{args[1]}{args[0]}"
        else:
            return None
    elif name == "intersection_tt":
        if all(used[1:4]) and all(used[4:7]):
            return "NO_REDUNDANT"
        elif not all(used[1:4]) and all(used[4:7]):
            return f"{args[0]} = on_tline {args[0]} {args[4]} {args[5]} {args[6]}"
            return f"过点{args[4]}作{args[5]}{args[6]}的垂线{args[4]}{args[0]}"
        elif all(used[1:4]) and not all(used[4:7]):
            return f"{args[0]} = on_tline {args[0]} {args[1]} {args[2]} {args[3]}"
            return f"过点{args[1]}作{args[2]}{args[3]}的垂线{args[1]}{args[0]}"
        else:
            return None
    elif name == "iso_triangle":
        return "NO_REDUNDANT"
    elif name == "lc_tangent":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "midpoint":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "mirror":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "nsquare" or name == "psquare":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_aline":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_aline2":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_bline":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_circle":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_line" or name == "on_opline":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_pline":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "on_tline":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "orthocenter":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "parallelogram":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "pentagon":
        return "NO_REDUNDANT"
    elif name == "quadrangle":
        return "NO_REDUNDANT"
    elif name == "r_trapezoid":
        return "NO_REDUNDANT"
    elif name == "r_triangle":
        if all(used[0:3]):
            return "NO_REDUNDANT"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"{args[1]} {args[2]} = segment {args[1]} {args[2]}"
            elif not used[1]:
                return f"{args[0]} {args[2]} = segment {args[0]} {args[2]}"
            elif not used[2]:
                return f"{args[0]} {args[1]} = segment {args[0]} {args[1]}"
        else:
            return None
    elif name == "rectangle":
        return "NO_REDUNDANT"
    elif name == "reflect":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "risos":
        if all(used[0:3]):
            return "NO_REDUNDANT"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"{args[1]} {args[2]} = segment {args[1]} {args[2]}"
            elif not used[1]:
                return f"{args[0]} {args[2]} = segment {args[0]} {args[2]}"
            elif not used[2]:
                return f"{args[0]} {args[1]} = segment {args[0]} {args[1]}"
        else:
            return None
    elif name == "s_angle":
        if all(used[0:3]):
            return "NO_REDUNDANT"
        else:
            return None
    elif name == "segment":
        return "NO_REDUNDANT"
    elif name == "shift":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
        # return f"{args[0]}{args[1]}={args[2]}{args[3]}，{args[0]}{args[2]}={args[1]}{args[3]}"
    elif name == "square":
        if used[2] and used[3]:
            return "NO_REDUNDANT"
        elif used[2] and not used[3]:
            return f"{args[2]} = nsquare {args[2]} {args[1]} {args[0]}"
            return f"以{args[0]}{args[1]}为边、∠{args[1]}为直角，构造等腰Rt△{args[0]}{args[1]}{args[2]}"
        elif not used[2] and used[3]:
            return f"{args[3]} = nsquare {args[3]} {args[1]} {args[0]}"
            return f"以{args[0]}{args[1]}为边、∠{args[1]}为直角，构造等腰Rt△{args[1]}{args[0]}{args[3]}"
        else:
            return None

    elif name == "isquare":
        return "NO_REDUNDANT"
    elif name == "trapezoid":
        return "NO_REDUNDANT"
    elif name == "triangle":
        if all(used[0:3]):
            return "NO_REDUNDANT"
        elif sum(element == False for element in used[0:3]) == 1:
            if not used[0]:
                return f"{args[1]} {args[2]} = segment {args[1]} {args[2]}"
            elif not used[1]:
                return f"{args[0]} {args[2]} = segment {args[0]} {args[2]}"
            elif not used[2]:
                return f"{args[0]} {args[1]} = segment {args[0]} {args[1]}"
        else:
            return None
    elif name == "triangle12":
        return "NO_REDUNDANT"
    elif name == "2l1c":
        return "NO_REDUNDANT"
    elif name == "e5128":
        return "NO_REDUNDANT"
    elif name == "3peq":
        return "NO_REDUNDANT"
    elif name == "trisect":
        return "NO_REDUNDANT"
    elif name == "trisegment":
        return "NO_REDUNDANT"
    elif name == "on_dia":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "ieq_triangle":
        return "NO_REDUNDANT"
    elif name == "cc_tangent0":
        return "NO_REDUNDANT"
    elif name == "cc_tangent":
        return "NO_REDUNDANT"
    elif name == "eqangle3":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    elif name == "tangent":
        if used[0] and used[1]:
            return "NO_REDUNDANT"
        elif used[0] and not used[1]:
            return "NO_REDUNDANT"
        elif not used[0] and used[1]:
            return "NO_REDUNDANT"
        else:
            return None
        el
    elif name == "on_circum":
        if not all(used[1:]):
            return f"{args[0]} = free {args[0]}"
        return "NO_REDUNDANT"
    else:
        return None


def _simplify_problem_expressions(
    this_problem: pr.Problem,
    used_points: list[str],
) -> str:
    simplified_text = ""
    for clause in this_problem.clauses:
        if len(clause.constructions) == 1:
            this_text = simplify_construction(
                clause.constructions, 0, used_points)
            if this_text == "NO_REDUNDANT":
                simplified_text += clause.txt()+"; "
            elif this_text:
                simplified_text += this_text+"; "
        elif len(clause.constructions) == 2:
            this_text1 = simplify_construction(
                clause.constructions, 0, used_points)
            this_text2 = simplify_construction(
                clause.constructions, 1, used_points)
            if this_text1 == "NO_REDUNDANT" and this_text2 == "NO_REDUNDANT":
                simplified_text += clause.txt()+"; "
            elif this_text1 == "NO_REDUNDANT" and (this_text2 is None or "free" in this_text2):
                del clause.constructions[1]
                simplified_text += clause.txt()+"; "
            elif (this_text1 is None or "free" in this_text1) and this_text2 == "NO_REDUNDANT":
                del clause.constructions[0]
                simplified_text += clause.txt()+"; "

            # this_text = translate_construction_to_chinese_two(
            #     clause.constructions, used_points)
            # if this_text[0]=="NO_REDUNDANT" and this_text[1]=="NO_REDUNDANT":
            #     simplified_text += clause.txt()+"; "
            # elif this_text[0]=="NO_REDUNDANT" and this_text[1]=="NO_REDUNDANT":
            #     simplified_text += this_text+"; "
        else:
            pass
    if simplified_text.endswith("; "):
        simplified_text = simplified_text[:-2]
    return simplified_text

def simplify_problem_expressions(
    this_txt: str,
    used_points: list[str],
):
    p = pr.Problem.from_txt(this_txt,translate=False)
    text = _simplify_problem_expressions(p, used_points)
    text_2 = p.goal.txt()
    return text+" ? "+text_2
    
if __name__ == "__main__":
    # print(get_used_three_intersection(args=('e','f','g','h','a','d','b'),used=(False,True,False,False,True,True,True)))

    txt = "a b c = triangle a b c; e f g h = ninepoints e f g h a c b ? cong c g e f"
    this_used_points = ["a",        "b",        "c",        "e",        "f","g"]
    print(simplify_problem_expressions(txt,this_used_points))