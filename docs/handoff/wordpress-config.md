# Handoff — session `wordpress-config`

**Resume line:** You are `wordpress-config`, working in `l3io-wordpress-config`. Read
`docs/handoff/wordpress-config.md`, then continue.

Written 2026-09-27. Work items are tagged `[todo]` / `[blocked]` / `[done]`; nothing here
is tagged as a fact, because a stale task that later reads as a measurement is the failure
this separation prevents. Durable facts about working in this repo live in `AGENTS.md`
instead — this file is transient state, which `AGENTS.md`'s own rules exclude.

## What this session owns

Repo `l3io-wordpress-config`, published as **`l3io-wordpress-config`**, importing as `l3io.wp.config`. Release
position **1 of 3** in the `l3io.wp` family and the gate on the other two.

Work arrived as a handoff, not as l3io-pm epics — so this repo has no stories, and
`/l3io-pm-plan` has nothing to plan. That is expected, not a gap.

## Done

- [done] Full internal rewrite under the PEP 420 `l3io.wp` namespace, five layers
  (`domain/ core/ ports/ adapters/ cli/`). `AGENTS.md` describes the invariants.
- [done] Four defects fixed against ADR-0010 (type fidelity, `set()` symmetry, bounded
  insertion, CLI falsy-vs-absent) plus `$table_prefix` support and read-back verification.
- [done] uv + hatchling packaging, zero runtime dependencies, `py.typed`, 85 tests at ~92%,
  ruff and `mypy --strict` clean.
- [done] GitHub Actions CI with full nektos/act parity — every job replays locally, nothing
  gated off.
- [done] **`v0.0.2` released** — tag, GitHub Release with wheel and sdist, and
  `l3io-wordpress-config 0.0.2` in the Gitea registry. PyPI untouched and still opt-in.
  `v0.0.1` preceded it under the retired distribution name `l3io-wp-config`, whose assets
  are still attached to that release (see the open decisions below).
  An earlier tag was cut and then fully withdrawn — tag, registry entry and release
  all deleted — when the family restarted its versioning, and the version floor that
  assumed it is gone. The release line starts at `0.0.1`.
- [done] Published to the internal Gitea registry; re-publishing an existing version is a
  verified no-op rather than a 409.
- [done] Handoff 01's "Done when" audited item by item.

## Awaiting a decision from Shawn — do not act on these unprompted

- [blocked] **Publish to PyPI.** Nothing is on PyPI (404). `publish-pypi` is reachable only
  by explicit `workflow_dispatch → target=pypi`; a tag deliberately cannot reach it.
- [blocked] **Make the `liquidlogiclabs` Gitea org public.** It is currently *limited*, so
  the package index returns 401 unauthenticated and every consumer needs credentials.

Both were put to him independently by this session and by `wordpress-backup`. The second is
the cheaper action.

## Open, not blocked

- [todo] No spec exists for this package and there is no `spec-index.md`, so CI's
  spec-pointer and spec-freshness checks skip entirely. **Nothing mechanically verifies that
  this code and the governing ADRs still agree** — the last alignment pass was by hand and
  will rot. `wordpress-backup` reported their own spec index came out at 24,720 bytes against
  a 16,384 threshold, so turning this on is not free.
- [todo] A workflow contract test — for each job, if any *executable* line reads a repo path
  or calls `uv` without `--no-project`, assert the job has a checkout. Deliberately not
  written: one real instance across two repositories is not a pattern. The shape is recorded
  so whoever hits it a second time inherits the design.

## Read first, in this order

1. `AGENTS.md` here — invariants, CI conventions, registry facts, known pitfalls.
2. `../l3io-wordpress-backup/_bmad-output/implementation-artifacts/handoffs/` —
   `00-SHARED-CONTEXT.md` then `01-l3io-wp-config.md`. The de facto spec for this package.
3. `../l3io-wordpress-backup/docs/adr/` — ADR-0007 (packaging, console scripts), ADR-0010
   (parser scope and read-back), ADR-0012 (naming); and `ARCHITECTURE-SPINE.md` for AD-1,
   AD-2, AD-14, AD-15, AD-27.

