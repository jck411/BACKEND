# Project Rules

## Virtual Environments & Dependencies

- Use [`uv venv`](https://github.com/astral-sh/uv) for Python virtual environments.
  Do not use `venv` or `virtualenv` directly.

## 1. Language & Interpreter Versions

- Pin the exact Python version in `pyproject.toml`:
  ```toml
  [project]
  requires-python = "==3.13.0"
  ```

## 2. Dependency Management

### 2.1 Adding a Dependency

- Use the package manager:
  - Python: `uv add <package>`
  - Node: `npm install <package>` or `pnpm add <package>`
- Commit both the manifest and lockfile (`uv.lock`, `package-lock.json`, etc.).

### 2.2 Installing Dependencies / CI

- Install strictly from the lockfile:
  - Python: `uv sync --strict`
  - Node: `npm ci` or `pnpm install`

## 3. Async, Concurrency & Event-Driven Design

- Use event-driven patterns (async tasks, callbacks, pub/sub).
- Use async I/O for external ops >10 ms; never block the main thread.
- Set timeouts for long tasks and raise timeout errors.
- Protect critical sections; never suppress cancellation errors.

## 4. Code Organisation & Style

- Each file should have a single responsibility.
- Keep files small and focused (<150 lines, avoid >300 lines).
- Limit complexity: cyclomatic complexity <15, ≤3 public symbols per file (domain modules: up to 5, 400 LOC).
- Reuse abstractions, eliminate duplication, avoid "god" classes.
- Use focused names (e.g., `ConnectionManager`).
- Import order: stdlib → third-party → internal.

## 5. Security

- Never commit or overwrite `.env`; read secrets via environment variables.
- Never log tokens, secrets, or PII.

## 6. Testing

- Use the standard testing framework (e.g., `pytest` for Python).
- Maintain ≥40% line coverage on critical logic.
- Place all tests in `tests/`.
- Linting and type checking must pass in CI.
- Enforce typing gradually.

### 6.1 Automatic Hook Installation

Python (uv):
```bash
uv add --dev pre-commit
uv run pre-commit install
# Optional: Enable pre-commit hooks by default in all new repos:
uv run pre-commit init-templatedir ~/.git-template
git config --global init.templateDir ~/.git-template
```
- Ensure `.pre-commit-config.yaml` is present.

## 7. Logging

- Use `structlog` for structured JSON logging.
- Include `event`, `module`, and `elapsed_ms` fields.

## 8. Performance

- Optimize only after profiling shows a pure function uses >2% of total CPU/time.
- Set realistic SLOs; avoid premature optimization.

## 9. Error Handling

1. Identify potential failure points.
2. Instrument logging at those points.
3. Analyze logs to determine root causes.
4. Address those causes.
- Fail fast on invalid input.
- Catch broad exceptions only at process boundaries.
- Fix root causes, not symptoms.

## 10. General Engineering Principles

- Prefer simple solutions; remove obsolete paths.
- Adopt new tech only when it fully replaces the old.
- Avoid stubbing/fake data outside tests.
- Deliver exactly what is requested; propose enhancements separately.
- Focus on functionality over enterprise features for hobby projects.
- Keep project scope manageable.
