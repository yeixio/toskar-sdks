# Releasing

One tag publishes every SDK at one version: `v0.2.0` puts `toskar` 0.2.0 on PyPI, npm, and crates.io, `Toskar` 0.2.0 on NuGet, and `ai.toskar:toskar` 0.2.0 on Maven Central, tags the Go module `go/v0.2.0`, and makes a GitHub release (`.github/workflows/release.yml`). PyPI, npm, NuGet, and crates.io take the packages by trusted publishing: they trust this repository's release workflow, so no token is stored. PyPI's and npm's packages also say which workflow built them (provenance).

## A release

1. **Set the version** on a branch, and merge it:

   ```sh
   scripts/set-version.sh 0.2.0
   ```

   It sets `typescript/package.json`, `python/pyproject.toml`, `kotlin/build.gradle.kts`, `dotnet/src/Toskar/Toskar.csproj`, and `rust/Cargo.toml`. The release fails if they don't match the tag.
2. **Tag the merge commit** on main, and push the tag:

   ```sh
   git tag v0.2.0 <merge commit> && git push origin v0.2.0
   ```

3. **Watch the release workflow.** It checks the versions and that the tag is on main, builds and checks every package, publishes them, tags `go/v0.2.0`, and makes the GitHub release with notes from the merged pull requests.

To rehearse, run the release workflow by hand (Actions → release → Run workflow): it builds and checks every package, and publishes nothing.

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

**Swift** needs nothing either: Swift Package Manager reads the package from this repository's root `Package.swift` at the `vX.Y.Z` tag itself.

**Maven Central** (Kotlin and Java, `ai.toskar:toskar`) takes a signed upload with a token, from the `maven-central` environment.

1. The namespace `ai.toskar` is registered at [central.sonatype.com](https://central.sonatype.com/publishing/namespaces), verified by a TXT record on `toskar.ai` (Route 53; done 2026-10-30). Keep the record: it does no harm, and re-verifying needs it.
2. In GitHub: toskar-sdks → Settings → Environments → **New environment** `maven-central`. Optionally add yourself as a required reviewer.
3. The upload token: central.sonatype.com → your account → **Generate User Token**. It shows a username and a password once:

   ```sh
   gh secret set MAVEN_CENTRAL_USERNAME --repo yeixio/toskar-sdks --env maven-central
   gh secret set MAVEN_CENTRAL_PASSWORD --repo yeixio/toskar-sdks --env maven-central
   ```

4. The signing key. Maven Central needs every file signed, and the public key on a keyserver:

   ```sh
   gpg --quick-gen-key "Toskar SDKs" ed25519 sign 5y   # asks for a passphrase
   gpg --list-keys "Toskar SDKs"                       # the long hex line is KEY
   gpg --keyserver keyserver.ubuntu.com --send-keys KEY
   gpg --armor --export-secret-keys KEY | gh secret set SIGNING_KEY --repo yeixio/toskar-sdks --env maven-central
   gh secret set SIGNING_PASSWORD --repo yeixio/toskar-sdks --env maven-central   # the passphrase
   ```

   Keep a backup of the key somewhere safe (`gpg --export-secret-keys --armor KEY`), as you would a password: releases signed with a new key are fine, but the old key can't be recovered.

The release's `kotlin` job builds, signs, uploads, and releases. Central checks the upload (signatures, POM, sources, and javadoc jars) and publishes it within about half an hour; search.maven.org can take longer to show it.

**NuGet** (.NET, `Toskar`) takes the package by trusted publishing: the workflow trades its GitHub identity for a NuGet key that lasts an hour.

1. Sign in at [nuget.org](https://www.nuget.org) (an account with two-factor authentication).
2. Your username → **Trusted Publishing** → **Create**, with:
   - Policy Name: `toskar-sdks release`
   - Package Owner: you
   - Repository Owner: `yeixio`
   - Repository: `toskar-sdks`
   - Workflow File: `release.yml`
   - Environment: `nuget`
3. In GitHub: toskar-sdks → Settings → Environments → **New environment** `nuget`, and its **variable** (not a secret: it's your public profile name) `NUGET_USER`, your nuget.org username:

   ```sh
   gh variable set NUGET_USER --repo yeixio/toskar-sdks --env nuget --body <your nuget.org username>
   ```

The first release creates the package, and it's yours. Optionally, after it: nuget.org → **Manage Packages** → `Toskar` → reserve the `Toskar` prefix (ID prefix reservation, by email to NuGet), so packages named `Toskar.*` show they're yours.

**crates.io** (Rust, `toskar`) takes a trusted publisher only for a crate that exists, so the first release publishes with a token, once.

1. Sign in at [crates.io](https://crates.io) with GitHub, and verify your email (Account Settings): crates.io publishes nothing from an account without one.
2. Account Settings → **API Tokens** → **New Token**: name `toskar-sdks first release`, expiring in 7 days, scope `publish-new`, crates `toskar`.
3. In GitHub: toskar-sdks → Settings → Environments → **New environment** `crates-io` → **Add environment secret** `CARGO_REGISTRY_TOKEN`, the token:

   ```sh
   gh secret set CARGO_REGISTRY_TOKEN --repo yeixio/toskar-sdks --env crates-io
   ```

4. After the first release: crates.io → crate `toskar` → **Settings** → **Trusted Publishing** → **Add**, with repository owner `yeixio`, repository `toskar-sdks`, workflow `release.yml`, and environment `crates-io`.
5. Revoke the token on crates.io, and delete the `CARGO_REGISTRY_TOKEN` secret. Every release after that uses the workflow's identity.

**Optional: approve each release** for these too: `nuget` and `crates-io` → **Required reviewers**.

## After the first release

- toskar.ai/developers installs with `npm install toskar` and `pip install toskar` instead of from git (the `INSTALL` and `PY_INSTALL` snippets in yeixio/toskar.ai `app/developers/page.tsx`).
- Toskar Core's `examples/README.md` does the same.
- `go get github.com/yeixio/toskar-sdks/go@v0.1.0` gets a version, not a commit.
- A new language's first release: toskar.ai/developers gets a section for it, and its README and the root README's table say where to install it from.

## Keeping up with Toskar Core

The sync workflow (`.github/workflows/sync.yml`) runs each day. When Toskar Core has a newer release, it syncs the spec, regenerates the SDKs and their reference docs onto a `sync/core-<tag>` branch, and runs CI and the conformance cases there, against that Core release. When they pass, it publishes to main with the repository secret `SYNC_DEPLOY_KEY`, so no one has to approve it. main needs an approved pull request, except from a deploy key. Nothing reaches PyPI, npm, or Go until a release tag. If a check fails, if main moved meanwhile, or if the key isn't set, it opens a pull request instead.

`SYNC_DEPLOY_KEY` is the private half of a deploy key with write access, titled "SDK sync workflow", on this repository only. To set it up or replace it:

```sh
ssh-keygen -t ed25519 -N '' -C "toskar-sdks sync" -f sync-key
gh repo deploy-key add sync-key.pub --repo yeixio/toskar-sdks --allow-write --title "SDK sync workflow"
gh secret set SYNC_DEPLOY_KEY --repo yeixio/toskar-sdks < sync-key
rm sync-key sync-key.pub
```