Those documents are authoritative. Do not re-derive their decisions; if one looks wrong,
say so and stop.

## Cautions — what was tested versus what was inferred

A handoff is read as settled fact, so the distinction is drawn explicitly.

**Tested by execution:**
- The registry username/password pair from the secret store returns **401** against the
  private Gitea package registry. Basic auth with the same username plus an API *token* as
  the password returns 200 — the pair is not interchangeable. Credential names, locations and
  values are deliberately not recorded here: this repository is public.
- Gitea's package index serves no root listing: `.../pypi/simple/` is 404 while
  `.../pypi/simple/<name>/` is 401. `/api/v1/version` returning 200 separates "needs auth"
  from "wrong host".
- `uv publish --check-url` does **not** skip an already-published version here — it
  attempted the upload and 409'd.

**Inferred, never verified — treat as hypotheses:**
- *Why* `--check-url` failed. The observed behaviour is the upload attempt; the explanation
  offered elsewhere is that the check does not receive the publish credentials. That cause
  was never confirmed.
- That making `liquidlogiclabs` public would make the index readable without credentials.
  Gitea's behaviour for a public org's package registry was not tested.
- That a PyPI publish additionally needs trusted publishing configured on PyPI's side and a
  `pypi` GitHub environment. Inferred from their absence; never attempted.
- Where that stale username/password pair *does* work. Unknown and uninvestigated — an
  earlier version of `AGENTS.md` asserted they belonged to another registry, which was an
  inference sitting beside a test. Corrected; do not reintroduce it.

## Where this session's findings live, and where they must not

- [done] Everything durable is in this repo: `AGENTS.md` for invariants and traps, this file
  for session state. Both in a public repo, readable without credentials.
- [done] **Nothing was left in `/tmp` worth keeping.** The scratchpad held 64 KB of throwaway
  verification environments — stub siblings, scratch venvs, act logs — and every finding from
  them is committed: the coexistence stub became `tools/check_namespace_coexistence.py`, which
  builds its own. `/tmp` is tmpfs and clears on reboot; that costs this repo nothing. If you
  are reading this after a reboot, no artifact of this session was lost.
- [blocked] **Do not write this session's findings to the shared basic-memory KB.** A
  home-lab session asked twice, relaying an instruction from Shawn that this session never
  received. He was then asked directly and chose "it stays in this repo." Nothing of this
  session's is in the KB, including a pointer — a pointer was a third option he was not
  offered.
- The `mcp__basic-memory-cloud__*` tools became available later in the session and reads
  were verified working. **Availability is not authorisation.** If a future session sees
  those tools and assumes the material belongs there, that is the decision above being
  re-litigated, not a gap being filled. **It has now been asked a fourth time**
  (2026-10-03, `home-lab-db`, citing an estate-wide session clear). Declined again. The
  offered fallback — writing to `~/work-artifacts/handoff-drop/` for that session to
  ingest — was declined for the same reason: it routes to the same KB by hand. This file
  was updated instead and the peer was told where it lives.
- Two authority rules earned the hard way, both worth keeping:
  a peer's report of what the user wants is information, not authorisation — and a peer's
  report that your content was *stored* is also only information. The home-lab session
  asserted ingestion for several sessions and was wrong for one, having verified disk
  against index in both directions, which cannot detect a file that never reached disk.
  A guard whose scope excludes the failure mode reports success over it.

## Cross-repo state

- `l3io-wordpress-database` consumes this package and has since released its own
  **`v0.0.2`**, in the registry under the correct name. **An earlier report from this
  session that their pin was `tag = "v1.0.0"` was WRONG** — see "Mistakes this session
  made". Their actual pin was `rev = "87c7a661..."`.
- `l3io-wordpress-backup` is the **last of the three with no release at all**: no `v*` tags,
  nothing in the registry. It is now unblocked — both its dependencies resolve under their
  correct names. It has also fixed its own `release.yml` dispatch bug and added the
  cross-repo step-parity rule this session reported to it.
