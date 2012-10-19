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

from subprocess import CalledProcessError

from pkg_resources import parse_version

from bloom import gbp

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import create_branch
from bloom.git import ensure_clean_working_env
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import get_last_tag_by_date
from bloom.git import inbranch
from bloom.git import show
from bloom.git import track_branches

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import check_output
from bloom.util import code
from bloom.util import create_temporary_directory
from bloom.util import execute_command
from bloom.util import get_versions_from_upstream_tag
from bloom.util import handle_global_arguments
from bloom.util import print_exc
from bloom.util import segment_version

try:
    from vcstools import VcsClient
except ImportError:
    error("vcstools was not detected, please install it.", file=sys.stderr)
    sys.exit(code.VCSTOOLS_NOT_FOUND)

has_rospkg = False
try:
    import rospkg
    has_rospkg = True
except ImportError:
    warning("rospkg was not detected, stack.xml discovery is disabled",
            file=sys.stderr)


def convert_catkin_to_bloom(cwd=None):
    """
    Converts an old style catkin branch/catkin.conf setup to bloom.
    """
    # Rename the branch to bloom from catkin
    execute_command('git branch -m catkin bloom', cwd=cwd)
    # Change to the bloom branch
    checkout('bloom', directory=cwd)
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
    error("This does not appear to be a bloom release repo. "
          "Please initialize it first using: git "
          "bloom-set-upstream <UPSTREAM_VCS_URL> <VCS_TYPE> [<VCS_BRANCH>]")
    sys.exit(1)


def check_for_bloom():
    """
    Checks for the bloom branch, else looks for and converts the catkin branch.
    Then it checks for the bloom branch and that it contains a bloom.conf file.
    """
    if branch_exists('catkin') and not branch_exists('bloom'):
        # Found catkin branch, migrate it to bloom
        info('catkin branch detected, up converting to the bloom branch')
        convert_catkin_to_bloom()
        return
    # Check for bloom.conf
    if os.path.exists('bloom'):
        error("File or directory bloom prevents checking out to the bloom "
              "branch, remove it.")
        sys.exit(1)
    if not branch_exists('bloom'):
        debug('no bloom branch')
        not_a_bloom_release_repo()
    with inbranch('bloom'):
        if not os.path.exists(os.path.join(os.getcwd(), 'bloom.conf')):
            debug('no bloom.conf file')
            not_a_bloom_release_repo()


def parse_bloom_conf(cwd=None):
    """
    Parses the bloom.conf file in the current directory and returns info in it.
    """
    bloom_conf = show('bloom', 'bloom.conf', directory=cwd)
    with open('.bloom.conf', 'w+') as f:
        f.write(bloom_conf)
    cmd = 'git config -f .bloom.conf bloom.upstream'
    upstream_repo = check_output(cmd, shell=True, cwd=cwd).strip()
    cmd = 'git config -f .bloom.conf bloom.upstreamtype'
    upstream_type = check_output(cmd, shell=True, cwd=cwd).strip()
    try:
        cmd = 'git config -f .bloom.conf bloom.upstreambranch'
        upstream_branch = check_output(cmd, shell=True, cwd=cwd).strip()
    except CalledProcessError:
        upstream_branch = ''
    os.remove('.bloom.conf')
    return upstream_repo, upstream_type, upstream_branch


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
        if has_rospkg:
            info("package.xml(s) not found, looking for stack.xml")
            if os.path.exists(stack_path):
                info("stack.xml found")
                # Assumes you are at the top of the repo
                stack = rospkg.stack.parse_stack_file(stack_path)
                meta = {}
                meta['name'] = [stack.name]
                meta['version'] = stack.version
                meta['type'] = 'stack.xml'
            else:
                error("Neither stack.xml, nor package.xml(s) were detected.")
                sys.exit(1)
        else:
            error("Package.xml(s) were not detected.")
            sys.exit(1)
    else:
        info("package.xml(s) found")
        try:
            version = verify_equal_package_versions(packages.values())
        except RuntimeError as err:
            print_exc(traceback.format_exc())
            error("Releasing multiple packages with different versions is "
                  "not supported: " + str(err))
            sys.exit(1)
        meta = {}
        meta['version'] = version
        meta['name'] = [p.name for p in packages.values()]
        meta['type'] = 'package.xml'
    return meta


def try_vcstools_checkout(repo, checkout_url, version=''):
    if not repo.checkout(checkout_url, version, shallow=True):
        if repo.get_vcs_type_name() == 'svn':
            error(
                "Could not checkout upstream repostiory "
                "({0})".format(checkout_url)
            )
        else:
            error(
                "Could not checkout upstream repostiory "
                "({0})".format(checkout_url)
              + " to branch ({0})".format(version)
            )
        return 1
    return 0


