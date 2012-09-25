# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import sys
import argparse
import shutil
import traceback

from subprocess import CalledProcessError, check_call

from . util import check_output

from . util import add_global_arguments
from . util import handle_global_arguments
from . util import bailout, execute_command, ansi, parse_stack_xml
from . util import assert_is_not_gbp_repo, create_temporary_directory
from . util import get_versions_from_upstream_tag, segment_version
from . git import branch_exists
from . git import get_current_branch
from . git import get_last_tag_by_date
from . git import get_root
from . git import track_branches

from . logging import debug
from . logging import error
from . logging import info
from . logging import log_prefix
from . logging import warning

from distutils.version import StrictVersion

try:
    from vcstools import VcsClient
except ImportError:
    error("vcstools was not detected, please install it.", file=sys.stderr)
    sys.exit(1)


def convert_catkin_to_bloom(cwd=None):
    """
    Converts an old style catkin branch/catkin.conf setup to bloom.
    """
    # Rename the branch to bloom from catkin
    execute_command('git branch -m catkin bloom', cwd=cwd)
    # Change to the bloom branch
    execute_command('git checkout bloom', cwd=cwd)
    # Rename the config cwd
    if os.path.exists(os.path.join(cwd, 'catkin.conf')):
        execute_command('git mv catkin.conf bloom.conf', cwd=cwd)
    # Replace the `[catkin]` entry in the config file with `[bloom]`
    bloom_path = os.path.join(cwd, 'bloom.conf')
    if os.path.exists(bloom_path):
        conf_file = open(bloom_path, 'r').read()
        conf_file = conf_file.replace('[catkin]', '[bloom]')
        open(bloom_path, 'w+').write(conf_file)
        # Stage the config file changes
        execute_command('git add bloom.conf', cwd=cwd)
        # Commit the change
        cmd = 'git commit -m "rename catkin.conf to bloom.conf"'
        execute_command(cmd, cwd=cwd)


def not_a_bloom_release_repo():
    bailout("This does not appear to be a bloom release repo. "
            "Please initialize it first using: git "
            "bloom-set-upstream <UPSTREAM_VCS_URL> <VCS_TYPE> [<VCS_BRANCH>]")


def check_for_bloom(cwd=None):
    """
    Checks for the bloom branch, else looks for and converts the catkin branch.
    Then it checks for the bloom branch and that it contains a bloom.conf file.
    """
    branches = check_output('git branch', shell=True, cwd=cwd)
    if branches.count('bloom') == 0:
        # There is not bloom branch, check for the legacy catkin branch
        if branches.count('catkin') == 0:
            # Neither was found
            not_a_bloom_release_repo()
        else:
            # Found catkin branch, migrate it to bloom
            info('catkin branch detected, up converting to the bloom branch')
            convert_catkin_to_bloom(cwd)
    # Check for bloom.conf
    try:
        execute_command('git checkout bloom', cwd=cwd)
    except CalledProcessError:
        not_a_bloom_release_repo()
    loc = os.path.join(cwd, 'bloom.conf') if cwd is not None else 'bloom.conf'
    if not os.path.exists(loc):
        # The repository has not been bloom initialized
        not_a_bloom_release_repo()


def parse_bloom_conf(cwd=None):
    """
    Parses the bloom.conf file in the current directory and returns info in it.
    """
    cmd = 'git config -f bloom.conf bloom.upstream'
    upstream_repo = check_output(cmd, shell=True, cwd=cwd).strip()
    cmd = 'git config -f bloom.conf bloom.upstreamtype'
    upstream_type = check_output(cmd, shell=True, cwd=cwd).strip()
    try:
        cmd = 'git config -f bloom.conf bloom.upstreambranch'
        upstream_branch = check_output(cmd, shell=True, cwd=cwd).strip()
    except CalledProcessError:
        upstream_branch = ''
    return upstream_repo, upstream_type, upstream_branch


def create_initial_upstream_branch(cwd=None):
    """
    Creates an empty, initial upstream branch in the given git repository.
    """
    execute_command('git symbolic-ref HEAD refs/heads/upstream', cwd=cwd)
    execute_command('rm -f .git/index', cwd=cwd)
    execute_command('git clean -dfx', cwd=cwd)
    execute_command('git commit --allow-empty -m "Initial upstream branch"',
                    cwd=cwd)


def detect_git_import_orig():
    """
    Returns True if git-import-orig is in the path, False otherwise
    """
    from subprocess import PIPE
    try:
        check_call('git-import-orig --help', shell=True, stdout=PIPE,
                   stderr=PIPE)
        return True
    except (OSError, CalledProcessError):
        return False
    return False


def summarize_repo_info(upstream_repo, upstream_type, upstream_branch):
    msg = 'upstream repo: ' + ansi('boldon') + upstream_repo \
        + ansi('reset')
    info(msg)
    msg = 'upstream type: ' + ansi('boldon') + upstream_type \
        + ansi('reset')
    info(msg)
    upstream_branch = upstream_branch if upstream_branch else '(No branch set)'
    msg = 'upstream branch: ' + ansi('boldon') + upstream_branch \
        + ansi('reset')
    info(msg)


