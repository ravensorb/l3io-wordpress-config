# Handoff — session `wordpress-config`

**Resume line:** You are `wordpress-config`, working in `l3io-wordpress-config`. Read
`docs/handoff/wordpress-config.md`, then continue.

Transient session state only: open decisions, open work, and cautions that still bind.
Durable facts about working in this repo live in `AGENTS.md`. Items are tagged `[todo]`
(open work) or `[blocked]` (Shawn's decision — ask, don't act). The full history behind
this file, through 2026-10-12, is on the `legacy/pre-cleanup` branch; `main` carries
current state only.

## What this session owns

`l3io-wordpress-config`, importing as `l3io.wp.config`: release **1 of 3** in the `l3io.wp`
family, and the gate on the other two. Work arrives as handoffs, not l3io-pm epics, so the
state tree is empty by design.

## Current state (2026-10-12)

- Last release: **`v0.0.2`**, on GitHub Releases and the internal Gitea registry. Nothing
  is on PyPI.
- Remote refs: tags `v0.0.0` (version baseline) and `v0.0.2`; branches `main`,
  `legacy/pre-cleanup` and `legacy/upstream-2019`. Older tags, the `v0.0.1` release and
  `dev2` were retired on 2026-10-12; `LEGACY.md` on `legacy/pre-cleanup` lists them.
- `main` is pushed and green on GitHub CI (11 of 11). 255 tests, 94.75% line coverage
  against a floor of 94. Python 3.11–3.14 declared and tested.
- `docs/traceability.toml` maps every governing rule to what enforces it. All gaps are
  closed.
- Unreleased behaviour changes since `v0.0.2`:
  - new public `ConfigKeyError`;
  - `nan`/`inf` are refused;
  - no stdlib exception escapes `WpConfigFile`;
  - quoted values containing `);` or `;` are read and written correctly;
  - only column-0 `$variables` are read.

  `l3io-wordpress-database` confirmed it is compatible.
- `make ci` replays the pipeline under act via `infisical run`, and leaves nothing in the
  working tree.

## Open

1. [done] **Floating version tags enabled** (Shawn, 2026-10-12), matching backup. They take
   effect on the next real release; none exist yet. Config narrowed `publish.yml`'s push
   filter to `v*.*.*`. Backup's is still `v*`, which would start a publish on a hand-pushed
   floating tag. That is backup's to adopt.
2. [blocked] **Next release version.** `0.1.0` is suggested for the behaviour changes
   above. It is chosen when `release.yml` is dispatched.
3. [blocked] **Publish to PyPI**, and **make the `liquidlogiclabs` Gitea org public**.
   AD-15: nothing reaches PyPI until all three packages can.
4. [blocked] **Fixes to backup's documents**, which belong to backup:
   - AD-30 is cited but undefined;
   - AD-24 conflicts with AD-2;
   - ADR-0007 names the old script;
   - ADR-0010 should record that its revisit condition (a) was met and fixed;
   - ADR-0012 cites "a version above 1.4".
5. [blocked] Doctor Check 24: whether the family gets a `CLAUDE.md` agent block.
6. [todo] Optional: the PHP 8.4 check (300 random configs written by `set()`, read back
   by PHP) as a local-only test, skipped without docker. It is the only grader
   independent of the scanner.
7. [todo] The Gitea registry contents have not been re-read since 2026-10-03.
8. [done] **FR-45 ported** from database's `cc107fb`, plus `make audit` from `0c4e3cf`:
   `.github/workflows/security-audit.yml`, unchanged except its header. Proved not vacuous
   with a planted dev-only `urllib3==1.26.4` (22 advisories, exit 1). All four triggers
   dry-run clean, and the job passes for real under act.

## Sent to `l3io-wordpress-database`

Three items (config's legacy-cleanup run, the floating-tag filter, and the repin after
config's next release) were written into database's own handoff at Shawn's request:
commit `145df84` on its branch `feat/plan-1-core-api`, not pushed. Nothing else waits on
delivery.

## Cautions that still bind

- **Do not write this session's findings to the shared basic-memory KB.** Shawn's answer,
  each time a peer asked, was that it stays in this repo. A peer's report of what Shawn
  wants is information, not authorisation.
- **Never enumerate HTTP methods against a real endpoint.** A loop including `DELETE` once
  deleted a registry package.
- **A matcher whose scope differs from the question reports confidently about the wrong
  set.** Prove every check by planting a failure. A read-back that re-scans with the
  scanner it verifies cannot catch that scanner's bugs.

## Read first

1. `AGENTS.md`.
2. `../l3io-wordpress-backup/_bmad-output/implementation-artifacts/handoffs/`:
   `00-SHARED-CONTEXT.md`, then `01-l3io-wp-config.md`.
3. `../l3io-wordpress-backup/docs/adr/` (ADR-0007, -0009, -0010, -0012, -0013) and
   `ARCHITECTURE-SPINE.md`.
