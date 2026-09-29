# Releasing `@hirefrank/network-jobs`

## Checklist (1.3.1 was cut this way)

1. Bump `version` in `package.json` (use the edit tool — never `npm version`,
   which auto-commits and auto-tags).
2. Add a `CHANGELOG.md` entry.
3. Run `./tests/run.sh` (must exit 0) and `bash -n bin/network-jobs setup lib/agents.sh`.
4. Verify the tarball before publishing:
   `npm pack --pack-destination /tmp/nj-pack` then
   `tar -tzf /tmp/nj-pack/*.tgz` — expect `bin/` entry intact, no
   `__pycache__/` (the `prepack` script deletes it), sane file count.
   Check `package/package.json` in the tarball for a single `scripts` key.
5. Commit, push, tag (`vX.Y.Z`), push the tag.
6. Publish (see Auth below), then `npm view @hirefrank/network-jobs version`
   — the full packument can 404 for a few minutes after a first publish while
   the registry replicates; `/latest` and the website converge first.

## Auth (learned 2026-09-29)

- The maintainer account uses passkey 2FA with no TOTP. Headless/CI shells
  **cannot** complete publish-time step-up (`EOTP` + browser URL fails fast
  without a TTY).
- First publish of a **new** package cannot use a stage-only token (the stage
  endpoint 404s until the package exists) and new bypass-2FA tokens are
  deprecated — so birth the package from a real terminal: run `npm publish`
  in the repo, complete the browser/passkey step when npm waits on it.
- Once the package exists, routine releases can use a **stage-only**
  granular token (`npm stage publish`) + approve in the browser with passkey.
- Keep a TOTP authenticator registered as a fallback (`npm publish --otp=…`
  always works).

## Next step (deferred): trusted publishing

Wire GitHub Actions as an npm trusted publisher so releases publish on tag
push with zero long-lived tokens (immune to the bypass-2FA deprecation,
Jan 2027). Requires one-time setup in the npm package access settings plus
a publish workflow. Not yet done — do it before the next release if the
stage-only flow feels heavy.
