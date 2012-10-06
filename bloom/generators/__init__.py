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

    def prepare_arguments(self, parser):
        """
        Argument preparation hook, should be implemented in child class

        Default arguments are added by this built-in base class method.
        The child class should call prepare_arguments of the base class
        for the default arguments after adding its own.

        :param parser: argparse.ArgumentParser on which to call add_argument()
        """
        group = parser.add_argument_group('common')
        add = group.add_argument
        add('-y', '--non-interactive', default=False, action='store_true',
            help="runs without user interaction")

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

    def branches(self):
        """
        Return True to cause a branching (and patching) step, default is True

        Override this to return False if this generator only runs on top of an
        existing branch and does not require separate patches.

        :returns: True to cause branching (and patching), False to skip it
        """
        return True

    def pre_branch(self):
        """
        Pre-branching hook, does not get called if branches() returns False
        """
        pass

    def post_branch(self):
        """
        Post-branching hook, does not get called if branches() returns False
        """
        pass

    def pre_patch(self):
        """
        Pre-patching hook, does not get called if branches() returns False
        """
        pass

    def post_patch(self):
        """
        Post-patching hook, does not get called if branches() returns False
        """
        pass


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
