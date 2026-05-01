# ADR-0005: Python Toolchain (inherited from Fabrica template)

> **Note:** this ADR was originally `0001-toolchain.md` in the Fabrica
> scaffold and is preserved here with the heading renumbered so future
> readers can see why the toolchain looks the way it does. ADRs 0001–0004
> cover pubmed-digest's project-level design decisions.

**Status:** Accepted
**Date:** 2026-04-30
**Deciders:** Luke Marshall

## Context

This repository is the canonical Python project template for this public
portfolio. Every project created from it inherits its toolchain decisions, so
the choices made here compound across every future repo.

Constraints shaping the decision:

- **Cadence:** 30–60 minutes per day. Tooling must not eat the session.
- **Quality bar:** senior-level production code. Tests, types, lint, CI
  must be enforced, not aspirational.
- **Audience:** public GitHub. Code is portfolio material; reviewers
  include hiring managers and peers.
- **Scope:** Python 3.12+. Biotech-first applied AI / biomedical
  tooling in subsequent projects, framed across four career lanes
  (applied AI/ML engineering, solutions engineering, technical sales,
  independent building).
- **Recency:** current best-practice as of 2026-04. Choices that age
  poorly cost re-tooling time later.
- **CI:** GitHub Actions free tier; tooling must run cleanly there.
- **Solo for now:** team-coordination concerns are deferred.

The Python tooling landscape consolidated significantly in 2024–2026.
Several long-standing tools were eclipsed by faster, more cohesive
replacements written in Rust. This ADR captures the choices made at the
moment of consolidation so future-me knows what the considered alternatives
were and why they lost.

## Decision

Adopt the following toolchain for this template and every project created from
it:

