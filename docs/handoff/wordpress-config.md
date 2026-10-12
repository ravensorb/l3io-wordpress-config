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

## For the next `l3io-wordpress-database` session — undelivered

Written 2026-10-12 because the database session ended before this reached it. Point that
session here. Nothing below approves any action in database's repo; each item is for it to
put to Shawn. Delete this section once database has acted on it or declined.

1. **Legacy cleanup.** Shawn retired config's legacy material and wants database to do the
   same, if he approves it there. Config's recipe, in order:
   - **Backup first.** `git fetch origin '+refs/heads/*:refs/remotes/origin/*' --tags`, then
     `git bundle create <dir>/repo-all-refs.bundle --all`, `git bundle verify`, and a test
     clone from the bundle confirming every tag. Also save the retired-name release files
     (`gh release download <tag>`) and a tag→commit list.
   - **Branch `legacy/pre-cleanup`** at `main`'s tip, plus a `LEGACY.md` listing every
     retired tag, branch and release with its full SHA. Upstream work not in `main`'s
     history goes to its own `legacy/*` branch.
   - **Before deleting,** check each legacy tag is an ancestor of `main` or on a legacy
     branch (`git merge-base --is-ancestor`), and that no sibling pins it. Then
     `gh release delete <tag> --yes --cleanup-tag` and
     `git push origin --delete <tags> <branches>`.
   - **Keep** `v0.0.0`, the version baseline, and the current release tag.
   - **Docs on `main`** describe the current package only. `LICENSE` keeps the original
     copyright line, which MIT requires.

   The permission classifier blocks the deletions until Shawn approves them explicitly.
   Reference: config's `LEGACY.md` on `legacy/pre-cleanup`, and commit `3b74f6d`.
2. **Floating tags.** Config maintains `v<major>`/`v<major>.<minor>` as backup does
   (commit `db7625d`). It also narrowed `publish.yml`'s push filter from `v*` to
   `['v*.*.*', '!v0.0.0']`, so a floating tag can never start a publish. If database
   enables floating tags, do the same; the guards are in config's
   `tests/test_workflow_gates.py`.
3. **Next config release.** Database pins config's `v0.0.2`, which the cleanup left in
   place. When config releases (`0.1.0` suggested; not yet decided):
   - repin to the new tag;
   - add a test that reads a `DB_PASSWORD` containing `);`, since the parser fix for such
     values only reaches database through that repin.

   Database's suite already passes against config's development build: 128 passed, and
   13 skipped for want of MySQL.

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
