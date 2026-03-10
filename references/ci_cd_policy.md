# CI/CD Policy

## Branch Model

- `main` is the only long-lived branch.
- Every change starts from the latest `origin/main`.
- Every change lands through a pull request into `main`.
- Merged task branches must be deleted.

## Pull Request Gates

Required checks on every pull request into `main`:

- `CI / test`
- `CI / governance`

Merge must stay blocked until all required checks pass.

## Commit Policy

Every commit must follow Conventional Commits:

- `feat:` for backward-compatible features
- `fix:` for backward-compatible bug fixes
- `docs:`, `test:`, `chore:`, `ci:` and similar non-release commits for support changes
- `!` marker or `BREAKING CHANGE:` footer for major-version bumps

## Versioning Policy

- `feat:` -> next minor version
- `fix:` -> next patch version
- breaking change -> next major version
- no release tag is created when merged commits contain only non-release types

The version workflow runs on pushes to `main` and tags the merge commit.

## Release Policy

- a `v*` tag triggers the release workflow
- release workflow builds the container image from [docker/Dockerfile](/home/artem/repos/mnemos/docker/Dockerfile)
- images are published to GHCR under `ghcr.io/<owner>/<repo>`

## Local Developer Setup

Run:

```bash
make install-hooks
```

This installs a `commit-msg` hook that rejects non-Conventional-Commit
messages before they enter local history.