| Concern | Choice |
|---------|--------|
| Package management | [`uv`](https://github.com/astral-sh/uv) |
| Linting + formatting | [`ruff`](https://github.com/astral-sh/ruff) |
| Type checking | [`pyright`](https://github.com/microsoft/pyright) (strict mode) |
| Build backend | [`hatchling`](https://hatch.pypa.io/latest/) |
| Package layout | `src/`-layout |
| Test runner | [`pytest`](https://docs.pytest.org/) + `pytest-cov` |
| Local enforcement | [`pre-commit`](https://pre-commit.com/) |
| CI | GitHub Actions |

## Options Considered

### Package management: `uv` vs `poetry` vs `hatch` vs raw `pip` + `venv`

| Dimension | `uv` | `poetry` | `hatch` | `pip`+`venv` |
|-----------|------|----------|---------|--------------|
| Speed | 10–100× pip | ~pip | ~pip | baseline |
| Python version mgmt | yes | no (needs `pyenv`) | yes | no |
| Lockfile | yes (`uv.lock`) | yes | no native | no |
| Dep groups (PEP 735) | yes | partial | yes | n/a |
| Single binary | yes | python pkg | python pkg | builtin |
| Active dev (2026) | very | slowing | active | n/a |

**Chose `uv`.** It collapses the `pip` + `venv` + `pyenv` + `poetry` +
`pip-tools` stack into one Rust binary. Speed is a real productivity
multiplier — `uv sync` is sub-second on a warm cache; `poetry install`
takes 30+ seconds. Native Python version management means no `pyenv`
dependency. Active development by Astral.

**Why not `poetry`?** Was the right answer 2020–2024. Slower, clunkier
CLI, and `pyproject.toml` semantics drift from the PEP standards. Many
ML/AI projects in 2026 are migrating off it.

**Why not `hatch`?** Closer in spirit to `uv` but slower and with a less
ergonomic CLI. Hatch is still excellent as a *build backend* (`hatchling`,
which we use), just not as the package manager.

### Linting + formatting: `ruff` vs `black` + `isort` + `flake8` + `pyupgrade` ensemble

| Dimension | `ruff` | ensemble |
|-----------|--------|----------|
| Speed | sub-second | seconds to minutes |
| Tools to configure | 1 | 4+ |
| Rule coverage | broad and growing | broad |
| Format + lint in one | yes | no |
| Active dev | very | mixed |

**Chose `ruff`.** Replaces the entire `black`/`isort`/`flake8`/`pyupgrade`
toolchain with a single Rust binary. Faster and one config block in
`pyproject.toml` instead of three or four config files. Curated rule sets
(`E`, `W`, `F`, `I`, `N`, `UP`, `B`, `C4`, `SIM`, `RET`, `PTH`, `TID`,
`TC`) give comprehensive coverage out of the box.

**Why not the ensemble?** Industry standard 2018–2023, now obsolete.
Maintaining four tools' configs and waiting for them serially is wasted
effort.

### Type checking: `pyright` vs `mypy`

| Dimension | `pyright` | `mypy` |
|-----------|-----------|--------|
| Speed | fast | slower |
| Strict mode default | yes | no |
| Editor integration | excellent (Pylance) | adequate |
| Maintained by | Microsoft | community |
| PEP coverage | aggressive | conservative |

**Chose `pyright`.** Faster, stricter by default, better IDE story
(Pylance is the default Python LSP for VSCode and uses pyright under the
hood). Strict mode catches more real bugs than mypy's default mode.

**Why not `mypy`?** Still the dominant choice in older projects but
slower, defaults are weaker, and PEP adoption is conservative. Acceptable
for legacy work; not worth choosing for new projects.

### Build backend: `hatchling` vs `setuptools` vs `poetry-core` vs `flit-core`

**Chose `hatchling`.** Modern, lightweight, no `setup.py` cruft, supports
PEP 517/518/621 cleanly. Used as the build backend; the Hatch CLI is
*not* required.

**Why not `setuptools`?** Decades of legacy syntax (`setup.py`,
`setup.cfg`) and edge cases. Works fine for big legacy projects;
unnecessary baggage for new ones.

**Why not `poetry-core` / `flit-core`?** Tied to their respective
package managers in subtle ways. `hatchling` is more independent.

### Package layout: `src/` vs flat

**Chose `src/`-layout.** Package code lives at `src/<package>/` instead
of `<package>/` at the root. This prevents a class of import bugs where
tests accidentally import from the working-directory copy of the package
instead of the installed copy — false-positive tests that pass during
dev and fail when shipped. The cost is one extra folder level.

**Critical caveat (learned 2026-04-25):** `hatchling`'s editable install
for `src/`-layout is fragile, especially when the project path contains
spaces. Symptom: `uv sync` reports success but `pytest` fails with
`ModuleNotFoundError`. **Mitigation:** explicitly set
`pythonpath = ["src"]` in `[tool.pytest.ini_options]` and
`extraPaths = ["src"]` in `[tool.pyright]`. This decouples test/type
infrastructure from the editable-install build step entirely.

## Trade-off Analysis

The biggest tradeoff is **cohesion vs ecosystem inertia**: the chosen
stack is tightly integrated and dramatically faster, but pulls this template
away from the still-large `poetry` + `black` + `mypy` mainstream.
Code review by a `poetry`-shop reviewer will require five minutes of
"oh, you're using `uv` — that's the new thing" explanation. Worth it for
the speed and cohesion gains.

Smaller tradeoff: **pyright strict mode** demands annotations everywhere,
which slows down throwaway prototyping. Mitigation: use a non-strict
project (or `# pyright: basic` at file top) for genuine throwaways. For
portfolio work, strictness is the point.

The `src/`-layout / hatchling editable-install fragility is a known
papercut, mitigated as described above. If hatchling fixes it cleanly in
a future release we can drop the `pythonpath`/`extraPaths` workaround,
but they cost nothing to keep.

## Consequences

**Easier:**
- New project setup: `uv init` plus a few minutes of customizing
  `pyproject.toml` instead of an hour of tooling decisions.
- CI: every project's CI is the same four steps — install `uv`, sync,
  ruff, pyright, pytest.
- Code consistency: one `pyproject.toml` is the entire config; no
  scattered `setup.cfg`/`tox.ini`/`.flake8`/`.isort.cfg`.
- Onboarding (future-self or collaborators): one tool to learn per
  concern, recent docs, active community.

**Harder:**
- Reading older Python projects: `setup.py`, `requirements.txt`, `tox`,
  `mypy`-only typing — all still common in legacy code, especially
  scientific Python and biotech repos. We'll need to read them as a
  separate dialect.
- Some niche packages don't yet publish wheels that work cleanly with
  `uv`'s resolver; rare but happens.

**To revisit:**
- 2027-Q2: re-evaluate the toolchain. Tools move fast. If something has
  meaningfully replaced any of these, we update the template and migrate
  active projects.
- If `hatchling` ships a fix for src-layout editable installs, drop the
  `pythonpath`/`extraPaths` workaround.

## Action Items

1. [x] Implement toolchain in `pyproject.toml`.
2. [x] Wire up GitHub Actions CI to enforce all four checks.
3. [x] Wire up `pre-commit` hooks for local enforcement.
4. [ ] Use this repository as the template for Project 1 (`pubmed-digest`) to
       validate the template flow end-to-end.
5. [ ] Re-evaluate at 2027-Q2.
