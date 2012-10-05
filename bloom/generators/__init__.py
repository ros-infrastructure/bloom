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

import os


class BloomGenerator(object):
    """
    Abstract generator class, from which all bloom generators inherit.
    """
    generator_type = None

    def __init__(self, title, description):
        self.__title = title
        self.__description = description
        self.__arguments = {}

    def add_argument(self, *args, **kwargs):
        """
        Adds argparse arguments to the generator

        See: http://docs.python.org/dev/library/argparse.html#the-\
        add-argument-method
        """
        self.__arguments[args] = kwargs

    def get_arguments(self):
        """
        Returns the accumulated argparse arguments

        :returns: a dict of args and kwargs for argparse's add_argument
        """
        return self.__arguments

    def branches(self):
        """
        Return True to cause a branching (and patching) step, default is True

        OVerride this to return False if this generator only runs on top of an
        existing branch and does not required separate patches.

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
    if this_file is None:
        try:
            this_file = __file__
        except NameError:
            return []
    if not this_file.endswith('__init__.py'):
        raise RuntimeError("list_generators must be called in a package")
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
    module = load_module(generator_name)
    if module is None:
        return None
    generator_class = generator_name.capitalize() + 'Generator'
    exec('generator = module.' + generator_class)
    locals()['generator'].generator_type = generator_name
    return locals()['generator']

if __name__ == '__main__':
    a = list_generators()
    print('Generators:') if len(a) > 0 else print('No generators found')
    for b in a:
        g = load_generator(load_generator_module, b)
        print('  ' + str(g.generator_type))

# P
# a
# d
# d
# i
# n
# g
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
# .
pass