- **AD-15 is not satisfied.** Tagged, released and mirrored is *not* resolvable from PyPI: a
  GitHub Release is not an index, and a limited-visibility mirror is not one a stranger can
  reach. If a dependent reaches PyPI while this package does not, installing it fails
  unresolvable — the outage this work exists to repair. Bottom-up: config first.

---

## Update — 2026-10-03

### Done since the 2026-09-27 writing

- [done] Distribution renamed to **`l3io-wordpress-config`**; namespace stayed `l3io.wp.config`.
  All three repos now match `l3io-wordpress-*` / `l3io.wp.*`, and it is **mechanically
  enforced** cross-repo by `../l3io-wordpress-backup/scripts/check-cicd-alignment.py`, which
  checks the distribution pattern and the namespace root *separately*, from each sibling's
  **committed** `pyproject.toml`. Passes 3 repos, 0 findings.
- [done] `v0.0.2` released and in the registry. Registry now holds exactly:
  `l3io-wordpress-config 0.0.2`, `l3io-wordpress-database 0.0.2`, and the stale
  `l3io-wp-database 0.0.1`.
- [done] `17cc438` — both `release.yml` dispatch sites moved from a hand-rolled
  `gh workflow run` to `LiquidLogicLabs/git-action-trigger-workflow@v2`. Input names were
  verified against the action's own `action.yml` at `v2` (`workflow-name` required, and it is
  `publish.yml`'s top-level `name:` — "Publish" — not the filename; plus `ref`, `inputs`,
  `token`).
- [done] `718e3d9` — four rediscovered facts into `AGENTS.md`. The one most likely to waste
  someone's afternoon: **`infisical secrets get` returns an empty string with exit 0** when
  `--env` is omitted, so a script that trusts it authenticates with nothing and the resulting
  401 reads as a bad token. Only `--env=prod` returns a value.
- [done] `b30eca9`, `7b51a97` — l3io module upgrades 3.1.3 → 3.2.1 → 3.2.2, committed and
  pushed; CI green on `7b51a97` (all 11 jobs). 3.2.2 added `review` to
  `VALID_SPRINT_STATUS`, which nothing in its diff announces.

### Open decisions — awaiting Shawn, do not act unprompted

- [blocked] **The legacy 2-component tags.** `v0.3 v1.0 v1.2 v1.3 v1.4` on this remote,
  `v1.0` on database's. None carries a GitHub Release, and both version-derivation paths
  already exclude them (`release.yml`'s `tag-format: "v*.*.*"` and `pyproject`'s
  `git_describe_command`, which are documented to agree). Their only live effect is a
  collision trap: **floating *minor* tags have the shape `vX.Y`, exactly these**, so the
  first `1.x` release would silently repoint a 2018 tag. This blocks giving config and
  database the floating tags that backup already has — backup is safe only because it has
  no legacy `v*` tags. Options put to him: delete the legacy tags, or skip floating-minor in
  these two and have the guard encode the exception.
- [blocked] **Retired-name release assets.** `l3io_wp_config-0.0.1.*` on this repo's
  `v0.0.1` and `l3io_wp_database-0.0.1.*` on database's — installable wheels under names
  nobody should install. Stripping only the assets keeps tag, release and notes.
- [todo] Retire `l3io-wp-database 0.0.1` from the registry. Safe now that `0.0.2` is
  published under the right name; database session's call, worth confirming no lock
  references it first.

### Mistakes this session made — not recoverable from git, and the reason this section exists

- **A registry package was deleted by accident.** Probing HTTP methods against the Gitea
  package endpoint with a loop that included `DELETE` **executed it** (204), removing
  `l3io-wp-config 0.0.1`. Verified afterwards that `l3io-wp-config` appeared **0 times** in
  both siblings' `uv.lock`, so nothing broke — luck, not care. Never enumerate HTTP methods
  against a real endpoint.
