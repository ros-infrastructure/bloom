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

import os
import pkg_resources

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

try:
    import catkin_pkg
    from pkg_resources import parse_version
    if parse_version(catkin_pkg.__version__) < parse_version('0.1.10'):
        error("This version of bloom requires catkin_pkg version >= '0.1.10',"
              " the used version of catkin_pkg is '{0}'".format(catkin_pkg.__version__),
              exit=True)
    from catkin_pkg.cmake import configure_file
    from catkin_pkg.cmake import get_metapackage_cmake_template_path
except ImportError as err:
    error("catkin_pkg was not detected, please install it.", exit=True)

BLOOM_GROUP = 'bloom.generators'


def list_generators():
    generators = []
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        generators.append(entry_point.name)
    return generators


def load_generator(generator_name):
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        if entry_point.name == generator_name:
            return entry_point.load()


def check_metapackage_for_valid_cmake(name):
    if not os.path.exists('CMakeLists.txt'):
        warning("See: http://ros.org/reps/rep-0127.html#metapackage")
        error("Metapackage '{0}' does not have a CMakeLists.txt, refusing to release."
              .format(name),
              exit=True)
    template_path = get_metapackage_cmake_template_path()
    env = {'name': name, 'metapackage_arguments': ''}
    expected_cmake = configure_file(template_path, env)
    with open('CMakeLists.txt', 'r') as f:
        actual_cmake = f.read()
    if expected_cmake != actual_cmake:
        error("Metapackage '{0}' has a non-compliant CMakeLists.txt, expected:"
              .format(name))
        for line in expected_cmake.splitlines():
            info("  " + line)
        error("But got instead:")
        for line in actual_cmake.splitlines():
            info("  " + line)
        warning("See: http://ros.org/reps/rep-0127.html#metapackage")
        error("Metapackage '{0}' has a non-compliant CMakeLists.txt".format(name),
              exit=True)


def is_metapackage(package):
    metapack = [True for e in package.exports if e.tagname == 'metapackage']
    if len(metapack) > 0:
        return True
    else:
        return False


class GeneratorError(Exception):
    def __init__(self, retcode):
        super(GeneratorError, self).__init__("Error running generator")
        self.retcode = retcode


class BloomGenerator(object):
    """
    Abstract generator class, from which all bloom generators inherit.
    """
    generator_type = None
    title = 'no title'
    description = None
    help = None

    @classmethod
    def exit(cls, retcode):
        raise GeneratorError(retcode)

    def prepare_arguments(self, parser):
        """
        Argument preparation hook, should be implemented in child class

        :param parser: argparse.ArgumentParser on which to call add_argument()
        """
        pass

    def handle_arguments(self, args):
        """
        Hook to handle parsed arguments from argparse
        """
        debug("BloomGenerator.handle_arguments: got args -> " + str(args))

    def summarize(self):
        """
        Summarize the command, consider listing configurations here
        """
        info("Running " + self.title + " generator")

    def get_branching_arguments(self):
        """
        Return a list of tuples, each representing parameters for branching.

        Override this to return something other than [] if this generator
        needs to produce branches.

        The tuples can either be singular (destination,), or contain two
        elements (destination, source). Optionally, a third tuple element
        can be a bool indicating if git-bloom-branch should be interactive:
        (destination, source, interactive)

        :returns: list of tuples containing arguments for git-bloom-branch
        """
        return []

    def pre_branch(self, destination, source):
        """
        Pre-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_branch(self, destination, source):
        """
        Post-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_export_patches(self, branch_name):
        """
        Pre-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_export_patches(self, branch_name):
        """
        Post-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_rebase(self, branch_name):
        """
        Pre-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_rebase(self, branch_name):
        """
        Post-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_patch(self, branch_name):
        """
        Pre-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_patch(self, branch_name):
        """
        Post-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0
