#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline regression checks using only disposable, owned package trees."""

import difflib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


SCRIPT = Path(sys.argv[1] if len(sys.argv) > 1 else "customizepkg-patching").resolve(strict=True)
assert os.geteuid() != 0, "run the checks as an ordinary user"
count = 0


def patch(name, before, after):
    return "".join(difflib.unified_diff(
        (before or "").splitlines(keepends=True),
        (after or "").splitlines(keepends=True),
        fromfile="/dev/null" if before is None else json.dumps(f"./{name}", ensure_ascii=False),
        tofile="/dev/null" if after is None else json.dumps(f"./{name}", ensure_ascii=False),
    ))


def snapshot(work):
    result = {}
    for path in work.rglob("*"):
        info = path.lstat()
        payload = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        result[str(path.relative_to(work))] = (info.st_mode, info.st_mtime_ns, payload)
    return result


def setup(root, name, files=None, saved=None, pkg="pkgname=demo\n"):
    base = root / name
    work, config, tmp = (base / part for part in ("work", "config", "tmp"))
    for path in (work, config, tmp):
        path.mkdir(parents=True)
    (work / "PKGBUILD").write_text(pkg)
    for name, content in (files or {}).items():
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if saved is not None:
        (config / "demo").write_text(saved)
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TMPDIR": str(tmp),
           "CUSTOMIZEPKG_DIR": str(config)}
    return work, config, env


def run(work, env, *args, ok=True):
    global count
    proc = subprocess.run(["/usr/bin/bash", str(SCRIPT), *args], cwd=work,
                          env=env, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=15)
    if ok is not None:
        assert (proc.returncode == 0) == ok, (work.parent.name, args, proc.returncode,
                                            proc.stdout, proc.stderr)
    assert not list(Path(env["TMPDIR"]).glob("customizepkg.*")), "private staging leaked"
    count += 1
    return proc


