from __future__ import print_function

import os
import subprocess
import traceback

from .. util import check_output
from .. util import execute_command
from .. logging import error
from .. git import has_changes
from .. git import inbranch

_patch_config_keys = ['parent', 'base', 'trim', 'trimbase']
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
    @inbranch(patches_branch, directory=directory)
    def fn():
        global _patch_config_keys
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        if not os.path.exists(conf_path):
            return None
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            config = {}
            for key in _patch_config_keys:
                config[key] = check_output(cmd + key, shell=True,
                                           cwd=directory).strip()
            return config
        except subprocess.CalledProcessError as err:
            traceback.print_exc()
            error("Failed to get patches info: " + str(err))
            return None
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
            traceback.print_exc()
            error("Failed to set patches info: " + str(err))
            raise
    return fn(config)
