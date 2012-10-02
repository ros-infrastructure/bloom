from __future__ import print_function

import os
import sys
import subprocess
import traceback

from .. util import check_output
from .. util import execute_command
from .. util import print_exc
from .. logging import error
from .. logging import debug
from .. git import get_current_branch
from .. git import has_changes
from .. git import inbranch

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.", file=sys.stderr)
    sys.exit(1)

try:
    import rospkg
except ImportError:
    print("rospkg was not detected, please install it.", file=sys.stderr)
    sys.exit(2)

_patch_config_keys = [
    'parent',    # The name of the parent reference
    'previous',  # Parent commit hash, used to check if rebase is needed
    'base',      # Commit hash before patches
    'trim',      # Trim sub folder name
    'trimbase'   # Commit hash before trimming
]
_patch_config_keys.sort()


def get_version(directory=None):
    basepath = directory if directory else os.getcwd()
    packages = find_packages(basepath=basepath)
    if type(packages) != dict or packages == {}:
        debug("get_version: didn't find packages, looking for stacks")
        stack_path = os.path.join(basepath, 'stack.xml')
        if os.path.exists(stack_path):
            stack = rospkg.stack.parse_stack_file(stack_path)
            return stack.version
        else:
            error("Version could not be determined.")
            sys.exit(1)
    try:
        return verify_equal_package_versions(packages.values())
    except RuntimeError as err:
        print_exc(traceback.format_exc())
        error("Releasing multiple packages with different versions is "
                "not supported: " + str(err))
        sys.exit(1)


def update_tag(version=None, force=True, directory=None):
    if version is None:
        version = get_version(directory)
    current_branch = get_current_branch(directory)
    tag_name = current_branch + "/" + version
    debug("Updating tag " + tag_name + " to point to " + current_branch)
    cmd = 'git tag ' + tag_name
    if force:
        cmd += ' -f'
    execute_command(cmd, cwd=directory)


def list_patches(directory=None):
    directory = directory if directory else '.'
    files = os.listdir(directory)
    patches = []
    for f in files:
        if f.endswith('.patch'):
            patches.append(f)
    return patches


def get_patch_config(patches_branch, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn():
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        if not os.path.exists(conf_path):
            return None
        cmd = 'git config -f {0} patches.'.format(conf_path)
        config = {}
        for key in _patch_config_keys:
            try:
                config[key] = check_output(cmd + key, shell=True,
                                           cwd=directory).strip()
            except subprocess.CalledProcessError as err:
                if key == 'previous':
                    config[key] = ''
                else:
                    print_exc(traceback.format_exc())
                    error("Failed to get patches info: " + str(err))
                    return None
        return config
    return fn()


def set_patch_config(patches_branch, config, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn(config):
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        config_keys = config.keys()
        config_keys.sort()
        if _patch_config_keys != config_keys:
            raise RuntimeError("Invalid config passed to set_patch_config")
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            for key in config:
                _cmd = cmd + key + ' "' + config[key] + '"'
                execute_command(_cmd, cwd=directory)
            # Stage the patches.conf file
            cmd = 'git add ' + conf_path
            execute_command(cmd, cwd=directory)
            if has_changes(directory):
                # Commit the changed config file
                cmd = 'git commit -m "Updated patches.conf"'
                execute_command(cmd, cwd=directory)
        except subprocess.CalledProcessError as err:
            print_exc(traceback.format_exc())
            error("Failed to set patches info: " + str(err))
            raise
    return fn(config)
