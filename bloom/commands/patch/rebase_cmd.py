from __future__ import print_function

import os
import sys
import argparse
import shutil
from tempfile import mkdtemp

from bloom.git import ensure_clean_working_env
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import get_root
from bloom.git import has_changes
from bloom.git import inbranch

from bloom.logging import ansi
from bloom.logging import debug
from bloom.logging import log_prefix

from bloom.commands.patch.common import get_patch_config
from bloom.commands.patch.common import set_patch_config

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import get_package_data
from bloom.util import handle_global_arguments


def non_git_rebase(upstream_branch, directory=None):
    # Create a temporary storage directory
    tmp_dir = mkdtemp()
    # Get the root of the git repository
    git_root = get_root(directory)
    try:
        # Copy the new upstream source into the temporary directory
        with inbranch(upstream_branch):
            ignores = ('.git', '.gitignore', '.svn', '.hgignore', '.hg', 'CVS')
            parent_source = os.path.join(tmp_dir, 'parent_source')
            shutil.copytree(git_root, parent_source,
                            ignore=shutil.ignore_patterns(*ignores))

        # Clear out the local branch
        execute_command('git rm -rf *', cwd=directory)
        # Collect .* files (excluding .git)
        dot_items = []
        for item in os.listdir(git_root):
            if item in ['.git', '..', '.']:
                continue
            if item.startswith('.'):
                dot_items.append(item)
        # Remove and .* files missed by 'git rm -rf *'
        if len(dot_items) > 0:
            execute_command('git rm -rf ' + ' '.join(dot_items), cwd=directory)
        # Clear out any untracked files
        execute_command('git clean -fdx', cwd=directory)  # for good measure?

        # Copy the parent source into the newly cleaned directory
        for item in os.listdir(parent_source):
            src = os.path.join(parent_source, item)
            dst = os.path.join(git_root, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)

        # Commit changes to the repository
        execute_command('git add ./*', cwd=directory)
        # Collect .* files
        dot_items = []
        for item in os.listdir(git_root):
            if item in ['.git', '..', '.']:
                continue
            if item.startswith('.'):
                dot_items.append(item)
        # Add any .* files missed by 'git add ./*'
        if len(dot_items) > 0:
            execute_command('git add ' + ' '.join(dot_items), cwd=directory)
        # Remove any straggling untracked files
        execute_command('git clean -dXf', cwd=directory)
        # Only if we have local changes commit
        # (not true if the upstream didn't change any files)
        if has_changes(directory):
            cmd = 'git commit -m "Rebase from \'' + upstream_branch + '\'"'
            data = get_package_data(upstream_branch)
            if type(data) in [list, tuple]:
                cmd += " @ version '{}'".format(data[1])
            execute_command(cmd, cwd=directory)
    finally:
        # Clean up
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def git_rebase(upstream_branch, directory=None):
    """
    Not currently used, because the more explicit merge must be used
    when trimming is done.

    For example:
        Upstream @ 1.0:
            foo/
                foo.rst
            bar/
                bar.rst

        release/foo @ 1.0:
            foo.rst

        release/bar @ 1.0:
            bar.rst

        Then... @ upstream update

        Upstream @ 1.1:
            LICENSE.txt
            foo/
                foo.rst
            bar/
                bar.rst

        release/foo @ 1.1:
            LICENSE.txt
            foo.rst

        release/bar @ 1.1:
            LICENSE.txt
            bar.rst

    The LICENSE.txt survives because the original trim patches do not contain
    a removal of LICENSE.txt in the diff (the trim patches are explicit)
    """
    raise NotImplementedError('bloom.commands.patch.rebase_cmd.git_rebase')


@log_prefix('[git-bloom-patch rebase]: ')
def rebase_patches(without_git_rebase=True, directory=None):
    ### Ensure a clean/valid working environment
    ret = ensure_clean_working_env(git_status=True, directory=directory)
    if ret != 0:
        return ret
    ### Make sure we need to actually call this
    # Get the current branch
    current_branch = get_current_branch(directory)
    # Get the patches branch
    patches_branch = 'patches/' + current_branch
    # Get the current patches.conf
    config = get_patch_config(patches_branch, directory=directory)
    # Get the current upstream commit hash
    upstream_commit_hash = get_commit_hash(config['parent'], directory)
    # If the current upstream commit hash is the same as the stored one, noop
    if upstream_commit_hash == config['previous']:
        debug("Nothing to do: Current branch (" + current_branch + ")'s "
                "base commit hash is the same as the source branch (" + \
                config['parent'] + ")'s commit hash.")
        debug("    Did you forget to update the parent branch first?")
        debug("    Updating the parent branch can be done by calling "
                "'git-bloom-patch rebase' on it, or 'git-bloom-import-upsteam'"
                " if the parent branch is the upstream branch.")
        return 0
    else:
        debug("rebase_patches: " + upstream_commit_hash + " == " + \
              config['previous'] + ": " + \
              str(upstream_commit_hash == config['previous']))

    ### Execute the rebase
    if without_git_rebase:
        non_git_rebase(config['parent'], directory=directory)
    else:
        git_rebase(config['parent'], directory=directory)

    ### Update the patches information
    # Get the latest configs
    config = get_patch_config(patches_branch, directory)
    # Set the base to the current hash (before patches)
    config['base'] = get_commit_hash(current_branch, directory)
    # Set the new upstream hash to the previous upstream hash
    config['previous'] = get_commit_hash(config['parent'], directory)
    # Clear the trimbase (it needs to be reapplied)
    config['trimbase'] = ''
    # Write the new configs
    set_patch_config(patches_branch, config, directory)
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = argparse.ArgumentParser(
        description="""\
This command sets the contents of the current branch to the contents of
the parent (upstream) branch.

It does this by replacing the current branch contents with parent contents:
    - delete current branch contents, copy over upstream branch contents
    - clear trim flag (so it can be reapplied)
    - update patches.conf

{0}\
WARNING: make sure to export patches and commit local changes before rebasing\
{1}

""".format(ansi('yellowf'), ansi('reset')),
        formatter_class=argparse.RawTextHelpFormatter
    )
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    return rebase_patches()
