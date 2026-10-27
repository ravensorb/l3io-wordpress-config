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

## Current state (2026-10-20)

- Last release: **`v0.1.1`** (2026-10-20), the write-permission fix below. Before it,
  **`v0.1.0`** (2026-10-12, Shawn), on GitHub Releases and the internal Gitea
  registry, with floating `v0` and `v0.1` now pointing at `v0.1.1`. Nothing is on PyPI. Verified by
  installing from both the release wheel and the Gitea index. Its notes first published
  as "no changes": the builder took the floating `v0.1` as the previous tag. That is
  fixed in `14512f0`, and the release body was rebuilt from `v0.0.2..v0.1.0` using
  `.github/changelog-config.json`.
- Remote refs: tags `v0.0.0` (version baseline) and `v0.0.2`; branches `main`,
  `legacy/pre-cleanup` and `legacy/upstream-2019`. Older tags, the `v0.0.1` release and
  `dev2` were retired on 2026-10-12; `LEGACY.md` on `legacy/pre-cleanup` lists them.
- `main` is pushed and green on GitHub CI (11 of 11). 269 tests, 95.32% line coverage
  against a floor of 95. Python 3.11–3.14 declared and tested.
- `docs/traceability.toml` maps every governing rule to what enforces it. All gaps are
  closed.
- Behaviour changes released in `v0.1.0`:
  - new public `ConfigKeyError`;
  - `nan`/`inf` are refused;
  - no stdlib exception escapes `WpConfigFile`;
  - quoted values containing `);` or `;` are read and written correctly;
  - only column-0 `$variables` are read.

  `l3io-wordpress-database` confirmed it is compatible.
- `make ci` replays the pipeline under act via `infisical run`, and leaves nothing in the
  working tree.

## 2026-10-20: write-permission defect, fixed in 0.1.1

Reported by `l3io-wordpress-backup` (session cmvgs1vhh0gy7tf01cfd5vtqt) and reproduced
against `v0.1.0`: `WpConfigFile.set()` wrote a temp file under the umask and renamed it
over the original, so a `0640` wp-config.php came back `0644` and DB_PASSWORD became
world-readable. It also did not fsync, used a fixed temp name that a planted symlink
redirected, and dropped the owner when run as root. Fixed on branch
`fix/write-preserves-mode`: `mkstemp` in the same directory, the original's
owner/group then mode copied on before any content is written, file fsync, rename,
directory fsync. Decided: an owner that cannot be kept refuses the write
(`ConfigWriteError`, original untouched), and the package never creates a wp-config.php.
Nine new tests failed on v0.1.0 before the fix. Verified on the built wheel in a clean
venv, as root in a container (`www-data` 33:33 `0640` kept; a non-owner refused, no temp
file left), and by `make ci` under act: 11 of 11.

- [done] **`v0.1.1` released** 2026-10-20 (dispatched at Shawn's instruction once CI
  on `4c842ca` passed): release run 39501412719, publish run 39501448291, both green.
  It is on GitHub Releases and the Gitea registry, not PyPI. Floating `v0` and `v0.1`
  moved to it. Its notes start from `v0.1.0`, so `14512f0` holds now that floating tags
  exist. Both the release wheel and the Gitea install keep a `0640` file `0640` under
  umask 022.  `l3io-wordpress-database` does not write files through this package.
- [done] **Traceability re-judged** against backup's `a865618`. Every drifted row was
  diffed against the text it was last judged on, recovered from backup's history by its
  stored hash, not just re-hashed. New rows: AD-30 binds and every clause has an
  enforcer here; ADR-0014 and ADR-0015 do not bind. AD-24 now excludes this package
  explicitly. ADR-0007, -0010 and -0012 now say what this table reported missing, so
  those notes are gone, and open item 4 below is closed.
- [done] **`make ci` uses the home-lab Infisical project** since `cbc7bc8`, merged
  2026-10-20. Separately, this session's shell had no `INFISICAL_API_URL`, so the CLI
  went to `app.infisical.com` and got 403; `INFISICAL_API_URL=https://secops.ravenwolf.org/api`
  fixed it. That is the host's environment, not this repo's.

## 2026-10-27: CI/CD alignment with `l3io-wordpress-database` (Shawn's request)

Worked out with "wordpress-database - agent 1" (Cursor, cmv567lc34jehtf013cb1ckqh),
reached through `happier session send` because `SendMessage` cannot reach a Cursor session.
Baseline: backup's `scripts/check-cicd-alignment.py` reports config, database and backup
**OK**. Already the same: Python 3.11–3.14, OS Independent, ubuntu-latest, uv `==0.11.6`,
the action pins, the four workflows and their triggers, the release-to-publish flow, the
`v*.*.*` publish filter, release notes from the previous release tag, the namespace check,
and act with home-lab Infisical. Both have released to GitHub through the workflows.

| # | Item | Owner | State |
|---|---|---|---|
| D1 | database `main` green: ruff format, coverage >= 87, `opentelemetry` past GHSA-xcq7-p3pf-p88h | database | in its working tree, not committed |
| D2 | database moves floating `v<major>`/`v<major>.<minor>` tags, ordering test ported | database | in its working tree |
| D3 | database collapses Python under act | — | **kept, agreed**: every Python × engine leg starts a service on 3306 |
| D4 | publish: `tag-info` in version-gate; GitHub release waits on `publish-pypi` | database | in its working tree; equivalent to config's |
| C1 | config adopts database's ruff set (`ARG`, `TRY`, `EM`, `S`, same `tests/*` ignores) | config | `1e9a9d0`, not pushed |
| F1 | add checks for D2, D4 and C1 to backup's `check-cicd-alignment.py`, so alignment is enforced, not remembered | backup | to propose once D1–D4 land |
| F2 | `l3io-age-passphrase` (ADR-0014's binder, a new family package) fails the checker: 21 findings and its name | ? | [blocked] Shawn: bring it to the standard, or let the name rule admit `l3io-<area>` |

## Open

1. [done] **Floating version tags enabled** (Shawn, 2026-10-12), matching backup. They take
   effect on the next real release; none exist yet. Config narrowed `publish.yml`'s push
   filter to `v*.*.*`; backup has since done the same (item 2).
2. [done] **Siblings: release notes once floating tags exist.** Backup adopted config's
   `14512f0` itself in `d85713f` (2026-10-20, on its unpushed branch `infisical-home-lab`):
   a `previous` step resolving the last `v*.*.*` tag, passed as `from-tag`, with the push
   filter narrowed to `v*.*.*` and both guarded in its
   `tests/contracts/test_workflow_invariants.py`. Database has no floating tags; it pins
   config's `v0.1.0` tag in its dev lock, harmless because it never writes the file.
3. [blocked] **Publish to PyPI**, and **make the `liquidlogiclabs` Gitea org public**.
   AD-15: nothing reaches PyPI until all three packages can.
4. [done] **Fixes to backup's documents**: all five landed in backup by 2026-10-20
   (AD-30 defined, AD-24 excludes config, ADR-0007, -0010 and -0012 corrected).
5. [blocked] Doctor Check 24: whether the family gets a `CLAUDE.md` agent block.
6. [todo] Optional: the PHP 8.4 check (300 random configs written by `set()`, read back
   by PHP) as a local-only test, skipped without docker. It is the only grader
   independent of the scanner.
7. [done] **Gitea registry re-read 2026-10-27:** it holds 0.0.2, 0.1.0 and 0.1.1 (wheel and
   sdist each), the same set as GitHub Releases. No retired version or dev build remains.
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
