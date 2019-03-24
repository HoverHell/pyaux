#!/usr/bin/env python

import os
import sys
import re
import subprocess
import datetime
import logging
import argparse
import shlex
import glob

LOGLEVEL_EVERYTHING = 1
HISTORY_FILE = os.environ.get('HISTORY_FILE', 'HISTORY.rst')
HISTORY_TAG = os.environ.get('HISTORY_TAG', r'(\nRelease History\n-+\n)')

# Note: this is similar to what `bumpversion` does.
HISTORY_VERSION_TAG = os.environ.get(
    'HISTORY_VERSION_TAG',
    # 3 dot-separated numbers or more, ISO datestamp or more
    r'^([0-9]+\.[0-9]+\.[0-9]+[^ ]*) \([0-9]{4}-[0-9]{2}-[0-9]{2}[^)]*\).*')
VERSION_TAG = os.environ.get(
    'VERSION_TAG',
    # Includes 3 groups, the second one should be the current version
    # ans is to be replaced with the new version; without quotes.
    r'''(\n(?:__)?version(?:__)? = ['"])(?P<version>[0-9a-zA-Z.+-]+)(['"] *(?:#.*)?\n)''')
SETUP_VERSION_TAG = os.environ.get('SETUP_VERSION_TAG', VERSION_TAG)
VERSION_FILES = os.environ.get('VERSION_FILES', '*/__init__.py')
VERSION_TAG_TPL = os.environ.get('VERSION_TAG_TPL', '%(version)s')

RELEASE_COMMIT_TPL = os.environ.get('RELEASE_COMMIT_TPL', 'Release %(version)s')


_log = logging.getLogger('_newrelease.py')


def make_parser():
    parser = argparse.ArgumentParser(
        description="Automatically prepare a new pypi release from git")

    parser.add_argument(
        'cmd',
        choices=('prepare', 'check', 'finalise'),
        nargs='?', default='prepare',
        help=(u"Action to perform; usual workflow is 'prepare',"
              u" check `git status`, 'check', then 'finalise'."))

    parser.add_argument(
        '-v', '--verbose',
        dest='verbosity',
        action='count', default=0,
        help="Verbosity level; specify multiple times to increase verbosity")

    parser.add_argument(
        '--major',
        dest='major', action='store_true',
        help="Make a major release (in `prepare`)")
    parser.add_argument(
        '--patch',
        dest='patch', action='store_true',
        help="Make a patch release (third number) (in `prepare`)")
    parser.add_argument(
        '--allow-unclean',
        dest='allow_unclean', action='store_true',
        help="Ignore reposotory taint (in `prepare`)")
    parser.add_argument(
        '--no-commit',
        dest='no_commit', action='store_true',
        help="Do not commit changes (in `finalise`)")

    return parser


def run_sh(*full_command):
    _log.info("Running command: %r", full_command)
    process = subprocess.Popen(
        full_command,
        stdin=subprocess.PIPE,
        shell=False, stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    _log.debug("Return code: %r", process.returncode)
    assert process.returncode == 0
    return stdout


def run_sh_cmd(cmd, **kwa):
    full_command = shlex.split(cmd)
    return run_sh(*full_command, **kwa)


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
        raise ValueError("Version not found", text)

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

    try:
        new_text = update_version_in_text(text, new_version, **kwa)
    except ValueError:
        # Re-raise with filename instead of the text
        raise ValueError("Version not found in file %r" % (filename,))

    with open(filename, 'w') as fo:
        fo.write(new_text)

    return new_text


def get_current_version(text=None):
    """ Obtain the current actual version from setup.py.

    Mainly intended for `finalise`.
    """
    if text is None:
        with open('setup.py') as fo:
            text = fo.read()

    match = re.search(VERSION_TAG, text)
    if not match:
        raise ValueError("Could not find version in setup.py")

    return match.group(2)


def get_git_mods():
    return run_sh_cmd('git status --porcelain')


def get_git_taint():
    return run_sh_cmd('git clean -d -x -n')


def prepare(params):
    if not params.allow_unclean:
        mods = get_git_mods()
        if mods.strip():
            _log.critical("Cannot proceed as git repo has modifications:\n%r", mods)
            return 14
        taint = get_git_taint()
        if taint.strip():
            _log.critical("Cannot proceed as git repo is not clean:\n%r", taint)
            return 13

    with open(HISTORY_FILE) as fo:
        history = fo.read()

    history_tag = HISTORY_TAG
    history_parts = re.split(history_tag, history, flags=re.MULTILINE)
    _log.debug("History parts: %r", [val[:10] for val in history_parts])
    history_versions = history_parts[-1]

    current_version_match = re.search(
        HISTORY_VERSION_TAG,
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

    version_tag = VERSION_TAG_TPL % dict(version=current_version)
    git_history = run_sh(
        "git", "log", "%s..HEAD" % (version_tag,),
        "--format=format: - %s")
    if isinstance(git_history, bytes):
        git_history = git_history.decode('utf-8', errors='replace')
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
        for filename in glob.glob(VERSION_FILES):
            update_version_in_file(filename, new_version,
                                   current_version=current_version)
    except ValueError as exc:
        _log.critical("Error updating version: %r", exc)
        return 2

    _log.info("Done")


def check(params):
    run_sh_cmd('python setup.py develop')
    run_sh_cmd('python setup.py test')
    if os.path.exists('test.sh'):
        run_sh('./test.sh')


def finalise(params):
    try:
        version = get_current_version()
    except ValueError as exc:
        _log.critical("Error getting current version: %r", exc)
        return 2

    _log.info("Found current version: %r", version)

    if not params.no_commit:
        mods = get_git_mods()
        if not mods.strip():
            _log.critical((
                "Finalise should be called after `prepare` made the"
                " changes and while they are not committed yet; alas, no"
                " changes are found by git"))
            return 4

    taint = get_git_taint()
    if taint.strip():
        _log.critical((
            "There are git-untracked files which should not exist;"
            " please run `git clean -d -x -f` to remove them before"
            " using `finalise`:\n%s"), taint)
        return 5

    tpl_env = dict(version=version)

    release_msg = RELEASE_COMMIT_TPL % tpl_env
    if not params.no_commit:
        run_sh('git', 'commit', '-a', '-m', release_msg)

    version_tag = VERSION_TAG_TPL % tpl_env
    run_sh('git', 'tag', '-a', version_tag, '-m', release_msg)
    run_sh_cmd('git push')
    run_sh_cmd('git push --tags')

    run_sh_cmd('python setup.py sdist')
    run_sh_cmd('python setup.py bdist_wheel')
    run_sh_cmd('twine upload ./dist/*')

    _log.debug("Done.")


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

    if params.cmd == 'prepare':
        return prepare(params)
    elif params.cmd == 'finalise':
        return finalise(params)


if __name__ == '__main__':
    sys.exit(main())