def auto_upstream_checkout(upstream_repo, upstream_url, devel_branch):
    info("Searching in upstream development branch for the name and version")
    info("  Upstream url: " + upstream_url)
    info("  Upstream type: " + upstream_repo.get_vcs_type_name())
    if devel_branch:
        info("  Upstream branch: " + str(devel_branch))
    # Handle special svn cases
    if upstream_repo.get_vcs_type_name() == 'svn':
        if devel_branch == '':
            upstream_url += '/trunk'
        else:
            upstream_url += '/branches/' + str(devel_branch)
        devel_branch = ''
    # Checkout to the upstream development branch
    retcode = try_vcstools_checkout(upstream_repo, upstream_url, devel_branch)
    if retcode != 0:
        return retcode
    # Look into the upstream devel branch for the version
    meta = get_upstream_meta(upstream_repo.get_path())
    if meta is None or None in meta.values():
        error("Failed to get the upstream meta data.")
        return 1
    # Summarize the package.xml/stack.xml contents
    info("Found upstream with version: " + ansi('boldon') + meta['version'] + \
         ansi('reset'))
    if meta['type'] == 'stack.xml':
        info("Upstream contains a stack called: " + ansi('boldon') + \
             meta['name'][0] + ansi('reset'))
    else:
        info("Upstream contains package" + \
             ('s: ' if len(meta['name']) > 1 else ': ') + ansi('boldon') + \
             ', '.join(meta['name']) + ansi('reset'))
    # If svn recreate upstream_repo and checkout to the tag
    if upstream_repo.get_vcs_type_name() == 'svn':
        # Remove the /trunk from the url
        upstream_url = '/'.join(upstream_url.split('/')[:-1])
        upstream_dir = upstream_repo.get_path()
        shutil.rmtree(upstream_dir)  # Delete old upstream
        upstream_repo = VcsClient('svn', upstream_dir)
        checkout_url = upstream_url + '/tags/' + meta['version']
        if not upstream_repo.checkout(checkout_url):
            got_it = False
            for name in meta['name']:
                warning("Didn't find the tagged version at " + checkout_url)
                checkout_url = upstream_url + '/tags/' + name + \
                               '-' + meta['version']
                warning("Trying " + checkout_url)
                if upstream_repo.checkout(checkout_url):
                    got_it = True
                    break
            if not got_it:
                error("Could not checkout upstream version")
                return 1
    # Return the meta data
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

    ### Fetch the upstream tag
    upstream_repo = None
    upstream_repo_dir = os.path.join(tmp_dir, 'upstream_repo')
    # If explicit svn url just export and git-import-orig
    if args.explicit_svn_url is not None:
        if args.upstream_version is None:
            error("'--explicit-svn-version' must be specified with "
                  "'--explicit-svn-url'")
            return 1
        info("Checking out upstream at version " + ansi('boldon') + \
             str(args.upstream_version) + ansi('reset') + \
             " from repository at " + ansi('boldon') + \
             str(args.explicit_svn_url) + ansi('reset'))
        upstream_repo = VcsClient('svn', upstream_repo_dir)
        retcode = try_vcstools_checkout(upstream_repo, args.explicit_svn_url)
        if retcode != 0:
            return retcode
        meta = {
            'name': None,
            'version': args.upstream_version,
            'type': 'manual'
        }
    # Else fetching from bloom configs
    else:
        # Check for a bloom branch
        check_for_bloom()
        # Parse the bloom config file
        upstream_url, upstream_type, upstream_branch = parse_bloom_conf()
        # If the upstream_tag is specified, don't search just fetch
        upstream_repo = VcsClient(upstream_type, upstream_repo_dir)
        if args.upstream_tag is not None:
            warning("Using specified upstream tag '" + args.upstream_tag + "'")
            if upstream_type == 'svn':
                upstream_url += '/tags/' + args.upstream_tag
                upstream_tag = ''
            else:
                upstream_tag = args.upstream_tag
            retcode = try_vcstools_checkout(upstream_repo,
                                            upstream_url,
                                            upstream_tag)
            if retcode != 0:
                return retcode
            meta = {
                'name': None,
                'version': args.upstream_tag,
                'type': 'manual'
            }
        # We have to search for the upstream tag
        else:
            if args.upstream_devel is not None:
                warning("Overriding the bloom.conf upstream branch with " + \
                        args.upstream_devel)
                devel_branch = args.upstream_devel
            else:
                devel_branch = upstream_branch
            meta = auto_upstream_checkout(upstream_repo,
                                             upstream_url, devel_branch)
            if type(meta) not in [dict] and meta != 0:
                return meta

    ### Export the repository
    version = args.upstream_version if args.upstream_version is not None \
                                    else meta['version']

    # Export the repository to a tar ball
    tarball_prefix = 'upstream-' + str(version)
    info('Exporting version {0}'.format(version))
    tarball_path = os.path.join(tmp_dir, tarball_prefix)
    if upstream_repo.get_vcs_type_name() == 'svn':
        upstream_repo.export_repository('', tarball_path)
    else:
        upstream_repo.export_repository(version, tarball_path)

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
        last_tag_version = '.'.join([gbp_major, gbp_minor, gbp_patch])
        if parse_version(version) < parse_version(last_tag_version):
            warning("""\
Version discrepancy:
    The upstream version, {0}, is not newer than the previous \
release version, {1}.
""".format(version, last_tag_version))
        if parse_version(version) <= parse_version(last_tag_version):
            if args.replace:
                if not gbp.has_replace():
                    error("The '--replace' flag is not supported on this "
                          "version of git-buildpackage.")
                    return 1
                # Remove the conflicting tag first
                warning("""\
The upstream version, {0}, is equal to or less than a previous \
import version.
    Removing conflicting tag before continuing \
because the '--replace' options was specified.\
""".format(version))
                execute_command('git tag -d {0}'.format('upstream/' + version))
                execute_command('git push origin :refs/tags/'
                                '{0}'.format('upstream/' + version))
            else:
                warning("""\
The upstream version, {0}, is equal to a previous import version. \
git-buildpackage will fail, if you want to replace the existing \
upstream import use the '--replace' option.\
""".format(version))

    # Look for upstream branch
    if not branch_exists('upstream', local_only=True):
        create_branch('upstream', orphaned=True, changeto=True)

    # Go to the master branch
    bloom_repo.update(get_commit_hash('upstream'))

    # Detect if git-import-orig is installed
    tarball_path += '.tar.gz'
    if gbp.import_orig(tarball_path, args.interactive) != 0:
        return 1

    # Push changes back to the original bloom repo
    execute_command('git push --all -f')
    execute_command('git push --tags')


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Imports the upstream repository using git-buildpackage's git-import-orig.