def get_upstream_meta(upstream_dir):
    meta = None
    # Check for stack.xml
    stack_path = os.path.join(upstream_dir, 'stack.xml')
    info("Checking for package.xml(s)")
    # Check for package.xml(s)
    try:
        from catkin_pkg.packages import find_packages
        from catkin_pkg.packages import verify_equal_package_versions
    except ImportError:
        error("catkin_pkg was not detected, please install it.",
              file=sys.stderr)
        sys.exit(1)
    packages = find_packages(basepath=upstream_dir)
    if packages == {}:
        info("package.xml(s) not found, looking for stack.xml")
        if os.path.exists(stack_path):
            info("stack.xml found")
            # Assumes you are at the top of the repo
            stack = parse_stack_xml(stack_path)
            meta = {}
            meta['name'] = [stack.name]
            meta['version'] = stack.version
            meta['type'] = 'stack.xml'
        else:
            bailout("Neither stack.xml, nor package.xml(s) were detected.")
    else:
        info("package.xml(s) found")
        try:
            version = verify_equal_package_versions(packages.values())
        except RuntimeError as err:
            traceback.print_exec()
            bailout("Releasing multiple packages with different versions is "
                    "not supported: " + str(err))
        meta = {}
        meta['version'] = version
        meta['name'] = [p.name for p in packages.values()]
        meta['type'] = 'package.xml'
    return meta