- **Two wrong-scope matchers produced two confidently wrong reports.** (1) An unscoped grep
  matched `tag = "v1.0.0"` inside a *comment* in database's pyproject and it was reported to
  them as their live pin; the real pin was `rev = "87c7a661..."`. (2) Grepping for
  `gh workflow run publish.yml` concluded backup had no publish dispatch at all, when it uses
  the org action — the matcher was the wrong *shape*. Same failure class this project keeps
  hitting: **a matcher whose scope differs from the question reports confidently about a set
  that does not contain the answer.** Anchor on the question, and check what the pattern
  cannot match.
- **A claim about release triggering was asserted before checking.** This session told the
  database session their `GITHUB_TOKEN` finding "appears not to hold", because `publish.yml`
  had run for `v0.0.2`. It had run on `workflow_dispatch`, not `push` — their finding was
  right. The `push`-event Publish runs on `v0.0.0`/`v0.0.1` came from tags pushed by hand
  from a terminal, which is exactly why the absence of the dispatch is easy to miss.

### Loose ends that are not ours

- [todo] An l3io upgrade **3.2.2 → 3.2.4** is sitting uncommitted in this repo (~54 paths)
  from a plugin reload. Previous two were committed with the substance separated from the
  timestamp churn; do the same.
- [todo] `l3io-doctor`'s `steps/health-check.md` cites `scripts/tests/test-detect-layout.py`
  as the Check 21 coverage evidence, but the installed payload ships no `scripts/tests/` and
  `payload-manifest.json` no longer lists it. Likely deliberate exclusion rather than
  deletion upstream, but as installed the claim cannot be checked. Module author's call.

### State of this repo's own BMad artifacts

`/l3io-doctor` ran clean — 25 checks, nothing flagged. That green is narrow and should not
be read as a populated project passing: `_bmad-output/` holds only empty state scaffolding,
so 16 of the 25 checks passed over an empty set. This repo still has no stories and no spec
index, as the 2026-09-27 entries above record.

---

## Update — 2026-10-12: rename, BMad 3.2.4, and the hardening brief

### Done since 2026-10-03

- [done] **Repository renamed** on GitHub `ravensorb/py-wpconfigr` → `ravensorb/l3io-wordpress-config`
  (GitHub redirects the old URL), and the local folder to `l3io-wordpress-config`. Live
  references followed in `76e6db2`; historical mentions of the old name are left as written.
  The per-repo Claude memory moved with the folder.
- [done] `6ee1dfe` — the l3io **3.2.2 → 3.2.4** reinstall listed under "Loose ends" above,
  committed. Skill trees are byte-identical to the two siblings. `_bmad/scripts/pm-status.py`
  is now **3.4.2** in all three repos (installed with its own `self-install`; the module
  upgrade had left every copy stale at a different version).
- [done] The read-first pointer to `01-l3io-wordpress-config.md` was wrong in both this file
  and `AGENTS.md`; the file is `01-l3io-wp-config.md`. Fixed.
- [done] **Verified 2026-10-12 after the rename**, on a fresh `uv sync --locked`:
  `pytest` 101 passed, coverage 92%; `../l3io-wordpress-backup/scripts/check-cicd-alignment.py`
  3 repos, 0 findings.
- [todo] **Not pushed.** `main` is ahead of `origin/main` — `git log origin/main..main` for
  the list; a count written here went stale within the hour. Last green GitHub CI: `c379ae3`.

### This session's brief

Shawn's goal: make this package **rock solid and stable** before the other two, since it is
release 1 of 3 and gates both. Suggested order:

1. `/l3io-doctor`, then reconcile this file. Everything tagged above is from earlier
   sessions; re-verify before relying on it.
2. The largest stability gap is the open `[todo]` above: **no spec and no `spec-index.md`**,
   so nothing mechanically checks that the code and ADR-0010/0007/0012 still agree.
3. Review the parser against ADR-0010's stated limits. A regex parser is permitted only by
   that ADR, and its "Revisit when" conditions are the test of whether it still holds.
