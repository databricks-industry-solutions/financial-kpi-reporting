### Contributor License Agreement (CLA)

By submitting a contribution to this repository, you certify that:

1. **You have the right to submit the contribution.**  
   You created the code/content yourself, or you have the right to submit it under the project's license.

2. **You grant us a license to use your contribution.**  
   You agree that your contribution will be licensed under the same terms as the rest of this project, and you grant the project maintainers the right to use, modify, and distribute your contribution as part of the project.

3. **You are not submitting confidential or proprietary information.**  
   Your contribution does not include anything you don’t have permission to share publicly.

If you are contributing on behalf of an organization, you confirm that you have the authority to do so. You agree to confirm these terms in your pull request. Any request that does not explicitely accept the terms will be assumed to have accepted. 

## Keeping the repo public-safe

This is a public repository. Do not commit anything tied to an internal network or process:

- **No private registries/mirrors** in `uv.lock`, `pyproject.toml`, `.npmrc`, `uv.toml`, or any config — pin public PyPI / npm. Route to a mirror locally via env vars (see the **Environments & proxies** section of the README); `.npmrc`/`uv.toml` are gitignored.
- **No internal references** — Jira keys (`FEIP-*`, `LPP-*`), `go/*` links, or internal workspace hosts. That trail belongs in the internal Demo Review Document / Jira, not here.
- **Before opening a PR**, run the guard:
  ```bash
  bash scripts/check-public.sh
  ```
  It fails if any of the above leak into tracked files. Re-lock dependencies (`uv lock`) only from an environment with public registry access so the lockfile stays portable.
