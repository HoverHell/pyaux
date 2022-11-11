#!/usr/bin/env python
from __future__ import annotations

import argparse
import datetime
import glob
import logging
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

LOGLEVEL_EVERYTHING = 1
HISTORY_FILE = os.environ.get("HISTORY_FILE", "HISTORY.rst")
HISTORY_TAG = os.environ.get("HISTORY_TAG", r"(\nRelease History\n-+\n)")

# Note: this is similar to what `bumpversion` does.
HISTORY_VERSION_TAG = os.environ.get(
    "HISTORY_VERSION_TAG",
    # 3 dot-separated numbers or more, ISO datestamp or more
    r"^([0-9]+\.[0-9]+\.[0-9]+[^ ]*) \([0-9]{4}-[0-9]{2}-[0-9]{2}[^)]*\).*",
)
VERSION_TAG = os.environ.get(
    "VERSION_TAG",
    # Includes 3 groups, the second one should be the current version
    # ans is to be replaced with the new version; without quotes.
    r"""(\n(?:__)?version(?:__)? = ['"])(?P<version>[0-9a-zA-Z.+-]+)(['"] *(?:#.*)?\n)""",
)
VERSION_FILES = os.environ.get("VERSION_FILES", "src/*/__init__.py")
VERSION_TAG_TPL = os.environ.get("VERSION_TAG_TPL", "%(version)s")

RELEASE_COMMIT_TPL = os.environ.get("RELEASE_COMMIT_TPL", "Release %(version)s")


LOGGER = logging.getLogger("_newrelease.py")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automatically prepare a new pypi release from git"
    )

    parser.add_argument(
        "cmd",
        choices=("prepare", "check", "finalize"),
        nargs="?",
        default="prepare",
        help=(
            "Action to perform; usual workflow is 'prepare',"
            " check `git status`, 'check', then 'finalize'."
        ),
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=0,
        help="Verbosity level; specify multiple times to increase verbosity",
    )

    parser.add_argument(
        "--major",
        dest="major",
        action="store_true",
        help="Make a major release (in `prepare`)",
    )
    parser.add_argument(
        "--patch",
        dest="patch",
        action="store_true",
        help="Make a patch release (third number) (in `prepare`)",
    )
    parser.add_argument(
        "--allow-unclean",
        dest="allow_unclean",
        action="store_true",
        help="Ignore reposotory taint (in `prepare`)",
    )
    parser.add_argument(
        "--no-commit",
        dest="no_commit",
        action="store_true",
        help="Do not commit changes (in `finalize`)",
    )

    return parser


def run_sh(*full_command: str) -> str:
    LOGGER.info("Running command: %r", full_command)
    process = subprocess.Popen(
        full_command, stdin=subprocess.PIPE, shell=False, stdout=subprocess.PIPE
    )
    stdout, _ = process.communicate()
    LOGGER.debug("Return code: %r", process.returncode)
    assert process.returncode == 0
    return stdout.decode()


def run_sh_cmd(cmd: str, **kwa: Any) -> str:
    full_command = shlex.split(cmd)
    return run_sh(*full_command, **kwa)


def _inc_ver_val(val: str) -> str:
    # NOTE: strips non-digit part of the version
    rex = r"^([0-9]+)"
    val_digits_match = re.search(rex, str(val))
    if not val_digits_match:
        raise ValueError(f"Value {val!r} did not match regex {rex!r}.")
    val_digits = val_digits_match.group(1)
    return str(int(val_digits) + 1)


def _inc_ver(parts: Sequence[str], num: int) -> list[str]:
    """Increment `num`th part of the version.

    >>> ver_parts = ['1', '2', '3hotfix1']
    >>> _inc_ver(ver_parts, 0)
    ['2', '0', '0']
    >>> _inc_ver(ver_parts, 1)
    ['1', '3', '0']
    >>> _inc_ver(ver_parts, 2)  # non-digit part is stripped
    ['1', '2', '4']
    """
    return [
        *parts[:num],
        _inc_ver_val(parts[num]),
        *(["0"] * (len(parts) - 1 - num)),
    ]


def update_version_in_text(text: str, new_version: str, current_version: str | None = None) -> str:
    match = re.search(VERSION_TAG, text)
    if match is None:
        raise ValueError("Version not found", text)

    pre_tag, current_actual_ver, post_tag = match.groups()
    if current_version is not None:
        if current_version != current_actual_ver:
            LOGGER.error(
                "Found version %r does not match expected %r",
                current_actual_ver,
                current_version,
            )

    # pre and post tag parts are supposed to contain the quotes
    new_tag = f"{pre_tag}{new_version}{post_tag}"
    new_text = f"{text[: match.start()]}{new_tag}{text[match.end() :]}"
    return new_text


def update_version_in_file(filename: str, new_version: str, **kwa: Any) -> str:
    with open(filename) as fo:
        text = fo.read()

    try:
        new_text = update_version_in_text(text, new_version, **kwa)
    except ValueError:
        # Re-raise with filename instead of the text
        raise ValueError(f"Version not found in file {filename!r}")

    with open(filename, "w") as fo:
        fo.write(new_text)

    return new_text


