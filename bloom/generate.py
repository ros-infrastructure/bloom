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

import argparse

from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments

from bloom.generators import list_generators
from bloom.generators import load_generator_module
from bloom.generators import load_generator


def run_generator(generator, args):
    generator.handle_arguments(args)
    generator.summarize()


def create_subparsers(parent_parser, generators):
    subparsers = parent_parser.add_subparsers(
        title='generators',
        description='Available bloom platform generators:',
        dest='generator'
    )
    for generator in generators:
        parser = subparsers.add_parser(generator.title,
                                       description=generator.description,
                                       help=generator.help)
        generator.prepare_arguments(parser)
        add_global_arguments(parser)


def create_generators(generator_names):
    generators = {}
    for generator_name in generator_names:
        generator = load_generator(load_generator_module, generator_name)
        if generator is not None:
            generators[generator_name] = generator()
        else:
            warning("Failed to load generator: " + str(generator_name))
    return generators


def get_parser():
    parser = argparse.ArgumentParser(description="bloom platform generator")

    return parser


def main(sysargs=None):
    parser = get_parser()
    parser = add_global_arguments(parser)

    # List the generators
    generator_names = list_generators()

    # Create the generators
    generators = create_generators(generator_names)

    # Setup a subparser for each generator
    create_subparsers(parser, generators.values())

    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    generator = generators[args.generator]

    @log_prefix('[git-bloom-generate {0}]: '.format(generator.title))
    def do_it(generator, args):
        return run_generator(generator, args)

    # Run the generator that was selected
    return do_it(generator, args)