This should be run in a git-buildpackage repository which has had its
upstream repository and upstream type set using the 'git-bloom-config'
tool. Optionally, the upstream branch can also be set by 'git-bloom-
config' as the place for git-bloom-import-upstream to search for a valid
package.xml (or stack.xml).

The default behaviour for git-bloom-import-upstream is to look at the
development branch (upstream branch or master/tip/trunk/etc...) for
package.xml(s) or a stack.xml. If found, the version is extracted from
the package.xml(s)/stack.xml and used as the upstream tag name from
which to import the upstream.

Which branch is searched for package.xml(s)/stack.xml can be overridden
using the '--upstream-devel' argument.  For example, if by default your
normal development branch is 'master', but you have a branch for an
older version, say '1.1.x', and need to release from it then
'--upstream-devel 1.1.x' will search that branch instead for the version.

For non-standard version tags (v1.1, 1.1-pre1) or if upstream projects
that do not contain a package.xml/stack.xml then the '--upstream-tag'
argument will prevent searching for the version in package.xml/stack.xml
and just try to import the given tag from the upstream repository. For
example, specifying '--upstream-tag foo-1.18' on an upstream repository,
'svn.example.com/svn/foo', would cause git-bloom-import-upstream to
import 'svn.example.com/svn/foo/tags/foo-1.18'.

For non standard svn layouts, the '--explicit-svn-url' argument can be
used. Specifying this argument will cause git-bloom-import-upstream to
import directly from this url, without trying to do anything
intelligent. Using this requires setting the version using
'--upstream-version'.

When importing non catkin projects use the '--upstream-version' argument
to specify the incoming version of the upstream project. This will
prevent automatic detection of the version and therefore will not fail
when neither a package.xml nor a stack.xml is not found.

""", formatter_class=argparse.RawTextHelpFormatter)
    add = parser.add_argument
    add('-i', '--interactive', action="store_true",
        help="""\
Allows git-import-orig to be run interactively,
otherwise questions are prevented by passing the
'--non-interactive' flag. (not supported on Lucid)

""")
    add('-r', '--replace', action="store_true",
        help="""\
Replaces an existing upstream import if the
git-buildpackage repository already has the
upstream version being released.

""")
    add('--upstream-devel', dest='upstream_devel', default=None,
        help="development branch on which to search for\n"
             "package.xml(s)/stack.xml\n\n")
    add('--upstream-tag', default=None,
        help="tag of the upstream repository to import from\n\n")
    add('--explicit-svn-url', default=None,
        help="explicit url for svn upstream (overrides upstream url)\n\n")
    add('--upstream-version', dest='upstream_version', default=None,
        help="explicitly specify the version\n"
             "(must be used with '--explicit-svn-url')\n\n")
    return parser


def main(sysargs=None):
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Check that the current directory is a serviceable git/bloom repo
    ret = ensure_clean_working_env()
    if ret != 0:
        parser.print_usage()
        return ret

    # Get the current git branch
    current_branch = get_current_branch()

    # Create a working temp directory
    tmp_dir = create_temporary_directory()

    cwd = os.getcwd()

    try:
        # Get off upstream branch
        if current_branch == 'upstream':
            checkout(get_commit_hash('upstream'), directory=cwd)

        retcode = import_upstream(cwd, tmp_dir, args)

        # Done!
        retcode = retcode if retcode is not None else 0
        if retcode == 0:
            info("I'm happy.  You should be too.")

        return retcode
    finally:
        # Change back to the original cwd
        os.chdir(cwd)
        # Clean up
        shutil.rmtree(tmp_dir)
        if current_branch and branch_exists(current_branch, True, cwd):
            checkout(current_branch, directory=cwd)
