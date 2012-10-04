from __future__ import print_function

import os
import sys
import traceback
import argparse
import shutil

from .. util import add_global_arguments
from .. util import execute_command
from .. util import handle_global_arguments
from .. util import print_exc
from .. logging import debug
from .. logging import error
from .. logging import log_prefix
from .. logging import warning
from .. git import ensure_clean_working_env
from .. git import get_commit_hash
from .. git import get_current_branch
from .. git import get_root
from .. git import has_changes
from .. git import inbranch

from . import_cmd import import_patches
from . trim_cmd import trim
from . common import get_patch_config
from . common import set_patch_config
from . common import update_tag


@log_prefix('[git-bloom-patch rebase]: ')
def rebase_patches(force=False, directory=None):
    ### Ensure a clean/valid working environment
    ret = ensure_clean_working_env(force, git_status=True, directory=directory)
    if ret != 0:
        return ret
    # Make sure we need to actually call this
    current_branch = get_current_branch()
    patches_branch = 'patches/' + current_branch
    config = get_patch_config(patches_branch, directory=directory)
    upstream_commit_hash = get_commit_hash(config['parent'], directory)
    if upstream_commit_hash == config['previous']:
        warning("Nothing to do: Current branch (" + current_branch + ")'s "
                "base commit hash is the same as the source branch (" + \
                config['parent'] + ")'s commit hash.")
        warning("    Did you forget to update the parent branch first?")
        warning("    Updating the parent branch can be done by calling "
                "'git-bloom-patch rebase' on it, or 'git-bloom-import-upsteam'"
                " if the parent branch is the upstream branch.")
        return 0
    else:
        debug("rebase_patches: " + upstream_commit_hash + " == " + \
              config['previous'] + ": " + \
              str(upstream_commit_hash == config['previous']))
    ### Execute the rebase
    # Get the new source into a temporary directory

    @inbranch(config['parent'])
    def duplicate_source(tmp_direct, direct):
        root = get_root(direct)
        dst = os.path.join(tmp_direct, 'parent_source')
        shutil.copytree(root, dst)
        return dst

    from tempfile import mkdtemp
    tmp_dir = mkdtemp()
    try:
        parent_source = duplicate_source(tmp_dir, directory)

        # Clear out the local branch
        git_root = get_root(directory)
        execute_command('git rm -rf *', cwd=directory)
        dot_items = []
        for item in os.listdir(git_root):
            if item in ['.git', '..', '.']:
                continue
            if item.startswith('.'):
                dot_items.append(item)
        if len(dot_items) > 0:
            execute_command('git rm -rf ' + ' '.join(dot_items), cwd=directory)
        execute_command('git clean -fdx', cwd=directory)  # for good measure?

        # Copy the parent source into the newly cleaned directory
        for item in os.listdir(parent_source):
            if item == '.git':  # Ignore .git folder
                continue
            src = os.path.join(parent_source, item)
            dst = os.path.join(git_root, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)

        # Commit changes to the repository
        execute_command('git add ./*', cwd=directory)
        dot_items = []
        for item in os.listdir(git_root):
            if item in ['.git', '..', '.']:
                continue
            if item.startswith('.'):
                dot_items.append(item)
        if len(dot_items) > 0:
            execute_command('git add ' + ' '.join(dot_items), cwd=directory)
        execute_command('git clean -dXf')  # Only remove objects ignored by git
        if has_changes():
            cmd = 'git commit -m "Rebase from ' + config['parent'] + '"'
            execute_command(cmd, cwd=directory)

        # Update the patches information
        config = get_patch_config(patches_branch, directory)
        config['base'] = get_commit_hash(current_branch, directory)
        config['previous'] = get_commit_hash(config['parent'], directory)
        config['trimbase'] = ''
        set_patch_config(patches_branch, config, directory)
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

    ### Restore the trimming and patches
    # Reapply the trimming
    try:
        if config['trim'] != '':
            trim(directory=directory)
    except Exception as err:
        print_exc(traceback.format_exc())
        error(str(err))
        return 4
    # Reapply the patches
    try:
        import_patches(directory)
    except Exception as err:
        print_exc(traceback.format_exc())
        error(str(err))
        return 5
    # Update the tag
    update_tag()
    return 0


def get_parser():
    """Returns a parser.ArgumentParser with all arguments defined"""
    parser = argparse.ArgumentParser(description="""\
This command attempts to remove any trimming and patching from the working
branch, then merge from this branch's source branch, and finally reapplying
the trimming and patches.

It does this by following these steps:

    - Remove any changes (including uncommited and un-exported changes)
        - git-bloom-patch remove
    - Undo any trimming of the source branch
        - git-bloom-patch trim --undo
    - Merge changes from the source branch
        - git -Xtheirs merge <source branch>
    - Redo any trimming
        - git-bloom-patch trim
    - Reapply any patches
        - git-bloom-patch import

""", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--force', help="forces rebase", default=False,
                        action='store_true')
    return parser


def main():
    # Assumptions: in a git repo, this command verb was passed, argv has enough
    sysargs = sys.argv[2:]
    parser = get_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    return rebase_patches(args.force)
