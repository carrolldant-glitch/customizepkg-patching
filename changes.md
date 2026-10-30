# customizepkg-patching 20-3 — verified candidate

Prepared for Danny on 2026-10-29 (US/Eastern). **Human source review accepted;
three separately approved clean-chroot builds passed.** Danny reviewed this
verification report and approved source-only GitHub publication to
[carrolldant-glitch/customizepkg-patching](https://github.com/carrolldant-glitch/customizepkg-patching).
That approval excludes AUR actions, binary releases, signing and host installation.
No automatic helper integration is configured.

## Baseline and confirmed failures

The original AUR `20-2` baseline is
`2fd4c24d99ccef3781694521f2ac63d0c3dd44a3`. Its complete tracked contents were
inspected before execution: `PKGBUILD`, `.SRCINFO` and the inline Bash script.
The previous scan found it orphaned; that metadata is not an adoption grant.

Two failures were reproduced with tiny, owned fixtures in a rootless,
network-disabled environment:

- GNU patch's exit status **1** for rejected hunks was accepted by the helper,
  which eventually returned success. Its guard checked only statuses above 1.
- Preview patched files in place, then reverted them. The shared revert routine
  deleted every empty restored file, confusing an existing empty file with a
  newly added file. It also operated on unrelated `.original` files.

The original evidence is retained locally under
`/home/elias/projects/aur-necromancer/build/triage-2026-10-29-next.VPuaDr/`.
Those original-behavior probes are not passing repair tests.

## Repair

- Replace apply-and-revert preview with a private, bounded copy of regular
  top-level files. A failed staged application never reaches real application.
  Empty files and unrelated backups/rejects are no longer deleted by preview.
- Use GNU patch's unified, noninteractive, forward-only, zero-fuzz mode, with
  read-only input failures and no version-control checkout. Preserve fresh
  `.original` backups; refuse collisions with existing affected backups.
- Check affected input contents/types again before real application. Reject
  nested, special-file, symlink and reserved-suffix targets. Use native quoting
  and file operations; do not evaluate filenames as shell code.
- Propagate errors through the shared change-pair iterator. Treat diff's status
  1 as a difference, not an error; preserve actual diff/editor/patch failures.
- Generate saved patches into a temporary file, validate before replacement,
  and rename within the selected patch directory. Reject empty/oversized saves;
  preserve old configuration on generation/write failure and preserve its mode
  on replacement. New configuration files are private (0600).
- Use `pkgbase` for split packages, falling back to the first `pkgname`. Read
  identity in a child shell so recipe variables/functions do not overwrite the
  helper's state. Printing patches and editing pairs no longer source recipes.
- Add `CUSTOMIZEPKG_DIR` for user-owned patch storage, retaining the original
  `/etc/customizepkg.d` default. Nothing configures Paru, Yay, Pacman or sudo.
- Reject unknown/conflicting modes and refuse modifications as root. Vim
  previews use private files with its read-only flag; explicit editing still
  edits the requested real file pairs.

## Packaging and license

Keep upstream version `20` and increment the downstream package release to `3`.
Install directly from the source script instead of moving/consuming it. A real
`makepkg --repackage` check now succeeds against the same extracted source tree.

Declare the coreutils commands actually invoked at runtime, retain Bash,
diffutils, patch and optional Vim, and add Python/ShellCheck only to check
dependencies. Add source checksums, generated `.SRCINFO`, an offline `check()`
and installed usage/trust documentation. No Python runtime is introduced.

`AUTHORS` and `COPYING` are unchanged copies from upstream commit
`125518163db775c42124200f26946a9f9849fffd`. AUTHORS explicitly specifies GPL
version 2; use `GPL-2.0-only` instead of the old ambiguous `GPL` label. Original
credits remain, with Danny identified as Contributor rather than AUR maintainer.

## Earlier rootless validation

Rootless evidence: `verification/rootless-final.NYlrrD/` (ignored, local only).
These host-tool diagnostics are separate from the three clean builds below.

- Bash syntax and ShellCheck pass for the helper.
- Ordinary-user, network-disabled package build completed successfully using
  the host's read-only toolchain and package inventory.
- **60 offline CLI checks pass in `check()` and the same 60 pass against the
  extracted installed command.** This repeats 60 checks, not 120 distinct ones.
- Checks cover both original failures, multi-file acceptance/rejection, empty
  files, addition/deletion/truncation, backup collisions, hidden and unusual
  names, no filename command evaluation, split-package identity, recipe-state
  isolation, mode errors, failed editors/saves/application, saved-patch round
  trips, links, traversal/absolute paths and resource limits.
- Installed executable mode is 0755; executable, documentation and both license
  files byte-match the reviewed source. Archive paths match the inspected file
  list; no install script, service or automatic hook is present.
- `.SRCINFO` byte-matches makepkg's generated output. All frozen input hashes
  still match after build and repackaging. The same source tree repackages
  successfully, with identical executable/document/license payloads.
- Namcap reports **no errors**, with four package warnings: the intentionally
  empty configuration directory and dependency-detection warnings for coreutils,
  diffutils and patch. The script actually invokes their commands, so these
  dependencies remain. The recipe's missing Maintainer warning is intentional
  Contributor attribution while the package remains unadopted.

Rootless package SHA-256:
`1ae295ad1c525bbbfdfabeb312433c0c53fe6f8dfb926647911b3918770b0da1`

Repackage SHA-256:
`5df8dd24cd1aed5f8084d5926dc545981bb82d49e10a93a0b6adadf5a51f3967`

Complete archives differ in build metadata/timestamps. No bit-identical archive
reproducibility claim is made. Earlier rootless development runs remain as
historical evidence; they are not extra clean-chroot passes.

## Clean-chroot validation — 3/3

Evidence: `verification/clean-chroots.wxjsNC/pass-1/`, `pass-2/` and `pass-3/`.
Each directory retains its frozen recipe, logs, artifact, installed-file
readback, `RESULTS.txt` and a checked `evidence.sha256` manifest.
These ignored build roots, logs and binaries remain local; they are not part of
the source repository. The runnable regression checks are included as `check.py`.

Each job used a separately created Arch `extra-x86_64` root and Danny's exact
approval. The roots shared the host kernel and normal verified package cache,
not a previously built root. No packages were installed on the host. Recipe
execution and tests ran as UID 1001, never root; the checker rejects root.

- All three builds exited **0**, passing Bash syntax, ShellCheck and all **60
  offline CLI checks** in `check()`.
- Each actual installed-in-chroot command passed `--version` and the same 60
  checks again in rootless, network-disabled Bubblewrap. It mounted only that
  chroot's read-only `/usr`, the checker, and private temporary data—not the
  personal home or keys. These are repeated validations, not 360 distinct tests.
- Archive paths match the expected file list. Executable mode is 0755. All four
  executable/document/license files byte-match the reviewed sources, their
  installed-in-chroot counterparts and the other two builds.
- All frozen review inputs remained unchanged. Each `.BUILDINFO` records the
  reviewed PKGBUILD hash. Fresh dependencies included patch `2.8.1-1`,
  ShellCheck `0.11.0-163` and Python `3.14.8-1`.
- Namcap reported **no errors** in any pass, with the same reviewed warnings
  explained above. `checkpkg` skipped comparison because no official-repository
  package exists; this is not a successful official-package comparison.

Package SHA-256 values, in pass order:

```text
pass 1: 17c9b869c81a45213af2989bb2b6c6bdfe21c504a26568dafa938cc525c0577a
pass 2: 8be2979d027ba859d09c7ad7b808a627bf817edd71ebb3c55f77bc8c29cea3be
pass 3: eb8f47201462fcb73c4217e0d7721a906f38e5461e335438b7014d5a9dde90dc
```

Complete archives differ in build metadata/timestamps. Matching payloads and
three successful fresh builds do **not** establish bit-identical archives or
guarantee behavior on every system. The original reviewed report is retained
with each frozen recipe; only this report was updated after verification.
`verification/verified-inputs.sha256` records the files reviewed after those
builds. Publication snapshots preserve that report and separately record the
source-only upload; the older review manifest describes the pre-build snapshots.

## Limits and remaining gates

**This helper is not a security sandbox.** Reading package identity still
sources a trusted PKGBUILD, whose top-level commands can act with the user's
authority. A child shell isolates shell state, not filesystem/network access.

**Real application is not an atomic multi-file transaction.** Concurrent edits,
signals, power loss and I/O failures can cause partial changes after preflight.
Use a disposable checkout, do not run concurrent writers, and inspect retained
backups on failure. A nonzero result does not promise rollback.

This repair deliberately supports regular top-level files only. Input snapshots
are capped at 4096 files/256 MiB, and saved patches at 4 MiB. Large source trees
and recursive workflows need a different isolated approach. GNU patch versions
may reject embedded-newline filenames; the check requires correct application
or rejection in staging without changing working files. Native diff/patch is
reused instead of introducing a custom patch parser or a deployment framework.

Clean-chroot count: **3/3**. The reviewed build inputs required no further
changes. Danny approved source publication on 2026-10-29; only this report's
release status was updated afterward. AUR publication and any host/helper
installation still require separate approval.
