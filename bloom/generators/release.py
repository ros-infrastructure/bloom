# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
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

import traceback

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_current_branch

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info
from bloom.logging import warning

from bloom.packages import get_package_data

from bloom.util import execute_command

from bloom.commands.git.patch.trim_cmd import trim

try:
    import catkin_pkg
    from pkg_resources import parse_version
    if parse_version(catkin_pkg.__version__) < parse_version('0.3.8'):
        warning("This version of bloom requires catkin_pkg version >= '0.3.8',"
                " the used version of catkin_pkg is '{0}'".format(catkin_pkg.__version__))
    from catkin_pkg import metapackage
except ImportError as err:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.", exit=True)


class ReleaseGenerator(BloomGenerator):
    title = 'release'
    description = """\
Generates a release branch for each of the packages in the source branch.
The common use case for this generator is to produce release/* branches for
each package in the upstream repository, so the source branch should be set to
'upstream' and the prefix set to 'release'.
"""

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-s', '--src', '--source-branch', default=None, dest='src',
            help="git branch to branch from (defaults to 'upstream')")
        add('-n', '--package-name', default=None, dest='name',
            help="name of package being released (use if non catkin project)")
        add('-p', '--prefix', default='release', dest='prefix',
            help="prefix for target branch name(s)")
        add('--release-increment', '-i', default=0,
            help="release increment number")
        return BloomGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.prefix = args.prefix
        if args.src is None:
            current_branch = get_current_branch()
            if current_branch is None:
                error("Could not determine current branch.", exit=True)
            self.src = current_branch
        else:
            self.src = args.src
        self.name = args.name
        self.release_inc = args.release_increment

    def summarize(self):
        self.branch_list = self.detect_branches()
        if type(self.branch_list) not in [list, tuple]:
            self.exit(self.branch_list if self.branch_list is not None else 1)
        info("Releasing package" +
             ('' if len(self.branch_list) == 1 else 's') + ": " + str(self.branch_list))

    def get_branching_arguments(self):
        p, s, i = self.prefix, self.src, self.interactive
        self.branch_args = [['/'.join([p, b]), s, i] for b in self.branch_list]
        return self.branch_args

    def pre_rebase(self, destination, msg=None):
        name = destination.split('/')[-1]
        msg = msg if msg is not None else (
            "Releasing package '" + name + "' to: '" + destination + "'"
        )
        info(msg)
        ret = trim(undo=True)
        return 0 if ret is None or ret < 0 else ret  # Ret < 0 indicates nothing was done

    def post_rebase(self, destination):
        # Figure out the trim sub dir
        name = destination.split('/')[-1]
        trim_d = [k for k, v in self.packages.items() if v.name == name][0]
        # Execute trim
        if trim_d in ['', '.']:
            return
        return trim(trim_d)

    def post_patch(self, destination):
        # Figure out the version of the given package
        if self.name is not None:
            warning("""\
Cannot automatically tag the release because this is not a catkin project.""")
            warning("""\
Please checkout the release branch and then create a tag manually with:""")
            warning("  git checkout release/" + str(self.name))
            warning("  git tag -f release/" + str(self.name) + "/<version>")
            return
        with inbranch(destination):
            name, version, packages = get_package_data(destination)
        # Execute git tag
        release_tag = destination + '/' + version + '-' + self.release_inc
        execute_command('git tag ' + release_tag)

    def metapackage_check(self, path, pkg):
        if pkg.is_metapackage():
            try:
                metapackage.validate_metapackage(path, pkg)
            except metapackage.InvalidMetapackage as e:
                warning("Invalid metapackage:")
                warning("  %s\n" % str(e))
                error(fmt("Refusing to release invalid metapackage '@|%s@{rf}@!', metapackage requirements:\n  @|%s" %
                      (pkg.name, metapackage.DEFINITION_URL)), exit=True)

    def detect_branches(self):
        self.packages = None
        with inbranch(self.src):
            if self.name is not None:
                self.packages = [self.name]
                return [self.name]
            name, version, packages = get_package_data(self.src)
            self.packages = packages
            # Check meta packages for valid CMakeLists.txt
            if isinstance(self.packages, dict):
                for path, pkg in self.packages.items():
                    # Check for valid CMakeLists.txt if a metapackage
                    self.metapackage_check(path, pkg)
            return name if type(name) is list else [name]
