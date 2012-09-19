from __future__ import print_function

import os
import subprocess
import traceback

from .. util import inbranch
from .. util import check_output
from .. util import execute_command
from .. logging import error


def list_patches(directory=None):
    files = os.listdir(directory)
    patches = []
    for f in files:
        if f.endswith('.patch'):
            patches.append(f)
    return patches


def get_patches_info(patches_branch, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn():
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        if not os.path.exists(conf_path):
            return [None, None]
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            parent = check_output(cmd + 'parent', shell=True, cwd=directory)
            spec = check_output(cmd + 'spec', shell=True, cwd=directory)
            return [parent, spec]
        except subprocess.CalledProcessError as err:
            traceback.print_exc()
            error("Failed to get patches info: " + str(err))
            return [None, None]
    return fn()


def set_patches_info(patches_branch, parent, base_commit, directory=None):
    @inbranch(patches_branch, directory=directory)
    def fn(parent, base_commit):
        conf_path = 'patches.conf'
        if directory is not None:
            conf_path = os.path.join(directory, conf_path)
        cmd = 'git config -f {0} patches.'.format(conf_path)
        try:
            parent_cmd = cmd + 'parent {0}'.format(parent)
            execute_command(parent_cmd, cwd=directory)
            spec_cmd = cmd + 'base {0}'.format(base_commit)
            execute_command(spec_cmd, cwd=directory)
        except subprocess.CalledProcessError as err:
            traceback.print_exc()
            error("Failed to set patches info: " + str(err))
    return fn(parent, base_commit)