with tempfile.TemporaryDirectory(prefix="customizepkg-check.") as temp:
    root = Path(temp)
    normal = patch("value.txt", "old\n", "new\n")

    work, config, env = setup(root, "preview", {"value.txt": "old\n", "empty": "",
        "unrelated.original": "keep backup\n", "unrelated.rej": "keep reject\n"}, normal)
    before = snapshot(work)
    run(work, env)
    assert snapshot(work) == before

    work, config, env = setup(root, "empty-preview", {"empty": ""}, patch("empty", "", "new\n"))
    before = snapshot(work)
    run(work, env)
    assert snapshot(work) == before and (work / "empty").is_file()

    work, config, env = setup(root, "reject", {"value.txt": "different\n"}, normal)
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    work, config, env = setup(root, "partial-reject", {"value.txt": "old\n", "second": "different\n"},
                             normal + patch("second", "expected\n", "new\n"))
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    work, config, env = setup(root, "apply", {"value.txt": "old\n", "unrelated.original": "keep\n",
        "unrelated.rej": "keep\n"}, normal)
    run(work, env, "--modify")
    assert (work / "value.txt").read_text() == "new\n"
    assert (work / "value.txt.original").read_text() == "old\n"
    assert (work / "unrelated.original").read_text() == "keep\n"
    assert (work / "unrelated.rej").read_text() == "keep\n"
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    for label, old, new in (("empty-apply", "", "new\n"), ("addition", None, "new\n"),
                            ("deletion", "old\n", None), ("truncate", "old\n", "")):
        work, config, env = setup(root, label, {} if old is None else {"value": old}, patch("value", old, new))
        run(work, env, "--modify")
        assert (work / "value.original").read_text() == (old or "")
        if new is None:
            assert not (work / "value").exists()
        else:
            assert (work / "value").read_text() == new

    for label, extra in (("collision", False), ("backup-symlink", True)):
        work, config, env = setup(root, label, {"value.txt": "old\n"}, normal)
        if extra:
            (work / "value.txt.original").symlink_to("value.txt")
        else:
            (work / "value.txt.original").write_text("previous backup\n")
        before = snapshot(work)
        run(work, env, "--modify", ok=False)
        assert snapshot(work) == before

    for name in (".hidden", "-leading", "file with spaces", "quote'and$dollar",
                 "$(touch UNEXPECTED)", "back\\slash", "tab\there"):
        work, config, env = setup(root, "name-" + str(count), {name: "old\n"}, patch(name, "old\n", "new\n"))
        run(work, env, "--modify")
        assert (work / name).read_text() == "new\n"
        assert (work / (name + ".original")).read_text() == "old\n"
        assert not (work / "UNEXPECTED").exists()

    # GNU patch versions differ on embedded newlines: either apply correctly or
    # reject in staging without touching the working files.
    work, config, env = setup(root, "newline-name", {"line\nbreak": "old\n"},
                             patch("line\nbreak", "old\n", "new\n"))
    before = snapshot(work)
    proc = run(work, env, "--modify", ok=None)
    if proc.returncode == 0:
        assert (work / "line\nbreak").read_text() == "new\n"
        assert (work / "line\nbreak.original").read_text() == "old\n"
    else:
        assert snapshot(work) == before

    work, config, env = setup(root, "multi-success", {"value.txt": "old\n", "second": "old\n"},
                             normal + patch("second", "old\n", "new\n"))
    run(work, env, "--modify")
    assert (work / "value.txt").read_text() == (work / "second").read_text() == "new\n"
    work, config, env = setup(root, "multi-collision", {"value.txt": "old\n", "second": "old\n",
                             "second.original": "older\n"}, normal + patch("second", "old\n", "new\n"))
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    work, config, env = setup(root, "split-package", {"value.txt": "old\n"}, normal,
                             "pkgbase=demo\npkgname=(first second)\n")
    run(work, env)
    work, config, env = setup(root, "shell-state", {"value.txt": "old\n"}, normal,
                             "pkgname=demo\nMODIFY=1\npatch() { return 77; }\n")
    before = snapshot(work)
    run(work, env)
    assert snapshot(work) == before

    for label, recipe in (("invalid-name", "pkgname=../../escape\n"), ("no-name", "true\n"),
                           ("recipe-fails", "pkgname=demo\nfalse\n")):
        work, config, env = setup(root, label, {"value.txt": "old\n"}, normal, recipe)
        before = snapshot(work)
        run(work, env, ok=False)
        assert snapshot(work) == before

    work, config, env = setup(root, "unknown-option", pkg="touch SHOULD_NOT_RUN\npkgname=demo\n")
    run(work, env, "--modfiy", ok=False)
    run(work, env, "--edit", "--modify", ok=False)
    run(work, env, "--help")
    run(work, env, "--version")
    assert not (work / "SHOULD_NOT_RUN").exists()

    for label, argument in (("print-no-source", "--patch"), ("edit-no-source", "--edit")):
        work, config, env = setup(root, label, {"value.original": "old\n", "value": "new\n"},
                                 pkg="touch SHOULD_NOT_RUN\npkgname=demo\n")
        env["EDITOR"] = "/usr/bin/true"
        before = snapshot(work)
        run(work, env, argument)
        assert snapshot(work) == before
        if argument == "--edit":
            env["EDITOR"] = "/usr/bin/false"
            run(work, env, argument, ok=False)

    work, config, env = setup(root, "save", {"value.original": "old\n", "value": "new\n"}, "previous\n")
    (config / "demo").chmod(0o640)
    run(work, env, "--patch", "--modify")
    saved = (config / "demo").read_text()
    assert "-old" in saved and "+new" in saved
    assert stat.S_IMODE((config / "demo").stat().st_mode) == 0o640
    assert sorted(p.name for p in config.iterdir()) == ["demo"]
    replay, _, replay_env = setup(root, "saved-roundtrip", {"value": "old\n"}, saved)
    run(replay, replay_env, "--modify")
    assert (replay / "value").read_text() == "new\n"

    work, config, env = setup(root, "save-special", {"file with spaces.original": "old\n",
                             "file with spaces": "new\n"})
    run(work, env, "--patch", "--modify")
    replay, _, replay_env = setup(root, "saved-special-roundtrip", {"file with spaces": "old\n"},
                                 (config / "demo").read_text())
    run(replay, replay_env, "--modify")
    assert (replay / "file with spaces").read_text() == "new\n"

    work, config, env = setup(root, "save-no-changes", {"value.original": "same\n", "value": "same\n"}, "previous\n")
    run(work, env, "--patch", "--modify", ok=False)
    assert (config / "demo").read_text() == "previous\n"
    work, config, env = setup(root, "save-too-large", {"value.original": "old\n",
                             "value": "x" * (4 * 1024 * 1024) + "\n"}, "previous\n")
    run(work, env, "--patch", "--modify", ok=False)
    assert (config / "demo").read_text() == "previous\n"
    work, config, env = setup(root, "save-fails", {"value.original": "old\n", "value": "new\n"}, "previous\n")
    config.chmod(0o500)
    try:
        run(work, env, "--patch", "--modify", ok=False)
        assert (config / "demo").read_text() == "previous\n"
    finally:
        config.chmod(0o700)

    for label, filename, saved in (("nested", "sub/value", patch("sub/value", "old\n", "new\n")),
                                  ("nested-add", "other", patch("sub/new", None, "new\n")),
                                  ("reserved", "value.original", patch("value.original", "old\n", "new\n")),
                                  ("reserved-new", "other", patch(".original", None, "new\n")),
                                  ("traversal", "value", patch("../outside", "old\n", "new\n"))):
        work, config, env = setup(root, label, {filename: "old\n"}, saved)
        (work.parent / "outside").write_text("old\n")
        before = snapshot(work)
        run(work, env, "--modify", ok=False)
        assert snapshot(work) == before
        assert (work.parent / "outside").read_text() == "old\n"

    work, config, env = setup(root, "symlink-target", saved=normal)
    outside = work.parent / "outside"
    outside.write_text("old\n")
    (work / "value.txt").symlink_to(outside)
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before and outside.read_text() == "old\n"

    work, config, env = setup(root, "absolute-target")
    outside = work.parent / "outside"
    outside.write_text("old\n")
    (config / "demo").write_text("".join(difflib.unified_diff(["old\n"], ["new\n"],
                                    fromfile=str(outside), tofile=str(outside))))
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before and outside.read_text() == "old\n"

    work, config, env = setup(root, "hardlink", {"value.txt": "old\n"}, normal)
    outside = work.parent / "outside"
    os.link(work / "value.txt", outside)
    run(work, env, "--modify")
    assert (work / "value.txt").read_text() == "new\n" and outside.read_text() == "old\n"

    work, config, env = setup(root, "directory-target", saved=patch("new", None, "content\n"))
    (work / "new").mkdir()
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    work, config, env = setup(root, "readonly", {"value.txt": "old\n"}, normal)
    (work / "value.txt").chmod(0o444)
    before = snapshot(work)
    run(work, env, "--modify", ok=False)
    assert snapshot(work) == before

    work, config, env = setup(root, "patch-symlink", {"value.txt": "old\n"}, normal)
    (config / "demo").rename(config / "real")
    (config / "demo").symlink_to("real")
    run(work, env, "--modify", ok=False)
    assert (config / "real").read_text() == normal

    work, config, env = setup(root, "apply-failure", {"value.txt": "old\n"}, normal)
    tools = work.parent / "tools"
    tools.mkdir()
    fake = tools / "patch"
    fake.write_text('#!/usr/bin/bash\nif [[ $PWD == */stage ]]; then exec /usr/bin/patch "$@"; fi\nexit 2\n')
    fake.chmod(0o700)
    env["PATH"] = str(tools) + ":/usr/bin:/bin"
    proc = run(work, env, "--modify", ok=False)
    assert "changes may be partial" in proc.stderr
    assert (work / "value.txt").read_text() == "old\n"

    work, config, env = setup(root, "vim-preview", {"value.txt": "old\n"}, normal)
    tools = work.parent / "tools"
    tools.mkdir()
    fake = tools / "vim"
    fake.write_text('#!/usr/bin/bash\nprintf "%s\\n" "$@" > "$TMPDIR/vim-args"\npwd > "$TMPDIR/vim-cwd"\n')
    fake.chmod(0o700)
    env["PATH"] = str(tools) + ":/usr/bin:/bin"
    before = snapshot(work)
    run(work, env, "--vimdiff")
    assert snapshot(work) == before
    assert (Path(env["TMPDIR"]) / "vim-args").read_text().splitlines()[:4] == ["-R", "-n", "-d", "--"]
    assert (Path(env["TMPDIR"]) / "vim-cwd").read_text().strip().endswith("/stage")

    work, config, env = setup(root, "large-input", {"value.txt": "old\n"}, normal)
    with (work / "large").open("wb") as handle:
        handle.truncate(257 * 1024 * 1024)
    run(work, env, ok=False)
    assert (work / "value.txt").read_text() == "old\n"

    work, config, env = setup(root, "file-count", saved=normal)
    for number in range(4096):
        (work / f"file-{number}").touch()
    proc = run(work, env, ok=False)
    assert "staging limit exceeded" in proc.stderr

    for label, saved in (("empty-patch", ""), ("invalid-patch", "this is not a patch\n"),
                          ("missing-patch", None)):
        work, config, env = setup(root, label, {"value.txt": "old\n"}, saved)
        before = snapshot(work)
        run(work, env, "--modify", ok=False)
        assert snapshot(work) == before
    work, config, env = setup(root, "large-patch", {"value.txt": "old\n"}, normal)
    with (config / "demo").open("wb") as handle:
        handle.truncate(4 * 1024 * 1024 + 1)
    run(work, env, ok=False)
    assert (work / "value.txt").read_text() == "old\n"

print(f"{count} offline CLI checks passed; all data was synthetic and disposable.")
