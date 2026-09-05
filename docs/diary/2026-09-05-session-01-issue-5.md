# Development diary — 2026-09-05 — Session 01, issue #5

**Branch:** `feat/5-fabrication-profile`
**Ticket:** #5 — Fabrication profile: parameters with explicit evidence levels

## What this is

The first product code. `src/layercake/` now exists alongside
`src/layercake_spike/`, and the product package never imports the spike — there
is an AST-walking test that asserts it rather than trusting discipline.

`FabricationProfile` holds the seven fabrication values, each as a named
`Parameter` carrying its evidence level and a scope note.

## The two things that made this worth its own ticket

**Provenance became data.** Session 01 established that these values are not
equally trustworthy: seating depth is *measured*, clearance is *held* because
neither Spike 02 round could resolve it, the minimum recess floor is an untested
*engineering choice*, and backing thickness derives from the last two. That
distinction was previously prose in docstrings, maintained by a test that
grepped for the phrase "NOT physically validated". It is now structured, and any
report emitted from a profile carries it.

Backing's evidence is **computed** as the weakest of its inputs rather than
asserted. If the floor is ever measured (#11), the backing upgrades on its own
instead of waiting for someone to notice.

**Parameters are named values, not floats.** Three unrelated concepts are
currently all 0.8 mm — visible step height, seating depth, and the round-1
as-printed backing. `Parameter` equality includes the name, so two values that
merely share a magnitude are not interchangeable, and arithmetic requires
reaching for `.mm` deliberately.

The stronger guard is behavioural rather than structural: a test perturbs `H` to
1.4 mm and asserts seating depth, floor and backing are all unmoved and the
profile still validates. That catches a derivation quietly relying on the
coincidence, which type-level separation alone would not.

## Design decisions worth review

**Evidence ranking.** `ENGINEERING_CHOICE < HELD < MEASURED`. Placing *held*
above *engineering choice* is a judgement: a held value has an empirical reason
for sitting where it does (the process could not resolve finer), whereas an
engineering choice has judgement only. The ranking is consulted only when
deriving one parameter from others, and the current derivation gives the same
answer either way — backing inherits `ENGINEERING_CHOICE` from the floor
regardless. So nothing turns on it today, but it is a real opinion in the code.

**Visible step height is `ENGINEERING_CHOICE`.** It is product intent rather
than a measurement, and no round tested whether 0.8 mm is the right visible step.
Arguably it wants a fourth level — something like `product_intent` — because it
is not a failure of evidence so much as a different *kind* of value. Left at
three levels because the ticket specified three.

**Duplication with the spike is deliberate.** `spike02/params.py` still holds
its own copies. The spike records what was actually built and measured; the
product profile records what the product will build. Making the spike consume
the product profile would couple an experiment's recorded history to a value
that can move. #9 makes the product path authoritative; the spike stays as
historical record.

## Scope

Held to #5. No canonical-model work pulled forward, nothing wired into the
derivation, no parameter value changed — the ticket moves and types them, it does
not re-decide them.

## Result

210 tests pass, 28 of them new. Both spike pipelines unchanged and still PASS.
