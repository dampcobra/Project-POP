"""Fabrication parameters, with each value's provenance carried as data.

Layercake's fabrication parameters are not equally trustworthy. Spike 02
*measured* the seating depth. It *held* the XY clearance at the process floor
because neither round could resolve it. The minimum recess floor is an
*engineering choice* that has never been printed or loaded. The backing
thickness is derived from the last two and can be no stronger than the weaker.

Until now that distinction lived in docstrings, maintained by a test that
grepped them. Here it is structured data, so a report can state which numbers
are measured without a human remembering to.

Not every provenance is evidence
--------------------------------
Visible step height is a *product specification* -- a decision about what
Layercake should look like -- not a claim about the world. It is recorded as
`PRODUCT_INTENT` and deliberately left off the evidence ranking: asking whether
a design decision is weaker than a measurement is a category error, and giving
it an artificial position purely to fit the derivation mechanism would bury that.
Derived physical parameters therefore accept evidential inputs only.

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


class ProvenanceError(ValueError):
    """A provenance category used in a way its kind does not support."""


class Provenance(Enum):
    """Where a parameter's value comes from.

    Two kinds of category live here, and they are **not** points on one scale.

    *Evidential* categories make a claim about physical reality, and can be
    ranked weakest to strongest: `ENGINEERING_CHOICE` < `HELD` < `MEASURED`.
    `HELD` sits above `ENGINEERING_CHOICE` because a held value has an empirical
    reason for being where it is -- the process could not resolve finer --
    whereas an engineering choice has judgement only.

    **That ordering is a narrow rule for deriving evidential parameters, not a
    general confidence hierarchy** (agreed Session 01). It answers one question:
    which provenance a value inherits when it is computed from others. It is not
    a claim that a held value is always more trustworthy than an engineering
    choice in some broader sense, and it should not be reused as one.

    `PRODUCT_INTENT` is **not evidential**. It records a decision about what
    Layercake should look like, not a claim about the world, so asking whether
    it is stronger or weaker than a measurement is a category error rather than
    a question with an answer. It is deliberately excluded from the ordering
    instead of being given an artificial position to fit the mechanism.
    """

    PRODUCT_INTENT = "product_intent"
    ENGINEERING_CHOICE = "engineering_choice"
    HELD = "held"
    MEASURED = "measured"

    @property
    def is_evidential(self) -> bool:
        """Whether this category makes a claim about physical reality."""
        return self in _EVIDENCE_ORDER

    @property
    def rank(self) -> int:
        """Position on the evidence scale. Non-evidential categories have none.

        Used only to decide which provenance a derived value inherits. Not a
        general confidence score.
        """
        if not self.is_evidential:
            raise ProvenanceError(
                f"{self.value} is not evidence, so it has no rank. It records a "
                "product decision rather than a claim about physical reality, "
                "and is not weaker or stronger than a measurement -- it is a "
                "different kind of statement."
            )
        return _EVIDENCE_ORDER.index(self)

    @staticmethod
    def weakest(*levels: "Provenance") -> "Provenance":
        """The weakest of several evidential categories.

        A parameter derived from others inherits this. Every input must be
        evidential: there is no meaningful answer to "is a product decision
        weaker than a measurement", so a derivation involving one has to state
        its own provenance explicitly rather than compute it.
        """
        if not levels:
            raise ProvenanceError("weakest() needs at least one provenance")
        non_evidential = [q.value for q in levels if not q.is_evidential]
        if non_evidential:
            raise ProvenanceError(
                f"cannot rank {', '.join(sorted(set(non_evidential)))} against "
                "evidence. A derived value whose inputs include a product "
                "decision must decide its own provenance explicitly rather than "
                "inherit one."
            )
        return min(levels, key=lambda e: e.rank)


#: The evidential categories, weakest first. `PRODUCT_INTENT` is absent by
#: design -- membership of this list is what makes a category rankable.
_EVIDENCE_ORDER = [
    Provenance.ENGINEERING_CHOICE,
    Provenance.HELD,
    Provenance.MEASURED,
]


@dataclass(frozen=True)
class Parameter:
    """One named fabrication value, with its provenance.

    Equality includes the name, so two parameters that merely share a magnitude
    are not interchangeable.
    """

    name: str
    value: float | str
    provenance: Provenance
    scope: str
    unit: str | None = "mm"
    is_z_dimension: bool = False
    derived_from: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.derived_from and not self.provenance.is_evidential:
            raise ProvenanceError(
                f"{self.name} is derived from {', '.join(self.derived_from)}, so "
                f"its provenance must be evidential; {self.provenance.value} is "
                "not. Derivation inherits the weakest evidence of its inputs, "
                "and a product decision does not sit on that scale."
            )

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
            "provenance": self.provenance.value,
            "is_evidential": self.provenance.is_evidential,
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
    "PRODUCT SPECIFICATION, not evidence. How far one completed colour level "
    "stands above the one below: a decision about what Layercake should look "
    "like, so no physical claim is being made about it and it carries no "
    "evidence rank. Distinct from the 0.40 mm floor, which IS an evidential "
    "claim that simply has not been tested. Currently equal to the seating "
    "depth by coincidence, not by relationship."
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
            "seating_depth", 0.80, Provenance.MEASURED, _SCOPE_MEASURED_DEPTH,
            is_z_dimension=True,
        )
        floor = Parameter(
            "minimum_recess_floor", 0.40, Provenance.ENGINEERING_CHOICE, _SCOPE_FLOOR,
            is_z_dimension=True,
        )
        return cls(
            visible_step_height=Parameter(
                "visible_step_height", 0.8, Provenance.PRODUCT_INTENT, _SCOPE_H,
                is_z_dimension=True,
            ),
            seating_depth=depth,
            per_side_clearance=Parameter(
                "per_side_clearance", 0.05, Provenance.HELD, _SCOPE_HELD_CLEARANCE,
            ),
            minimum_recess_floor=floor,
            backing_thickness=Parameter(
                "backing_thickness",
                1.2,
                Provenance.weakest(depth.provenance, floor.provenance),
                _SCOPE_BACKING,
                is_z_dimension=True,
                derived_from=("seating_depth", "minimum_recess_floor"),
            ),
            layer_height=Parameter(
                "layer_height", 0.20, Provenance.HELD, _SCOPE_LAYER,
            ),
            offset_join=Parameter(
                "offset_join", "round", Provenance.ENGINEERING_CHOICE, _SCOPE_JOIN,
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
            "provenance_note": (
                "Values do not all make the same kind of claim. 'measured' is "
                "backed by a physical result; 'held' is fixed deliberately "
                "because it could not be resolved; 'engineering_choice' has "
                "never been tested. Those three are evidential and can be "
                "ranked. 'product_intent' is not evidence at all -- it records a "
                "decision about what Layercake should look like -- so it is "
                "excluded from the ranking rather than placed on it. A derived "
                "value inherits the weakest evidence of its inputs."
            ),
            "parameters": {q.name: q.to_dict() for q in self.parameters()},
        }

    def to_markdown(self) -> str:
        lines = [
            "# Fabrication profile",
            "",
            "| Parameter | Value | Provenance | Derived from |",
            "|---|---|---|---|",
        ]
        for q in self.parameters():
            value = f"{q.mm:.2f} mm" if q.unit == "mm" else f"`{q.value}`"
            derived = ", ".join(q.derived_from) if q.derived_from else "-"
            lines.append(
                f"| {_human(q.name)} | {value} | `{q.provenance.value}` | {derived} |"
            )
        lines += [
            "",
            "**Values do not all make the same kind of claim.** `measured` is "
            "backed by a physical result; `held` is fixed deliberately because it "
            "could not be resolved; `engineering_choice` has never been tested. "
            "Those three are evidential and can be ranked, and a derived value "
            "inherits the weakest of its inputs.",
            "",
            "`product_intent` is **not evidence**: it records a decision about "
            "what Layercake should look like, not a claim about physical reality. "
            "It is excluded from the ranking rather than placed on it.",
            "",
            "## Scope of each value",
            "",
        ]
        for q in self.parameters():
            lines.append(f"- **{_human(q.name)}** (`{q.provenance.value}`): {q.scope}")
        return "\n".join(lines) + "\n"


#: Tolerance for layer-multiple and backing comparisons. Generous enough to
#: absorb binary floating point (1.2 - 0.8 is 0.39999999999999991) and far
#: tighter than anything a printer resolves.
_LAYER_TOL = 1e-9


def _human(name: str) -> str:
    return name.replace("_", " ")