@log_prefix('[git-bloom-import-upstream]: ')
def import_upstream(cwd, tmp_dir, args):
    # Ensure the bloom and upstream branches are tracked locally
    track_branches(['bloom', 'upstream'])

    # Create a clone of the bloom_repo to help isolate the activity
    bloom_repo_clone_dir = os.path.join(tmp_dir, 'bloom_clone')
    os.makedirs(bloom_repo_clone_dir)
    os.chdir(bloom_repo_clone_dir)
    bloom_repo = VcsClient('git', bloom_repo_clone_dir)
    bloom_repo.checkout('file://{0}'.format(cwd))

    # Ensure the bloom and upstream branches are tracked from the original
    track_branches(['bloom', 'upstream'])

    # Check for a bloom branch
    check_for_bloom(os.getcwd())

    # Parse the bloom config file
    upstream_repo, upstream_type, upstream_branch = parse_bloom_conf()

    # Summarize the config contents
    summarize_repo_info(upstream_repo, upstream_type, upstream_branch)

    # If the upstream repo is git, then assert some things about the repo
    if upstream_type == 'git':
        info("Verifying a couple of things about the upstream git repo...")
        # Ensure the upstream repo is not setup as a gbp
        assert_is_not_gbp_repo(upstream_repo)

    # Checkout upstream
    upstream_dir = os.path.join(tmp_dir, 'upstream')
    upstream_client = VcsClient(upstream_type, upstream_dir)
    if args.upstream_branch != None:
        ver = args.upstream_branch
        warning("Overriding the bloom.conf branch with {0}".format(ver))
    else:
        ver = upstream_branch if upstream_branch != '(No branch set)' else ''

    checkout_url = upstream_repo
    checkout_ver = ver

    # Handle svn
    if upstream_type == 'svn':
        if ver == '':
            checkout_url = upstream_repo + '/trunk'
        else:
            checkout_url = upstream_repo + '/branches/' + ver
        checkout_ver = ''
        debug("Checking out from url {0}".format(checkout_url))
    else:
        debug("Checking out branch "
          "({0}) from url {1}".format(checkout_ver, checkout_url))

    # XXX TODO: Need to validate if ver is valid for the upstream repo...
    # see: https://github.com/vcstools/vcstools/issues/4
    if not upstream_client.checkout(checkout_url, checkout_ver):
        if upstream_type == 'svn':
            error(
                "Could not checkout upstream repostiory "
                "({0})".format(checkout_url)
            )
        else:
            error(
                "Could not checkout upstream repostiory "
                "({0})".format(checkout_url)
              + " to branch ({0})".format(ver)
            )
        return 1

    # Get upstream meta data
    meta = get_upstream_meta(upstream_dir)
    if meta is None or None in meta.values():
        print(meta)
        bailout("Failed to get the upstream meta data.")

    # Summarize the stack.xml contents
    info("Upstream has version " + ansi('boldon')
        + meta['version'] + ansi('reset'))
    if meta['type'] == 'stack.xml':
        info("Upstream contains a stack called " + ansi('boldon')
           + meta['name'][0] + ansi('reset'))
    else:
        info("Upstream contains package" \
           + ('s: ' if len(meta['name']) > 1 else ': ') \
           + ', '.join(meta['name']))

    # For convenience
    name = meta['name'][0] if type(meta['name']) == list else meta['name']
    version = meta['version']

    # Export the repository to a tar ball
    tarball_prefix = 'upstream-' + str(version)
    info('Exporting version {0}'.format(version))
    tarball_path = os.path.join(tmp_dir, tarball_prefix)
    # Change upstream_client for svn
    export_version = version
    if upstream_type == 'svn':
        upstream_client = VcsClient('svn', os.path.join(tmp_dir, 'svn_tag'))
        checkout_url = upstream_repo + '/tags/' + version
        if not upstream_client.checkout(checkout_url):
            warning("Didn't find the tagged version at " + checkout_url)
            checkout_url = upstream_repo + '/tags/' + name + '-' + version
            warning("Trying " + checkout_url)
            if not upstream_client.checkout(checkout_url):
                error("Could not checkout upstream version")
                return 1
        export_version = ''
    if not upstream_client.export_repository(export_version, tarball_path):
        error("Failed to export upstream repository.")
        return 1

    # Get the gbp version elements from either the last tag or the default
    last_tag = get_last_tag_by_date()
    if last_tag == '':
        gbp_major, gbp_minor, gbp_patch = segment_version(version)
    else:
        gbp_major, gbp_minor, gbp_patch = \
            get_versions_from_upstream_tag(last_tag)
        info("The latest upstream tag in the release repository is "
              + ansi('boldon') + last_tag + ansi('reset'))
        # Ensure the new version is greater than the last tag
        full_version_strict = StrictVersion(version)
        last_tag_version = '.'.join([gbp_major, gbp_minor, gbp_patch])
        last_tag_version_strict = StrictVersion(last_tag_version)
        if full_version_strict < last_tag_version_strict:
            warning("""\
Version discrepancy:
The upstream version, {0}, should be greater than the previous \
release version, {1}.

Upstream should re-release or you should fix the release repository.\
""".format(version, last_tag_version))
        if full_version_strict == last_tag_version_strict:
            if args.replace:
                # Remove the conflicting tag first
                warning("""\
Version discrepancy:
The upstream version, {0}, is equal to a previous import version. \
Removing conflicting tag before continuing because the '--replace' \
options was specified.\
""".format(version))
                execute_command('git tag -d {0}'.format(last_tag))
                execute_command('git push origin :refs/tags/'
                                '{0}'.format(last_tag))
            else:
                warning("""\
Version discrepancy:
The upstream version, {0}, is equal to a previous import version. \
git-buildpackage will fail, if you want to replace the existing \
upstream import use the '--replace' option.\
""".format(version))

    # Look for upstream branch
    output = check_output('git branch', shell=True)
    if output.count('upstream') == 0:
        info(ansi('boldon') + "No upstream branch" + ansi('reset') \
            + "... creating an initial upstream branch.")
        create_initial_upstream_branch()

    # Go to the master branch
    bloom_repo.update('master')

    # Detect if git-import-orig is installed
    if not detect_git_import_orig():
        bailout("git-import-orig not detected, did you install "
                "git-buildpackage?")

    # Import the tarball
    cmd = 'git import-orig {0}'.format(tarball_path + '.tar.gz')
    if not args.interactive:
        cmd += ' --no-interactive'
    if not args.merge:
        cmd += ' --no-merge'
    try:
        if check_call(cmd, shell=True) != 0:
            bailout("git-import-orig failed '{0}'".format(cmd))
    except CalledProcessError:
        bailout("git-import-orig failed '{0}'".format(cmd))

    # Push changes back to the original bloom repo
    execute_command('git push --all -f')
    execute_command('git push --tags')


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Imports the upstream repository specified by bloom using git-buildpackage's \
git-import-orig function. This should be run in a git-buildpackage repository \
which has had its upstream repository set using git-bloom-set-upstream.\
""")
    parser.add_argument('-i', '--interactive', help="""\
Allows git-import-orig to be run interactively, otherwise questions \
are prevented by passing the '--non-interactive' flag.\
""",
                        action="store_true")
    parser.add_argument('-r', '--replace', help="""\
Replaces an existing upstream import if the git-buildpackage repository \
already has the upstream version being released.\
""",
                        action="store_true")
    parser.add_argument('-b', '--upstream-branch', help="""\
This specifies an upstream branch to use for the import, but if this is \
not specified then the branch is used.\
""")
    parser.add_argument('-m', '--merge', help="""\
Asks git-import-orig to merge the resulting import into the master branch. \
This is disabled by defualt. This will cause an editor to open for sign-off \
of the merge.
""",
                        action="store_true")
    return parser


def main(sysargs=None):
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Check that the current directory is a serviceable git/bloom repo
    if get_root == None:
        error("This command has to be run in a git repository.")
        parser.print_usage()
        return 1

    # Get the current git branch
    current_branch = get_current_branch()

    if current_branch == 'upstream':
        error("You cannot run git-bloom-import-upstream while in the "
              "upstream branch, because this branch is going to be modified.")
        return 1

    # Create a working temp directory
    tmp_dir = create_temporary_directory()

    cwd = os.getcwd()

    try:
        retcode = import_upstream(cwd, tmp_dir, args)

        # Done!
        if retcode is None or retcode == 0:
            info("I'm happy.  You should be too.")

        return retcode
    finally:
        # Change back to the original cwd
        os.chdir(cwd)
        # Clean up
        shutil.rmtree(tmp_dir)
        if current_branch and branch_exists(current_branch, True, cwd):
            execute_command('git checkout ' + current_branch, cwd)
