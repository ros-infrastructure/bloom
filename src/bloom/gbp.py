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

"""Interface for git-buildpackage"""

from __future__ import print_function

import sys
import subprocess

from distutils.version import LooseVersion

from bloom.logging import error

from bloom.util import execute_command

_gbp_version = None


# Assert that git-buildpackage is installed
def assert_gbp_exists():
    global _gbp_version
    p = subprocess.Popen('git-buildpackage --version', shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        _gbp_version = out.split()[1]
    return p.returncode == 0

if not assert_gbp_exists():
    error("Git-buildpackage is not installed, please install it before "
          "using bloom.")
    sys.exit(1)


def get_gbp_version():
    global _gbp_version
    return _gbp_version


def has_interactive():
    gbp_version = LooseVersion(get_gbp_version())
    return gbp_version >= LooseVersion('0.5.32')


def has_replace():
    return has_interactive()


def import_orig(tarball, interactive=False, merge=False, directory=None):
    cmd = 'git import-orig {0}'.format(tarball)
    if not interactive and has_interactive():
        cmd += ' --no-interactive'
    if not merge:
        cmd += ' --no-merge'
    ret = execute_command(cmd, silent=False, autofail=False, cwd=directory)
    if ret != 0:
        error("git-import-orig failed '{0}'".format(cmd))
        return True
    return False
