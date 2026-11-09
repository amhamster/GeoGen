"""Load and validate declarative initial-geometry templates.

Templates deliberately reuse the existing construction DSL.  This keeps a
template's premises visible to the solver and avoids treating a theorem as an
axiom.  More elaborate P2+ templates may later provide dedicated coordinate
builders, but P0/P1 are fully expressible as ordered existing constructions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class StructureTemplateError(ValueError):
    """Raised when a structure-template file is malformed."""


def load_templates(
        path: str, definitions: dict, priorities: Optional[set[str]] = None
) -> list[dict]:
    """Return enabled templates whose clauses are valid existing DSL actions."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StructureTemplateError(f"Cannot load structure templates from {path}: {exc}") from exc

    templates = data.get("templates")
    if not isinstance(templates, list):
        raise StructureTemplateError("structure template file must contain a templates list")

    result = []
    for template in templates:
        if not template.get("enabled", False):
            continue
        if priorities is not None and template.get("priority") not in priorities:
            continue
        _validate_template(template, definitions)
        result.append(template)

    if not result:
        selected = sorted(priorities) if priorities else "enabled priorities"
        raise StructureTemplateError(f"No templates selected for {selected}")
    return result


def template_seed(template: dict) -> tuple[list[tuple], list[bool]]:
    """Convert a validated template into prgenerate's serializable seed form."""
    alphabet = [False] * 26
    problem = []
    for clause in template["clauses"]:
        points = list(clause["points"])
        constructions = _clause_constructions(clause)
        for name in points + [arg for construction in constructions for arg in construction["args"]]:
            alphabet[ord(name) - ord("a")] = True
        if len(constructions) == 1:
            construction = constructions[0]
            problem.append((points, construction["name"], list(construction["args"])))
        elif len(constructions) == 2:
            first, second = constructions
            problem.append((
                points,
                first["name"], list(first["args"]),
                second["name"], list(second["args"]),
            ))
        else:
            raise StructureTemplateError(
                f"{template['id']}: a clause may contain at most two constructions"
            )
    return problem, alphabet


def _validate_template(template: dict, definitions: dict) -> None:
    template_id = template.get("id", "<unnamed>")
    if not isinstance(template_id, str) or not template_id:
        raise StructureTemplateError("template id must be a non-empty string")
    clauses = template.get("clauses")
    if not isinstance(clauses, list) or not clauses:
        raise StructureTemplateError(f"{template_id}: clauses must be a non-empty list")

    known = set()
    for index, clause in enumerate(clauses):
        if not isinstance(clause, dict):
            raise StructureTemplateError(f"{template_id}[{index}]: clause must be an object")
        points = clause.get("points")
        if not isinstance(points, list):
            raise StructureTemplateError(f"{template_id}[{index}]: points must be a list")
        constructions = _clause_constructions(clause)
        if len(constructions) > 2:
            raise StructureTemplateError(f"{template_id}[{index}]: at most two constructions are supported")
        args = [arg for construction in constructions for arg in construction["args"]]
        if any(not _is_point_name(p) for p in points + args):
            raise StructureTemplateError(f"{template_id}[{index}]: only lowercase point names a-z are supported")
        if len(set(points)) != len(points) or any(p in known for p in points):
            raise StructureTemplateError(f"{template_id}[{index}]: points must be introduced exactly once")
        current = known | set(points)
        for construction in constructions:
            name = construction["name"]
            cons_args = construction["args"]
            if name not in definitions:
                raise StructureTemplateError(f"{template_id}[{index}]: unknown construction {name!r}")
            if len(cons_args) != len(definitions[name].construction.args):
                raise StructureTemplateError(
                    f"{template_id}[{index}]: {name} expects "
                    f"{len(definitions[name].construction.args)} args, got {len(cons_args)}"
                )
            if any(arg not in current for arg in cons_args):
                raise StructureTemplateError(f"{template_id}[{index}]: construction refers to a future point")
        known.update(points)


def _is_point_name(value: object) -> bool:
    return isinstance(value, str) and len(value) == 1 and "a" <= value <= "z"


def _clause_constructions(clause: dict) -> list[dict]:
    """Normalize the one- and two-construction JSON clause forms."""
    has_single = "name" in clause or "args" in clause
    has_multiple = "constructions" in clause
    if has_single == has_multiple:
        raise StructureTemplateError(
            "a clause must use either name/args or constructions, but not both"
        )
    if has_single:
        name, args = clause.get("name"), clause.get("args")
        if not isinstance(name, str) or not isinstance(args, list):
            raise StructureTemplateError("single construction clauses require a string name and list args")
        return [{"name": name, "args": args}]
    constructions = clause.get("constructions")
    if not isinstance(constructions, list) or not constructions:
        raise StructureTemplateError("constructions must be a non-empty list")
    for construction in constructions:
        if (
            not isinstance(construction, dict)
            or not isinstance(construction.get("name"), str)
            or not isinstance(construction.get("args"), list)
        ):
            raise StructureTemplateError("each construction requires a string name and list args")
    return constructions
