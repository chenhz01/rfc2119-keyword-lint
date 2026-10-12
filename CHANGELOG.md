# Changelog — rfc2119-keyword-lint

All releases are local drafts; no remote operations are performed.

## v0.1.1 — 2026-10-13

Fixed:
- K6 MAY-density now counts uppercase normative statements only; unicode-adjacent K3 confirmed.

Changed:
- self_test expanded to >=60 cases across functional / exception / extreme-edge
  categories (scaffold v2 four defenses: SystemExit capture, Unicode-safe
  matching, Windows newline-safe fixtures, SUMMARY last line).
- README: added Performance section with [Measured] numbers and in-repo
  reproduction commands.

## v0.1.0 — 2026-10-13

Added:
- Initial local draft: RFC 2119 keyword consistency linter.
- argparse CLI (pure standard library), self_test.py, MIT LICENSE.
