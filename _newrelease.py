#!/usr/bin/env python

import os
import sys
import re
import subprocess
import datetime
import logging
import argparse

LOGLEVEL_EVERYTHING = 1
HISTORY_FILE = os.environ.get('HISTORY_FILE', 'HISTORY.rst')
HISTORY_TAG = os.environ.get('HISTORY_TAG', r'(\nRelease History\n-+\n)')
VERSION_TAG = os.environ.get(
    'VERSION_TAG', r'''(\n(?:__)?version(?:__)? = ['"])(?P<version>[0-9.]+)(['"] *(?:#.*)?\n)''')
SETUP_VERSION_TAG = os.environ.get('SETUP_VERSION_TAG', VERSION_TAG)
VERSION_FILE = os.environ.get('VERSION_FILE', 'pyaux/__init__.py')


_log = logging.getLogger('_newrelease.py')


def make_parser():
    parser = argparse.ArgumentParser(
        description="Automatically prepare a new pypi release from git / github")
    parser.add_argument(
        '-v', '--verbose',
        dest='verbosity',
        action='count', default=0,
        help="Verbosity level; specify multiple times to increase verbosity")
    parser.add_argument(
        '--major',
        dest='major', action='store_true',
        help="Make a major release")
    parser.add_argument(
        '--patch',
        dest='patch', action='store_true',
        help="Make a patch release (third number)")
    parser.add_argument(
        '--allow-unclean',
        dest='allow_unclean', action='store_true',
        help="Ignore reposotory taint")
    return parser


def run_sh(command, *args):
    full_command = (command,) + args
    _log.debug("full_command: %r", full_command)
    process = subprocess.Popen(
        full_command,
        shell=False, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    _log.debug("Return code: %r", process.returncode)
    assert process.returncode == 0
    return stdout


def _inc_ver_val(val):
    # NOTE: strips non-digit part of the version
    val_digits = re.search('^([0-9]+)', str(val)).group(1)
    return str(int(val_digits) + 1)


def _inc_ver(parts, num):
    """ Increment `num`th part of the version.

    >>> ver_parts = ['1', '2', '3hotfix1']
    >>> _inc_ver(ver_parts, 0)
    ['2', '0', '0']
    >>> _inc_ver(ver_parts, 1)
    ['1', '3', '0']
    >>> _inc_ver(ver_parts, 2)  # non-digit part is stripped
    ['1', '2', '4']
    """
    return (parts[:num] +
            [_inc_ver_val(parts[num])] +
            ['0'] * (len(parts) - 1 - num))


def update_version_in_text(text, new_version, current_version=None):
    match = re.search(VERSION_TAG, text)
    if match is None:
        raise ValueError("Version not found in file %r" % (filename,))

    pre_tag, current_actual_ver, post_tag = match.groups()
    if current_version is not None:
        if current_version != current_actual_ver:
            _log.error("Found version %r does not match expected %r",
                       current_actual_ver, current_version)

    # pre and post tag parts are supposed to contain the quotes
    new_tag = '%s%s%s' % (pre_tag, new_version, post_tag)
    new_text = '%s%s%s' % (
        text[:match.start()],
        new_tag,
        text[match.end():])
    return new_text


def update_version_in_file(filename, new_version, **kwa):
    with open(filename) as fo:
        text = fo.read()

    new_text = update_version_in_text(text, new_version, **kwa)
    with open(filename, 'w') as fo:
        fo.write(new_text)

    return new_text


def main(args=None):
    parser = make_parser()
    params = parser.parse_args(args)

    _log_levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGLEVEL_EVERYTHING,
    }
    logging.basicConfig(level=_log_levels[min(params.verbosity, 3)])

    if not params.allow_unclean:
        taint = run_sh('git', 'clean', '-d', '-x', '-n')
        if taint.strip():
            _log.critical("Cannot proceed as git repo is not clean:\n%r", taint)
            return 13
        mods = run_sh('git', 'status', '--porcelain')
        if mods.strip():
            _log.critical("Cannot proceed as git repo has modifications:\n%r", mods)
            return 14

    with open(HISTORY_FILE) as fo:
        history = fo.read()

    history_tag = HISTORY_TAG
    history_parts = re.split(history_tag, history, flags=re.MULTILINE)
    _log.debug("History parts: %r", [val[:10] for val in history_parts])
    history_versions = history_parts[-1]

    current_version_match = re.search(
        # 3 dot-separated numbers or more, ISO datestamp or more
        r'^([0-9]+\.[0-9]+\.[0-9]+[^ ]*) \([0-9]{4}-[0-9]{2}-[0-9]{2}[^)]*\).*',
        history_versions, re.MULTILINE)
    current_version = current_version_match.group(1)
    today = datetime.date.today().isoformat()
    version_parts = current_version.split('.')

    new_version = os.environ.get('NEW_VERSION')
    if not new_version:
        if params.major:
            version_parts = _inc_ver(version_parts, 0)
        elif params.patch:
            version_parts = _inc_ver(version_parts, 2)
        else:
            version_parts = _inc_ver(version_parts, 1)

        new_version = '.'.join(version_parts)

    _log.debug("New version: %s", new_version)

    git_history = run_sh(
        "git", "log", "%s..HEAD" % (current_version,),
        "--format=format: - %s")
    _log.debug("Git history: %r", git_history)

    new_history_header = "%s (%s)" % (new_version, today)
    new_history_header_full = "%s\n%s" % (
        new_history_header,
        '+' * len(new_history_header))
    new_history_versions = "\n%s\n\n%s\n\n%s" % (
        new_history_header_full,
        git_history,
        history_versions)
    new_history_full = ''.join(
        history_parts[:-1] +
        [new_history_versions])
    _log.log(LOGLEVEL_EVERYTHING, "New history: \n%s", new_history_full)

    with open(HISTORY_FILE, 'w') as fo:
        fo.write(new_history_full)

    try:
        update_version_in_file('setup.py', new_version,
                               current_version=current_version)
        update_version_in_file(VERSION_FILE, new_version,
                               current_version=current_version)
    except ValueError as exc:
        _log.critical("Error updating version: %r", exc)
        return 2

    raise Exception("TODO")


if __name__ == '__main__':
    sys.exit(main())
