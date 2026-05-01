# Changelog

All notable changes to `pubmed-digest` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Spawned from the Fabrica template; renamed package to `pubmed_digest`.
- `docs/SPEC.md` and ADRs 0001–0004 covering metadata-first retrieval,
  structured-output grounding, model routing, and benchmark methodology.
- ADR 0005 preserves the inherited toolchain rationale (formerly ADR 0001).

## [0.1.0] - 2026-04-30

### Added
- Initial scaffold with `pyproject.toml` using PEP 735 dependency groups, src-layout package, MIT license.
- `pytest` smoke tests with `pythonpath = ["src"]` to bypass hatchling editable-install fragility.
- `ruff` linting + formatting with curated rule set (E, W, F, I, N, UP, B, C4, SIM, RET, PTH, TID, TC).
- `pyright` strict-mode type checking with `extraPaths = ["src"]` for the same reason.
- `pre-commit` hooks: trailing whitespace, end-of-file, YAML/TOML validation, large-file blocking, private-key detection, merge-conflict detection, ruff, ruff-format, pyright.
- GitHub Actions CI running ruff + pyright + pytest on push and PR.
- ADR 0001 documenting toolchain decisions.
- README with badges, quickstart, stack table, project layout, dev commands.
