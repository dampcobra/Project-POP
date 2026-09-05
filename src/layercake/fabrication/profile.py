"""Fabrication parameters, with each value's evidential weight carried as data.

Layercake's fabrication parameters are not equally trustworthy. Spike 02
*measured* the seating depth. It *held* the XY clearance at the process floor
because neither round could resolve it. The minimum recess floor is an
*engineering choice* that has never been printed or loaded. The backing
thickness is derived from the last two and can be no stronger than the weaker.

Until now that distinction lived in docstrings, maintained by a test that
grepped them. Here it is structured data, so a report can state which numbers
are measured without a human remembering to.

Numerically equal is not semantically equal
-------------------------------------------
Three unrelated concepts are currently all 0.8 mm: visible step height, seating
depth, and the round-1 as-printed backing. That is a coincidence of where the
project happens to be, and it is precisely the trap Session 01 removed when the
backing stopped inheriting `H`.

Parameters are therefore named values, not bare floats. Two parameters with the
same magnitude and different names are not equal, so a value cannot be passed
where another was meant without the substitution being visible. Callers reach
for `.mm` deliberately when they want arithmetic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Iterator


class ProfileError(ValueError):
    """A fabrication profile that cannot be manufactured as specified."""


class Evidence(Enum):
    """How well a parameter's value is supported.

    Ordered weakest to strongest. `HELD` sits above `ENGINEERING_CHOICE` because
    a held value has an empirical reason for being where it is -- the process
    could not resolve finer -- whereas an engineering choice has judgement only.
    Both are below `MEASURED`. The ranking is only consulted when deriving a
    parameter from others, and is worth a second opinion.
    """

    ENGINEERING_CHOICE = "engineering_choice"
    HELD = "held"
    MEASURED = "measured"

    @property
    def rank(self) -> int:
        return _EVIDENCE_ORDER.index(self)

    @staticmethod
    def weakest(*levels: "Evidence") -> "Evidence":
        """The weakest of several levels: a derived value inherits this."""
        if not levels:
            raise ValueError("weakest() needs at least one evidence level")
        return min(levels, key=lambda e: e.rank)


_EVIDENCE_ORDER = [Evidence.ENGINEERING_CHOICE, Evidence.HELD, Evidence.MEASURED]


@dataclass(frozen=True)
class Parameter:
    """One named fabrication value, with its provenance.

    Equality includes the name, so two parameters that merely share a magnitude
    are not interchangeable.
    """

    name: str
    value: float | str
    evidence: Evidence
    scope: str
    unit: str | None = "mm"
    is_z_dimension: bool = False
    derived_from: tuple[str, ...] = ()

    @property
    def mm(self) -> float:
        """The value in millimetres. Raises for a non-length parameter."""
        if self.unit != "mm":
            raise TypeError(f"{self.name} is not a length ({self.unit or 'no unit'})")
        return float(self.value)

    def to_dict(self) -> dict:
        d: dict = {
            "value": self.value,
            "unit": self.unit,
            "evidence": self.evidence.value,
            "scope": self.scope,
            "is_z_dimension": self.is_z_dimension,
        }
        if self.derived_from:
            d["derived_from"] = list(self.derived_from)
        return d


# --- Session 01 provenance ---------------------------------------------------

_SCOPE_MEASURED_DEPTH = (
    "Measured, Spike 02 round 2. Best balance of positive guidance, resistance "
    "to rocking/tilting and easy removal before glue. Scoped to one process: "
    "Bambu P1S, 0.20 mm layer height, 0.15 mm elephant-foot compensation, PLA, "
    "12 x 12 mm square seating footprint. Provisional, not a universal constant."
)

_SCOPE_HELD_CLEARANCE = (
    "HELD at the process floor, not measured. Spike 02 round 1 could not resolve "
    "clearance -- nominally identical children felt different, so process "
    "variation is at least as large as the ladder step. Round 2 held it fixed. "
    "Neither round measured it."
)

_SCOPE_FLOOR = (
    "Engineering choice, NOT physically validated. Two layers at 0.20 mm. No "
    "print has exercised this floor beneath a loaded registration recess, on the "
    "member everything else glues to. Deferred validation: issue #11."
)

_SCOPE_BACKING = (
    "Derived: seating depth + minimum recess floor. Independent of visible step "
    "height since Session 01 -- a structural member does not inherit how tall an "
    "artwork level looks. Sits exactly at the minimum floor, so it carries no "
    "margin; raising the minimum recess floor is the dial."
)

_SCOPE_H = (
    "Product intent, not a measurement: how far one completed colour level "
    "stands above the one below. Currently equal to the seating depth by "
    "coincidence, not by relationship."
)

_SCOPE_LAYER = (
    "Process condition the coupon geometry was designed around. Every Z "
    "dimension is a whole number of these, so the slicer cannot quantise a "
    "feature into a depth other than the one intended."
)

_SCOPE_JOIN = (
    "Round join gives a true radial offset, so clearance is the requested value "
    "everywhere including at corners. A mitre would hand out c*sqrt(2) on a "
    "diagonal -- more than asked for, and unlike anything a nozzle produces."
)


@dataclass(frozen=True)
class FabricationProfile:
    """The parameters a canonical artwork is fabricated against."""

    visible_step_height: Parameter
    seating_depth: Parameter
    per_side_clearance: Parameter
    minimum_recess_floor: Parameter
    backing_thickness: Parameter
    layer_height: Parameter
    offset_join: Parameter
    _order: tuple[str, ...] = field(
        default=(
            "visible_step_height",
            "seating_depth",
            "per_side_clearance",
            "minimum_recess_floor",
            "backing_thickness",
            "layer_height",
            "offset_join",
        ),
        repr=False,
    )

    # -- construction ---------------------------------------------------------

    @classmethod
    def default(cls) -> "FabricationProfile":
        """The Session 01 defaults, with their provenance."""
        depth = Parameter(
            "seating_depth", 0.80, Evidence.MEASURED, _SCOPE_MEASURED_DEPTH,
            is_z_dimension=True,
        )
        floor = Parameter(
            "minimum_recess_floor", 0.40, Evidence.ENGINEERING_CHOICE, _SCOPE_FLOOR,
            is_z_dimension=True,
        )
        return cls(
            visible_step_height=Parameter(
                "visible_step_height", 0.8, Evidence.ENGINEERING_CHOICE, _SCOPE_H,
                is_z_dimension=True,
            ),
            seating_depth=depth,
            per_side_clearance=Parameter(
                "per_side_clearance", 0.05, Evidence.HELD, _SCOPE_HELD_CLEARANCE,
            ),
            minimum_recess_floor=floor,
            backing_thickness=Parameter(
                "backing_thickness",
                1.2,
                Evidence.weakest(depth.evidence, floor.evidence),
                _SCOPE_BACKING,
                is_z_dimension=True,
                derived_from=("seating_depth", "minimum_recess_floor"),
            ),
            layer_height=Parameter(
                "layer_height", 0.20, Evidence.HELD, _SCOPE_LAYER,
            ),
            offset_join=Parameter(
                "offset_join", "round", Evidence.ENGINEERING_CHOICE, _SCOPE_JOIN,
                unit=None,
            ),
        )

    # -- inspection -----------------------------------------------------------

    def parameters(self) -> Iterator[Parameter]:
        for name in self._order:
            yield getattr(self, name)

    def z_dimensions(self) -> Iterator[Parameter]:
        return (q for q in self.parameters() if q.is_z_dimension)

    @property
    def required_backing_mm(self) -> float:
        """The thinnest backing that can host this profile's recess."""
        return self.seating_depth.mm + self.minimum_recess_floor.mm

    # -- derivation -----------------------------------------------------------

    def _replace_param(self, name: str, value: float | str) -> "FabricationProfile":
        current: Parameter = getattr(self, name)
        return replace(self, **{name: replace(current, value=value)})

    def with_visible_step_height(self, mm: float) -> "FabricationProfile":
        return self._replace_param("visible_step_height", mm)

    def with_seating_depth(self, mm: float) -> "FabricationProfile":
        return self._replace_param("seating_depth", mm)

    def with_per_side_clearance(self, mm: float) -> "FabricationProfile":
        return self._replace_param("per_side_clearance", mm)

    def with_minimum_recess_floor(self, mm: float) -> "FabricationProfile":
        return self._replace_param("minimum_recess_floor", mm)

    def with_backing_thickness(self, mm: float) -> "FabricationProfile":
        return self._replace_param("backing_thickness", mm)

    def with_layer_height(self, mm: float) -> "FabricationProfile":
        return self._replace_param("layer_height", mm)

    # -- validation -----------------------------------------------------------

    def validate(self) -> "FabricationProfile":
        """Raise `ProfileError` if this profile cannot be manufactured.

        Returns self, so a profile can be validated inline where it is built.
        """
        for q in self.parameters():
            if q.unit == "mm" and q.mm <= 0:
                raise ProfileError(
                    f"{_human(q.name)} must be positive, got {q.mm} mm"
                )

        layer = self.layer_height.mm
        for q in self.z_dimensions():
            n = q.mm / layer
            if not math.isclose(n, round(n), abs_tol=_LAYER_TOL):
                raise ProfileError(
                    f"{_human(q.name)} {q.mm} mm is not a whole number of "
                    f"{layer} mm layers ({n:.4g} layers). The slicer quantises a "
                    "Z feature to a layer boundary, so this would be built at a "
                    "different size than specified."
                )

        needed = self.required_backing_mm
        if self.backing_thickness.mm < needed - _LAYER_TOL:
            raise ProfileError(
                f"backing thickness {self.backing_thickness.mm} mm cannot host "
                f"seating depth {self.seating_depth.mm} mm plus minimum recess "
                f"floor {self.minimum_recess_floor.mm} mm: it needs at least "
                f"{needed:.4g} mm. A shallower backing would leave no sound "
                "floor beneath the recess."
            )
        return self

    # -- reporting ------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "profile": "layercake fabrication profile",
            "required_backing_mm": self.required_backing_mm,
            "evidence_note": (
                "Values do not carry equal weight. 'measured' is backed by a "
                "physical result; 'held' is fixed deliberately because it could "
                "not be resolved; 'engineering_choice' has never been tested. A "
                "derived value inherits the weakest evidence of its inputs."
            ),
            "parameters": {q.name: q.to_dict() for q in self.parameters()},
        }

    def to_markdown(self) -> str:
        lines = [
            "# Fabrication profile",
            "",
            "| Parameter | Value | Evidence | Derived from |",
            "|---|---|---|---|",
        ]
        for q in self.parameters():
            value = f"{q.mm:.2f} mm" if q.unit == "mm" else f"`{q.value}`"
            derived = ", ".join(q.derived_from) if q.derived_from else "-"
            lines.append(
                f"| {_human(q.name)} | {value} | `{q.evidence.value}` | {derived} |"
            )
        lines += [
            "",
            "**Values do not carry equal weight.** `measured` is backed by a "
            "physical result; `held` is fixed deliberately because it could not be "
            "resolved; `engineering_choice` has never been tested. A derived value "
            "inherits the weakest evidence of its inputs.",
            "",
            "## Scope of each value",
            "",
        ]
        for q in self.parameters():
            lines.append(f"- **{_human(q.name)}** (`{q.evidence.value}`): {q.scope}")
        return "\n".join(lines) + "\n"


#: Tolerance for layer-multiple and backing comparisons. Generous enough to
#: absorb binary floating point (1.2 - 0.8 is 0.39999999999999991) and far
#: tighter than anything a printer resolves.
_LAYER_TOL = 1e-9


def _human(name: str) -> str:
    return name.replace("_", " ")