4. Settle or re-raise the `[blocked]` decisions (legacy 2-component tags, retired-name
   release assets, PyPI publish, Gitea org visibility). They remain Shawn's.

### Notes for this session

- Secrets: Infisical, project **`home-lab-discovery`**; this machine has a machine identity
  configured and the session is approved to read from it. `AGENTS.md`'s trap still applies:
  `infisical secrets get` without `--env=prod` returns empty with exit 0.
- Legacy PyPI names `wpdatabase2` (0.0.15) and `wpbackup2` (0.2.21) are owned by this project
  and still point at the old GitHub URLs, which redirect. The plan for them (tombstone releases
  pointing at the new names, done last) is in
  `../l3io-wordpress-backup/_bmad-output/implementation-artifacts/handoffs/04-legacy-names-and-registrations.md`.
  The legacy `wp-configr` / `wpconfigr` name was upstream's, not ours.
- PyPI trusted publishing is bound to the GitHub owner/repo/workflow. None of the three
  `l3io-wordpress-*` names exists on PyPI or TestPyPI (checked 2026-10-12), so register any
  publisher under the **new** repository name.

### Brief step 1 — `/l3io-doctor` and reconciliation (2026-10-12)

**Doctor: 26 checks, one flag, nothing in its repair sequence.** Read the green as the
2026-10-03 entry did — narrow. The state tree is empty, there is no `spec-index.md` and no
`docs/adr/`, so Checks 16, 17 and 19 did not run at all and most of the rest passed over an
empty set.

- [blocked] **Check 24 — agent instruction block absent.** For `--runtime claude` it would
  *create* `CLAUDE.md`; this repo has only `AGENTS.md`, and neither sibling has a `CLAUDE.md`
  either. The doctor itself marks this "on request" and keeps it out of its repair sequence.
  Not done; Shawn's call whether the family gets one.
- Check 20 is green with two informational lines: `baseline_drift` (`bmb_version` expected
  `v2.2.2`, found none — bmb is not installed here) and three `status_contradictions` for
  deprecated skills the manifest no longer lists. Neither affects this repo.
- [todo] The `scripts/tests/test-detect-layout.py` loose end above still holds at 3.2.4:
  `health-check.md` Check 21 still cites it, the installed doctor still ships no
  `scripts/tests/`, and `payload-manifest.json` still does not list it.

**Re-verified by execution today:**
- `uv sync --locked` + `pytest`: 101 passed, 92%. `AGENTS.md` still said 85; corrected.
- `check-cicd-alignment.py`: 3 repos, 0 findings.
- Remote tags here: `v0.0.0 v0.0.1 v0.0.2 v0.3 v1.0 v1.2 v1.3 v1.4`; database: `v0.0.0 v0.0.1
  v0.0.2 v1.0`. `v0.0.0` is the annotated "Baseline" tag, not the withdrawn version.
- Retired-name assets are still attached: `l3io_wp_config-0.0.1.{whl,tar.gz}` on this repo's
  `v0.0.1`, `l3io_wp_database-0.0.1.{whl,tar.gz}` on database's.
- PyPI and TestPyPI: 404 for all three `l3io-wordpress-*` names.
- Last GitHub CI run is still `c379ae3`, green; nothing since has been pushed.

**Not re-verified:** the Gitea registry contents, including whether `l3io-wp-database 0.0.1`
is still there. Reading the token from Infisical was refused by the harness's permission
classifier this session, so the 2026-10-03 registry list stands as recorded, unchecked.

**Found while reconciling:**
- [done] **Coverage floor.** `fail_under = 92` (observed 92.18%, line coverage, identical on
  3.11–3.14); the `contracts` subset runs pass `--no-cov`. Planted violation: ignoring
  `tests/test_cli.py` fails at 75.90%. Replayed under act: `contracts` and all four `test`
  legs green.
