# Releasing

One tag publishes every SDK at one version: `v0.2.0` puts `toskar` 0.2.0 on PyPI and npm, tags the Go module `go/v0.2.0`, and makes a GitHub release (`.github/workflows/release.yml`). PyPI and npm take the packages by trusted publishing: they trust this repository's release workflow, so no token is stored, and each package says which workflow built it (provenance).

## A release

1. **Set the version** on a branch, and merge it:

   ```sh
   scripts/set-version.sh 0.2.0
   ```

   It sets `typescript/package.json` and `python/pyproject.toml`. The release fails if they don't match the tag.
2. **Tag the merge commit** on main, and push the tag:

   ```sh
   git tag v0.2.0 <merge commit> && git push origin v0.2.0
   ```

3. **Watch the release workflow.** It checks the versions and that the tag is on main, builds and checks both packages, publishes them, tags `go/v0.2.0`, and makes the GitHub release with notes from the merged pull requests.

To rehearse, run the release workflow by hand (Actions → release → Run workflow): it builds and checks both packages, and publishes nothing.

**Versions are the SDKs' own,** not Toskar Core's: many Core releases don't change the API, and the SDKs have fixes of their own. What says which Core an SDK works with is the client contract. Each release names the contract it was built for (`CONTRACT_VERSION`, and the release notes), and works with any Core of that contract's major version; an older Core may lack newer routes and fields. They're 0.x while the SDKs are in preview. A release after a Core sync that changes the contract's minor version is a minor release here too.

## Setting up the registries, once

These need the accounts' owner, and are done once.

**PyPI**

1. Sign in at [pypi.org](https://pypi.org) (an account with two-factor authentication).
2. Your account → **Publishing** → **Add a new pending publisher** → GitHub, with:
   - PyPI Project Name: `toskar`
   - Owner: `yeixio`
   - Repository name: `toskar-sdks`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

The first release creates the project, and it's yours. Nothing is stored in GitHub.

**npm**

npm takes a trusted publisher only for a package that exists, so the first release publishes with a token, once.

1. Sign in at [npmjs.com](https://www.npmjs.com) (an account with two-factor authentication).
2. Account → **Access Tokens** → **Generate New Token** → Granular Access Token: read and write on packages, with **Bypass two-factor authentication** on, expiring in 7 days.
3. In GitHub: toskar-sdks → Settings → Environments → `npm` (the first release workflow run makes it; or **New environment** `npm`) → **Add environment secret** `NPM_TOKEN`, the token.
4. After the first release: npmjs.com → package `toskar` → **Settings** → **Trusted Publisher** → GitHub Actions, with organization `yeixio`, repository `toskar-sdks`, workflow `release.yml`, and environment `npm`. Then, in the same settings, **Publishing access** → require two-factor authentication and disallow tokens.
5. Delete the token on npmjs.com, and the `NPM_TOKEN` secret.

Every release after that publishes by trusted publishing.

**Optional: approve each release.** In GitHub, Settings → Environments → `pypi` and `npm` → **Required reviewers**: a release then waits for your approval before it publishes.

**Go** needs nothing: the module is public, and the Go proxy and pkg.go.dev take it from the `go/vX.Y.Z` tag.

## After the first release

- toskar.ai/developers installs with `npm install toskar` and `pip install toskar` instead of from git (the `INSTALL` and `PY_INSTALL` snippets in yeixio/toskar.ai `app/developers/page.tsx`).
- Toskar Core's `examples/README.md` does the same.
- `go get github.com/yeixio/toskar-sdks/go@v0.1.0` gets a version, not a commit.
