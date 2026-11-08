# PHASES

## Round 1 — Agreed in the package-family review
- [x] `Predicate.failures()` returning `tuple[Failure, ...]` (branch `feature/failures`, 280 tests)
- [x] Registries, JSON Schema and argument errors on pyvocabulary (branch `refactor/pyvocabulary`, 259 tests)
- [x] Rule names with a trailing newline are rejected (bug in `re.match` with `$`)
- [ ] Open PRs for both branches; the refactor stays a draft until pyvocabulary is on PyPI

## Next
- [ ] `Failure.message`: a `message=` option at registration, defaulting to the rule description
- [x] Collect doctests (`--doctest-modules`): already in `addopts`
- [ ] Run the SQLAlchemy end-to-end test in CI (it needs SQLAlchemy installed)
- [x] Clean up the 3 pre-existing `mypy --strict` findings (unused `type: ignore` in `registry.py`, untyped call in `rules.py`)
- [x] Remove unused `noqa` directives flagged by ruff `RUF100`
