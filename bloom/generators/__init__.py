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

from __future__ import print_function

from bloom.logging import debug
from bloom.logging import info


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

    def __init__(self, title=None, description=None, help=None):
        self.title = title if title is not None else self.generator_type
        desc = description
        self.description = desc if desc is not None else self.description
        self.help = help if help is not None else self.help

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


def list_generators(this_file=None):
    import os
    if this_file is None:
        try:
            this_file = __file__
        except NameError:
            return []
    if this_file.split('/')[-1] not in ['__init__.py', '__init__.pyc']:
        raise RuntimeError("list_generators must be called in a package: " + \
                           this_file)
    this_location = os.path.dirname(os.path.abspath(this_file))
    modules = []  # Actually any modules or sub-pacakges in this package
    for item in os.listdir(this_location):
        if item == '__init__.py':
            continue
        item_location = os.path.join(this_location, item)
        if os.path.isdir(item_location):
            modules.append(item)
        if os.path.isfile(item_location):
            if item.endswith('.py'):
                modules.append(os.path.splitext(item)[0])
    return modules


def load_generator_module(generator_name):
    code = "import bloom.generators.{0} as module".format(generator_name)
    module = None
    exec(code)
    return module


def load_generator(load_module, generator_name):
    # Load the module
    module = load_module(generator_name)
    if module is None:
        return None
    # Find the generator class
    generator_class = None
    for item in dir(module):
        if item.lower() == (generator_name + 'generator').lower():
            generator_class = item
    if generator_class is None:
        raise RuntimeError("Could not find a generator class for the " + \
                           generator_name + " generator.")
    exec('generator = module.' + generator_class)
    locals()['generator'].generator_type = generator_name
    return locals()['generator']

if __name__ == '__main__':
    a = list_generators()
    print('Generators:') if len(a) > 0 else print('No generators found')
    for b in a:
        g = load_generator(load_generator_module, b)
        print('  ' + str(g.generator_type))