- [todo] **`make ci` / `make ci-job` fail outside a TTY on this machine.** The `Makefile`
  comment above `ACT_BARE_SECRETS` says act "does not prompt for [GITHUB_TOKEN] when absent";
  tested 2026-10-12, it does prompt (`Provide value for 'GITHUB_TOKEN'`, act 0.2.89,
  `~/.actrc` declares `-s GITHUB_TOKEN`) and then fails. Earlier sessions likely had the
  variable exported. Workaround that worked: `GITHUB_TOKEN="$(gh auth token)" make ci-job
  JOB=...`. Not fixed — whether the `Makefile` should supply it is a design change, and the
  comment is wrong either way.

### Brief step 2 — replaced: traceability instead of a spec index (2026-10-12)

The brief's step 2 rested on a wrong premise, which this file stated as fact: that a spec
index would let CI check the code against the ADRs. It would not. `spec-align.py build`
produces a table of contents of planning-doc headings for l3io-execute's story `Spec:`
pointers; with no stories here it checks nothing, and `ci.yml` never ran a spec check at
all. Shawn chose a traceability table instead.

- [done] `docs/traceability.toml` — one row per governing rule, all 42 (AD-1..29, ADR-0001..0013),
  each judged binds/doesn't against the text at backup `0431282`; `tests/test_traceability.py`
  checks it. Planted violations (renamed enforcer, edited rule, removed row, binding row with
  no coverage) each fail; a worktree with no sibling reports the drift test *skipped*; act
  replays `static` and all four `test` legs green.
- 14 rules bind this package. **Gaps the audit found, stated in their rows as `untested`:**
  - [todo] AD-4 — no `dry_run`/`what_if` grep gate.
  - [todo] AD-10 — nothing asserts only `cli/` configures logging.
  - [todo] AD-14 — only file-adapter paths checked; public entry points not derived.
  - [todo] AD-15 — `publish-pypi`'s never-from-a-tag `if:` is unchecked.
  - [todo] ADR-0007 — console script + `python -m` untested.
  - [todo] ADR-0009 — Python floor and matrix coverage untested; this is FR-48, whose family
    shape is `l3io-wordpress-database`'s `tests/test_declared_facts.py`, blocked here on 3.14.
    Note ADR-0009 says the matrix covers "every version in the range", and `>=3.11` is
    open-ended — that reads in favour of *adding* the 3.14 classifier. Still Shawn's call.
  - [todo] ADR-0013 — no check that workflows never gate on `env.ACT`.

**Problems in the authoritative documents** — reported, not resolved; they live in
`l3io-wordpress-backup` and are not this session's to edit:
- [blocked] **AD-30 does not exist.** This repo's `AGENTS.md` and `tests/test_package_version.py`
  cite "AD-30 — the git tag is the version"; the spine stops at AD-29 and no ADR records it.
  It appears only in comments in backup's `Makefile` and `release.yml`. Not a table row.
- [blocked] **AD-24 vs AD-2.** AD-24 binds "all three packages" to `opentelemetry-api`; AD-2
  forbids this package any dependency. AD-10 carves this package out of structlog; AD-24 has no
  matching carve-out. Judged non-binding by AD-2's precedence.
- [blocked] **ADR-0007** still names the console script `l3io-wp-config`.
- [blocked] **ADR-0012** still says the fork republishes at "a version above 1.4".
- [blocked] **ADR-0013** says `make ci` runs act under `infisical run`; this repo's
  `Makefile` uses placeholders instead. That is the same spot where `make ci-job` now fails
  outside a TTY (see step 1's entry), so the ADR's mechanism may also be the fix.
- Relayed the five document problems to `l3io-wordpress-database-24`, at Shawn's direction,
  for the backup session. No backup session was open, so database put them to Shawn directly.
  Its answers:
  - AD-30 is cited in database too, in 7 places, so whatever backup decides applies to both.
  - [todo] **database's `make ci` does not have the TTY failure.** Its Makefile wraps act
    in `infisical run ... --env prod`, which is ADR-0013's mechanism and puts `GITHUB_TOKEN`
    in the environment. Config's placeholder approach is the outlier, so the likely fix
    for config's `make ci-job` is to align with database's wrapper rather than amend the
    ADR. Not done.
