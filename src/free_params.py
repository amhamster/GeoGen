from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numericals as nm


@dataclass(frozen=True)
class ParamSpec:
    size: int
    bounds: List[Tuple[float, float]]
    defaults: List[float]


INDEPENDENT_PARAM_SPECS: Dict[str, ParamSpec] = {
    'segment': ParamSpec(
        size=2,
        bounds=[(0.0, 1.0), (0.0, 1.0)],
        defaults=[0.5, 0.0],
    ),
    'triangle': ParamSpec(
        size=3,
        bounds=[(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)],
        defaults=[0.5, 0.5, 0.5],
    ),
    'ieq_triangle': ParamSpec(
        size=1,
        bounds=[(0.0, 1.0)],
        defaults=[0.5],
    ),
    'iso_triangle': ParamSpec(
        size=2,
        bounds=[(0.0, 1.0), (0.0, 1.0)],
        defaults=[0.5, 0.5],
    ),
    'r_triangle': ParamSpec(
        size=2,
        bounds=[(0.0, 1.0), (0.0, 1.0)],
        defaults=[0.5, 0.5],
    ),
    'risos': ParamSpec(
        size=1,
        bounds=[(0.0, 1.0)],
        defaults=[0.5],
    ),
    'rectangle': ParamSpec(
        size=2,
        bounds=[(0.0, 1.0), (0.0, 1.0)],
        defaults=[0.5, 0.5],
    ),
    'isquare': ParamSpec(
        size=1,
        bounds=[(0.0, 1.0)],
        defaults=[0.5],
    ),
    'trapezoid': ParamSpec(
        size=4,
        bounds=[(0.0, 1.0)] * 4,
        defaults=[0.5, 0.5, 0.5, 0.5],
    ),
    'eq_trapezoid': ParamSpec(
        size=3,
        bounds=[(0.0, 1.0)] * 3,
        defaults=[0.5, 0.5, 0.5],
    ),
    'r_trapezoid': ParamSpec(
        size=3,
        bounds=[(0.0, 1.0)] * 3,
        defaults=[0.5, 0.5, 0.5],
    ),
    'eq_quadrangle': ParamSpec(
        size=3,
        bounds=[(0.0, 1.0)] * 3,
        defaults=[0.5, 0.5, 0.5],
    ),
    'eqdia_quadrangle': ParamSpec(
        size=3,
        bounds=[(0.0, 1.0)] * 3,
        defaults=[0.5, 0.5, 0.5],
    ),
}


class FreeParamRegistry:
    def __init__(self) -> None:
        self._specs: List[ParamSpec] = []
        self._names: List[str] = []

    def add(self, name: str) -> int:
        if name not in INDEPENDENT_PARAM_SPECS:
            raise ValueError(f'Unknown independent construction: {name}')
        spec = INDEPENDENT_PARAM_SPECS[name]
        self._specs.append(spec)
        self._names.append(name)
        return len(self._specs) - 1

    def total_size(self) -> int:
        return sum(spec.size for spec in self._specs)

    def bounds(self) -> List[Tuple[float, float]]:
        bounds: List[Tuple[float, float]] = []
        for spec in self._specs:
            bounds.extend(spec.bounds)
        return bounds

    def defaults(self) -> List[float]:
        defaults: List[float] = []
        for spec in self._specs:
            defaults.extend(spec.defaults)
        return defaults

    def slice_params(self, flat_params: List[float]) -> Dict[str, List[float]]:
        result: Dict[str, List[float]] = {}
        cursor = 0
        for name, spec in zip(self._names, self._specs):
            result[name] = list(flat_params[cursor: cursor + spec.size])
            cursor += spec.size
        return result

    def iter_slices(self, flat_params: List[float]):
        cursor = 0
        for spec in self._specs:
            yield list(flat_params[cursor: cursor + spec.size])
            cursor += spec.size


def sketch_independent(name: str, params: List[float]):
    if name == 'iso_triangle':
        return nm.sketch_with_params('iso_triangle', [], params=params)
    return nm.sketch_with_params(name, [], params=params)


def build_registry_for_problem(problem_obj) -> FreeParamRegistry:
    registry = FreeParamRegistry()
    for clause in problem_obj.clauses:
        clause_all_fixed = all(num is not None for num in clause.nums)
        for construction in clause.constructions:
            if clause_all_fixed:
                continue
            if construction.name in INDEPENDENT_PARAM_SPECS:
                registry.add(construction.name)
    return registry
