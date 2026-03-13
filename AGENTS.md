# Agent Guidelines

- Use `uv` for dependency and environment management (`uv add`, `uv sync`, `uv run`).
- Use modern Python typing and keep code compatible with the project `requires-python`.
- Before committing, run:
  - `uv run prek run --all-files`
  - `uv run pytest`
- Keep changes small and readable; update docs when behavior or commands change.
