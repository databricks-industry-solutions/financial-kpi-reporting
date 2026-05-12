# Pre-Publication Compliance Record

This repository follows Databricks' policy for making an internal repo
publicly accessible. A public repo is externally accessible + indexable;
all content, history, issues, PRs, workflows, and CI logs are public.

This file is the durable record of approvals + controls. **Do not flip the
repo to public until every "TODO" below is replaced with the real
reference / date / approver.**

> Owner accountability: the requester/owner implements *and* maintains
> these controls. "Review Complete" is not ongoing compliance — if
> violations or drift are found, do not proceed (or revert to private)
> until remediated.

---

## 1. Sensitive-content scan

- [x] Repo + git history scanned for PII, customer IDs, internal URLs /
      system names / architecture references, secrets / keys / tokens.
- [x] Internal Jira / FE-tracker links removed (FEIP-* references stripped
      from README; internal demo-tier audit removed from repo).
- [x] No `.env`, credential, or secret files in working tree or history.
- [x] Sample identities are synthetic (`*@example.com`).
- [x] No hardcoded internal hostnames; Confluence / Lakebase / workspace
      host values are widgets or env vars.
- [ ] **TODO — Owner**: re-run the scan immediately before flipping
      public; record date here: `___________`.

## 2. Package / artifact publication

- [x] Synthetic data only — see `NOTICE` and `SECURITY.md`.
- [x] Docs state intended use, supported environment, and known
      limitations (`README.md`, `SECURITY.md`).
- [ ] **TODO — Owner**: APX dependency is Databricks-internal (see
      `NOTICE`). Confirm APX is approved for external distribution via
      this repo, OR vendor/replace it before publishing. Reference:
      `___________`.
- [ ] **TODO — Owner**: If publishing any wheels / npm packages /
      release tarballs, confirm metadata + docs are public-safe.

## 3. Dependency / license compliance

- [x] `LICENSE.md` present (Databricks Industry Solutions DB license,
      inherited from the template scaffold).
- [x] `NOTICE.md` present.
- [x] Dependency licenses documented in `README.md`.
- [x] All runtime deps are OSS-permissive (MIT / BSD / Apache 2.0 / ISC /
      LGPL 3.0 for `psycopg`, which is acceptable as a dynamically linked
      driver).

## 4. Legal approval (go/lpp)

- [ ] **TODO — Owner**: file LPP request at go/lpp and link the approval
      record below before publishing. Non-OSS / non-public packages
      require approval before external distribution.
  - LPP request: `___________`
  - Approval date: `___________`
  - Approver: `___________`

## 5. OSS hygiene

- [x] `LICENSE.md` (Databricks Industry Solutions DB license).
- [x] `NOTICE.md`.
- [x] Maintainer contact section in `README.md`.
- [x] `CODEOWNERS` configured at `.github/CODEOWNERS`.
- [x] `SECURITY.md` disclosure path: `security@databricks.com`.
- [x] `.github/CODEOWNERS` lists named maintainers: `@simonkuijpers`,
      `@sujayd555`.

## 6. Security controls

- [x] CI builds + tests on every push / PR (`.github/workflows/ci.yml`).
- [x] SCA / vulnerability scan in CI: `pip-audit` (Python) + `bun pm
      audit` (JS).
- [x] CodeQL SAST in CI for Python and JavaScript / TypeScript.
- [x] Dependabot configured for `uv`, `npm`, and `github-actions`
      (`.github/dependabot.yml`).
- [x] Tagged-release build job (`release` job runs on `v*` tags, attaches
      built artifacts to a GitHub Release).
- [ ] **TODO — Owner**: enable GitHub repo settings (cannot be set from
      this repo's files):
  - [ ] Secret scanning + push protection — **on**
  - [ ] Dependabot alerts + Dependabot security updates — **on**
  - [ ] Branch protection on `main`: require PR, require CODEOWNERS
        review, require status checks (`validate-bundle`,
        `build-and-test`, `vuln-scan`, `codeql`), disallow force-push
  - [ ] Restrict who can publish releases / push tags

## 7. Approvals

- [ ] **TODO — Owner**: peer approval (must NOT be the requester).
  - Reviewer: `___________`
  - Date: `___________`
- [ ] **TODO — Owner**: VP / lead written approval.
  - Approver: `___________`
  - Date: `___________`
  - Link to written approval (email / doc / ticket): `___________`

## 8. Ongoing maintenance

- [ ] **TODO — Owner**: name the current maintainer(s) responsible for
      issues, PRs, security patches, and dependency upgrades. Confirm
      they have time + authority to maintain the repo going forward.
  - Maintainer(s): `___________`
  - Confirmation date: `___________`

## 9. Exceptions (if any)

If any item above cannot be satisfied, file both:

- [ ] Legal exception via go/lpp — link: `___________`
- [ ] Security exception via go/securityexception — link: `___________`
- [ ] Documented rationale below:

> _Rationale:_

Scope of any exception is valid only for **this repository**. New repos
or new components require a fresh intake via go/entsecintake.

---

## Help

`it-support@databricks.com`

---

**Last reviewed:** _fill in before flipping public_  
**Reviewed by:** _fill in before flipping public_
