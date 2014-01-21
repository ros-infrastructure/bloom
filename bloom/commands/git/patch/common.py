from __future__ import print_function

import os
import subprocess
import traceback

from bloom.git import has_changes
from bloom.git import inbranch
from bloom.git import show

from bloom.logging import error

from bloom.util import execute_command
from bloom.util import print_exc

_patch_config_keys = [
    'parent',    # The name of the parent reference
    'previous',  # Parent commit hash, used to check if rebase is needed
    'base',      # Commit hash before patches
    'trim',      # Trim sub folder name
    'trimbase'   # Commit hash before trimming
]
_patch_config_keys.sort()


def list_patches(directory=None):
    directory = directory if directory else '.'
    files = os.listdir(directory)
    patches = []
    for f in files:
        if f.endswith('.patch'):
            patches.append(f)
    return patches


def get_patch_config(patches_branch, directory=None):
    config_str = show(patches_branch, 'patches.conf')
    if config_str is None:
        error("Failed to get patches info: patches.conf does not exist")
        return None
    lines = config_str.splitlines()
    meta = {}
    for key in _patch_config_keys:
        meta[key] = ''
    for line in lines:
        if line.count('=') == 0:
            continue
        key, value = line.split('=', 1)
        meta[key.strip()] = value.strip()
    return meta


def set_patch_config(patches_branch, config, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn(config):
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        config_keys = list(config.keys())
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
