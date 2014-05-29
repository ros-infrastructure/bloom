from __future__ import print_function

import sys
import os
import tempfile
import shutil

from bloom.git import branch_exists
from bloom.git import checkout
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import get_root
from bloom.git import track_branches

from bloom.logging import debug
from bloom.logging import log_prefix
from bloom.logging import error
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import execute_command
from bloom.util import handle_global_arguments

from bloom.commands.git.patch.common import get_patch_config
from bloom.commands.git.patch.common import set_patch_config


def _set_trim_sub_dir(sub_dir, force, config, directory):
    debug("_set_trim_sub_dir(" + str(sub_dir) + ", " + str(force) + ", " +
          str(config) + ", " + str(directory) + ")")
    if sub_dir is not None:
        if config['trim'] != '' and config['trim'] != sub_dir:
            warning("You are trying to set the trim sub directory to " +
                    sub_dir + ", but it is already set to " +
                    config['trim'] + ".")
            if not force:
                warning("Changing the sud directory is not advised. "
                        "If you are sure you want to do this, use "
                        "'--force'")
                return None
            else:
                warning("Forcing the change of the sub directory.")
        # Make the sub_dir absolute
        git_root = get_root(directory)
        sub_dir_abs = os.path.join(git_root, sub_dir)
        # Make sure it is a directory
        if not os.path.isdir(sub_dir_abs):
            error("The given sub directory, (" + sub_dir + ") does not "
                  "exist in the git repository at " + git_root)
            return None
        # Set the trim sub directory
        config['trim'] = sub_dir
    return config


def _undo(config, directory):
    debug("_undo(" + str(config) + ", " + str(directory) + ")")
    # TODO: handle repo with changes
    # TODO: handle repo with patches applied
    if config['trimbase'] == '':
        debug("Branch has not been trimmed previously, undo not required.")
        return None
    # Reset with git-revert
    current_branch = get_current_branch(directory)
    if current_branch is None:
        error("Could not determine current branch.", exit=True)
    cmt = get_commit_hash(current_branch, directory)
    cmd = 'git revert --no-edit -Xtheirs ' + config['trimbase'] + '..' + cmt
    execute_command(cmd, cwd=directory)
    # Unset the trimbase
    config['trimbase'] = ''
    return config


def _trim(config, force, directory):
    debug("_trim(" + str(config) + ", " + str(force) + ", " +
          str(directory) + ")")
    if config['trimbase'] != '':
        warning("It looks like the trim operation has already been done, "
                "nested trimming is not supported.")
        if force:
            warning("Proceeding anyways because of '--force'")
        else:
            warning("If you would like to continue anyways use '--force'")
            return None
    current_branch = get_current_branch(directory)
    if current_branch is None:
        error("Could not determine current branch.", exit=True)
    config['trimbase'] = get_commit_hash(current_branch)
    tmp_dir = tempfile.mkdtemp()
    try:
        # Buckup trim sub directory
        git_root = get_root()
        sub_dir = os.path.join(git_root, config['trim'])
        storage = os.path.join(tmp_dir, config['trim'])
        shutil.copytree(sub_dir, storage)
        # Clear out any untracked files
        execute_command('git clean -fdx', cwd=directory)
        # Collect al files (excluding .git)
        items = []
        for item in os.listdir(git_root):
            if item in ['.git', '..', '.']:
                continue
            items.append(item)
        # Remove and .* files missed by 'git rm -rf *'
        if len(items) > 0:
            execute_command('git rm -rf ' + ' '.join(items), cwd=directory)
        # Copy the sub directory back
        for item in os.listdir(storage):
            src = os.path.join(storage, item)
            dst = os.path.join(git_root, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)
        # Stage
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
        # Commit
        cmd = 'git commit -m "Trimmed the branch to only the ' + \
              config['trim'] + ' sub directory"'
        execute_command(cmd, cwd=directory)
        # Update the patch base to be this commit
        current_branch = get_current_branch(directory)
        if current_branch is None:
            error("Could not determine current branch.", exit=True)
        config['base'] = get_commit_hash(current_branch)
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
    return config


@log_prefix('[git-bloom-patch trim]: ')
def trim(sub_dir=None, force=False, undo=False, directory=None):
    # Get the current branch
    current_branch = get_current_branch(directory)
    # Ensure the current branch is valid
    if current_branch is None:
        error("Could not determine current branch, are you in a git repo?",
              exit=True)
    # Construct the patches branch
    patches_branch = 'patches/' + current_branch
    try:
        # See if the patches branch exists
        if branch_exists(patches_branch, False, directory=directory):
            if not branch_exists(patches_branch, True, directory=directory):
                track_branches(patches_branch, directory)
        else:
            error("No patches branch (" + patches_branch + ") found, cannot "
                  "perform trim.", exit=True)
        # Get the parent branch from the patches branch
        config = get_patch_config(patches_branch, directory=directory)
        if config is None:
            error("Could not retrieve patches info.", exit=True)
        # If sub_dir is set, try to set it
        new_config = _set_trim_sub_dir(sub_dir, force, config, directory)
        if new_config is None:
            sys.exit('Could not perform trim')
        # Perform trime or undo
        if undo:
            new_config = _undo(new_config, directory)
            if new_config is None:
                return -1  # Indicates that nothing was done
        else:
            new_config = _trim(new_config, force, directory)
        if new_config is None:
            sys.exit('Could not perform trim')
        # Commit the new config
        set_patch_config(patches_branch, new_config, directory)
    finally:
        if current_branch:
            checkout(current_branch, directory=directory)


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'trim',
        description="""\
Moves a given sub directory into the root of the git repository.

If you call trim on a patched branch (even --undo), bad things will happen...\
"""
    )
    parser.set_defaults(func=main)
    add = parser.add_argument
    add('--sub-directory', '-s', metavar='SUB_DIRECTORY',
        help="the sub directory to move the root of the repository",
        default=None)
    add('--force', '-f', help="force the change of the SUB_DIRECTORY if set",
        action='store_true', default=False)
    add('--undo', '-u', help="reverses the the trim using 'git reset --hard'",
        action='store_true', default=False)
    add_global_arguments(parser)
    return parser


def main(args):
    handle_global_arguments(args)
    return trim(args.sub_directory, args.force, args.undo)
