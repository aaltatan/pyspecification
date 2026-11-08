# PHASES

## Round 1 — Agreed in the package-family review
- [x] `Predicate.failures()` returning `tuple[Failure, ...]` (branch `feature/failures`, 280 tests)
- [x] Registries, JSON Schema and argument errors on pyvocabulary (branch `refactor/pyvocabulary`, 259 tests)
- [x] Rule names with a trailing newline are rejected (bug in `re.match` with `$`)
- [x] Open PRs for both branches. Merged into `main` locally for review instead of PRs; pyvocabulary 0.1.0 now comes from PyPI (2026-11-08)

## Next
- [x] `Failure.message`: a `message=` option at registration (and on `object_rule`/`subscriptable_rule`), defaulting to the description, then the docstring
- [x] Collect doctests (`--doctest-modules`): already in `addopts`
- [ ] Run the SQLAlchemy end-to-end test in CI (it needs SQLAlchemy installed)
- [x] Clean up the 3 pre-existing `mypy --strict` findings (unused `type: ignore` in `registry.py`, untyped call in `rules.py`)
- [x] Remove unused `noqa` directives flagged by ruff `RUF100`