def get_current_version(text: str | None = None) -> str:
    """
    Obtain the current actual version from `pyproject.toml`

    Mainly intended for `finalize`.
    """
    filename = next(iter(glob.glob(VERSION_FILES)))
    if text is None:
        with open(filename) as fo:
            text = fo.read()

    match = re.search(VERSION_TAG, text)
    if not match:
        raise ValueError(f"Could not find version in {filename} with regex {VERSION_TAG!r}.")

    return match.group("version")


def get_git_mods() -> str:
    return run_sh_cmd("git status --porcelain")


def get_git_taint() -> str:
    return run_sh_cmd("git clean -d -x -n")


def prepare(params: argparse.Namespace) -> int:
    if not params.allow_unclean:
        mods = get_git_mods()
        if mods.strip():
            LOGGER.critical("Cannot proceed as git repo has modifications:\n%r", mods)
            return 14
        taint = get_git_taint()
        if taint.strip():
            LOGGER.critical("Cannot proceed as git repo is not clean:\n%r", taint)
            return 13

    with open(HISTORY_FILE) as fo:
        history = fo.read()

    history_tag = HISTORY_TAG
    history_parts = re.split(history_tag, history, flags=re.MULTILINE)
    LOGGER.debug("History parts: %r", [val[:10] for val in history_parts])
    history_versions = history_parts[-1]

    current_version_match = re.search(HISTORY_VERSION_TAG, history_versions, re.MULTILINE)
    if not current_version_match:
        raise ValueError(f"History did not have a regex match for {HISTORY_VERSION_TAG!r}")
    current_version = current_version_match.group(1)
    today = datetime.date.today().isoformat()
    version_parts = current_version.split(".")

    new_version = os.environ.get("NEW_VERSION")
    if not new_version:
        if params.major:
            version_parts = _inc_ver(version_parts, 0)
        elif params.patch:
            version_parts = _inc_ver(version_parts, 2)
        else:
            version_parts = _inc_ver(version_parts, 1)

        new_version = ".".join(version_parts)

    LOGGER.debug("New version: %s", new_version)

    version_tag = VERSION_TAG_TPL % dict(version=current_version)
    git_history = run_sh("git", "log", f"{version_tag}..HEAD", "--format=format: - %s")
    if isinstance(git_history, bytes):
        git_history = git_history.decode("utf-8", errors="replace")
    LOGGER.debug("Git history: %r", git_history)

    new_history_header = f"{new_version} ({today})"
    new_history_header_full = "{}\n{}".format(
        new_history_header,
        "+" * len(new_history_header),
    )
    new_history_versions = "\n{}\n\n{}\n\n{}".format(
        new_history_header_full,
        git_history,
        history_versions,
    )
    new_history_full = "".join(history_parts[:-1] + [new_history_versions])
    LOGGER.log(LOGLEVEL_EVERYTHING, "New history: \n%s", new_history_full)

    with open(HISTORY_FILE, "w") as fo:
        fo.write(new_history_full)

    try:
        for filename in glob.glob(VERSION_FILES):
            update_version_in_file(filename, new_version, current_version=current_version)
    except ValueError as exc:
        LOGGER.critical("Error updating version: %r", exc)
        return 2

    LOGGER.info("Done")
    return 0


def check(params: argparse.Namespace) -> None:
    run_sh_cmd("pip install -e .")
    run_sh_cmd("tox -e py310")
    if os.path.exists("test.sh"):
        run_sh("./test.sh")


def finalize(params: argparse.Namespace) -> int:
    try:
        version = get_current_version()
    except ValueError as exc:
        LOGGER.critical("Error getting current version: %r", exc)
        return 2

    LOGGER.info("Found current version: %r", version)

    if not params.no_commit:
        mods = get_git_mods()
        if not mods.strip():
            LOGGER.critical(
                "Finalize should be called after `prepare` made the"
                " changes and while they are not committed yet; alas, no"
                " changes are found by git"
            )
            return 4

    taint = get_git_taint()
    if taint.strip():
        LOGGER.critical(
            (
                "There are git-untracked files which should not exist;"
                " please run `git clean -d -x -f` to remove them before"
                " using `finalize`:\n%s"
            ),
            taint,
        )
        return 5

    tpl_env = dict(version=version)

    release_msg = RELEASE_COMMIT_TPL % tpl_env
    if not params.no_commit:
        run_sh("git", "commit", "-a", "-m", release_msg)

    version_tag = VERSION_TAG_TPL % tpl_env
    run_sh("git", "tag", "-a", version_tag, "-m", release_msg)
    run_sh_cmd("git push")
    run_sh_cmd("git push --tags")

    run_sh_cmd("python -m build")
    run_sh_cmd("twine upload ./dist/*")

    LOGGER.debug("Done.")
    return 0


def main(args: Sequence[str] | None = None) -> int:
    parser = make_parser()
    params = parser.parse_args(args)

    _log_levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGLEVEL_EVERYTHING,
    }
    logging.basicConfig(level=_log_levels[min(params.verbosity, 3)])

    if params.cmd == "prepare":
        return prepare(params)
    if params.cmd == "finalize":
        return finalize(params)
    return 1


if __name__ == "__main__":
    sys.exit(main())
