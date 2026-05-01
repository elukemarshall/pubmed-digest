# Python AI/ML Project Template

[![CI](https://github.com/elukemarshall/fabrica/actions/workflows/ci.yml/badge.svg)](https://github.com/elukemarshall/fabrica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A modern Python project template: a clean, opinionated scaffold for applied
AI/ML projects with quality gates already wired in. Clone it, rename it, write
code.

## Why

Starting a Python project well takes hours: pin a Python version, write
`pyproject.toml`, configure a linter, configure a type checker, configure
tests, set up CI, write a license, gitignore a hundred files. Most of that
work is identical on every project. Doing it from scratch each time wastes
hours and produces drift between projects.

This repository is the canonical starting point for new Python projects in
this portfolio. Every meaningful new project starts from it. Improvements to
the template flow forward into future projects; lessons from individual
projects flow back into the template.

The bar is **production-quality from day one**:

- Strict type checking (`pyright` strict mode).
- Comprehensive linting + formatting (`ruff` with a curated rule set).
- Tests via `pytest` with coverage tracking.
- Pre-commit hooks enforcing all of the above locally.
- GitHub Actions running all of the above on every push and PR.
- Minimal Dockerfile + `.dockerignore` for reproducible container smoke tests.
- MIT licensed, public-by-default.

## Quickstart

### Via GitHub UI

Click the green **Use this template** button at the top of this repo, name
your new project, and clone it.

### Via `gh` CLI

```bash
gh repo create my-new-project --template elukemarshall/fabrica --public --clone
cd my-new-project
```

### Then customize

1. Rename the package directory: `mv src/fabrica src/my_new_project`.
2. Update `pyproject.toml`: `name`, `description`, `[project.urls]`, and
   `[tool.hatch.build.targets.wheel] packages` to point at the new path.
3. Replace this README's content with your project's.
4. `uv sync` to install dependencies.
5. `uv run pytest` / `uv run ruff check .` / `uv run pyright` to verify.
6. `git add . && git commit -m "chore: rename template" && git push`.

The CI workflow at `.github/workflows/ci.yml` runs automatically on the
first push.

## What's inside

| Layer | Tool | Purpose |
|-------|------|---------|
| Package management | [`uv`](https://github.com/astral-sh/uv) | 10–100× faster than `pip`/`poetry`. Manages Python version, venv, deps, lockfile. |
| Linting + formatting | [`ruff`](https://github.com/astral-sh/ruff) | Replaces `black`, `isort`, `flake8`, `pyupgrade`. One tool, very fast. |
| Type checking | [`pyright`](https://github.com/microsoft/pyright) | Strict mode. Faster than `mypy`, better editor integration. |
| Testing | [`pytest`](https://docs.pytest.org/) + `pytest-cov` | Discovery, fixtures, coverage. |
| Local enforcement | [`pre-commit`](https://pre-commit.com/) | Runs hooks on every commit before code reaches the repo. |
| CI | [GitHub Actions](https://docs.github.com/en/actions) | Runs the same checks on every push and PR. |
| Container smoke test | [Docker](https://docs.docker.com/) | Verifies the project can build and import in a clean container. |
| Build backend | [`hatchling`](https://hatch.pypa.io/latest/) | Modern, lightweight, no setuptools cruft. |

For the *why* behind these specific choices, see
[`docs/adr/0001-toolchain.md`](docs/adr/0001-toolchain.md).

## Project layout

```text
python-ai-project-template/
├── .github/workflows/ci.yml      ← GitHub Actions config
├── .dockerignore                 ← container build hygiene
├── Dockerfile                    ← reproducible container smoke test
├── .gitignore
├── .pre-commit-config.yaml       ← local quality gates
├── LICENSE                       ← MIT
├── README.md                     ← this file
├── pyproject.toml                ← project + tool config
├── uv.lock                       ← pinned dependency versions
├── src/
│   └── fabrica/
│       ├── __init__.py           ← package entry point
│       └── py.typed              ← PEP 561 marker
└── tests/
    ├── __init__.py
    └── test_smoke.py             ← smoke tests proving infra works
```

## Development

```bash
# Install everything (creates .venv, installs deps, sets up editable package)
uv sync

# Run tests
uv run pytest

# Lint + auto-fix
uv run ruff check . --fix

# Format
uv run ruff format .

# Type check
uv run pyright

# Run all pre-commit hooks against all files (manual trigger)
uv run pre-commit run --all-files
```

## Container Smoke Test

```bash
docker build -t fabrica-template .
docker run --rm fabrica-template
```

The Dockerfile is intentionally minimal. Template-derived services should extend it with
`compose.yml`, health checks, environment-specific config, workers, databases, and runbooks
when the project actually needs production-shaped deployment.

## Requirements

- Python 3.12+ (managed by `uv` — you don't need to install it separately).
- `uv` installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

That's it. `uv` handles the rest.

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgments

Built on the work of [Astral](https://astral.sh/) (`uv`, `ruff`),
[Microsoft](https://github.com/microsoft/pyright) (`pyright`), the
[pytest team](https://docs.pytest.org/), and the broader Python community.
