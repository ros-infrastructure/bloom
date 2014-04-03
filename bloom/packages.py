# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Open Source Robotics Foundation, Inc.
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
#  * Neither the name of Open Source Robotics Foundation, Inc. nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
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

"""
Provides common utility functions for bloom.
"""

from __future__ import print_function

import os
import sys
import traceback

from bloom.git import show

from bloom.config import BLOOM_CONFIG_BRANCH

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr, exit=True)


def get_ignored_packages(release_directory=None):
    prefix = os.environ.get('BLOOM_TRACK', 'packages')
    data = show(BLOOM_CONFIG_BRANCH, '{0}.ignored'.format(prefix), directory=release_directory) or ''
    return [p.strip() for p in data.split() if p.strip()]


def get_package_data(branch_name=None, directory=None, quiet=True, release_directory=None):
    """
    Gets package data about the package(s) in the current branch.

    It also ignores the packages in the `packages.ignore` file in the master branch.

    :param branch_name: name of the branch you are searching on (log use only)
    """
    log = debug if quiet else info
    repo_dir = directory or os.getcwd()
    if branch_name:
        log("Looking for packages in '{0}' branch... ".format(branch_name), end='')
    else:
        log("Looking for packages in '{0}'... ".format(directory or os.getcwd()), end='')
    # Check for package.xml(s)
    packages = find_packages(repo_dir)
    if type(packages) == dict and packages != {}:
        if len(packages) > 1:
            log("found " + str(len(packages)) + " packages.",
                use_prefix=False)
        else:
            log("found '" + list(packages.values())[0].name + "'.",
                use_prefix=False)
        version = verify_equal_package_versions(packages.values())
        ignored_packages = get_ignored_packages(release_directory=release_directory)
        for k, v in dict(packages).items():
            # Check for packages with upper case names
            if v.name.lower() != v.name:
                error("Cowardly refusing to release packages with uppercase characters in the name: " + v.name)
                error("See:")
                error("  https://github.com/ros-infrastructure/bloom/issues/191")
                error("  https://github.com/ros-infrastructure/bloom/issues/76")
                error("Invalid package names, aborting.", exit=True)
            # Check for ignored packages
            if v.name in ignored_packages:
                warning("Explicitly ignoring package '{0}' because it is in the `{1}.ignored` file."
                        .format(v.name, os.environ.get('BLOOM_TRACK', 'packages')))
                del packages[k]
        if packages == {}:
            error("All packages that were found were also ignored, aborting.",
                  exit=True)
        return [p.name for p in packages.values()], version, packages
    # Otherwise we have a problem
    log("failed.", use_prefix=False)
    error("No package.xml(s) found, and '--package-name' not given, aborting.",
          use_prefix=False, exit=True)
