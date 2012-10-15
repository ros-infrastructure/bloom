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
import inspect
import traceback

from subprocess import CalledProcessError

from bloom.commands.branch import execute_branch

from bloom.generators import GeneratorError
from bloom.generators import list_generators
from bloom.generators import load_generator_module
from bloom.generators import load_generator

from bloom.logging import error
from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.commands.patch.export_cmd import export_patches
from bloom.commands.patch.import_cmd import import_patches
from bloom.commands.patch.rebase_cmd import rebase_patches

from bloom.util import add_global_arguments
from bloom.util import code
from bloom.util import handle_global_arguments
from bloom.util import maybe_continue
from bloom.util import print_exc


def parse_branch_args(branch_args):
    if type(branch_args) not in [list, tuple] or \
       len(branch_args) not in [1, 2, 3]:
        error("Invalid branching arguments given: " + str(branch_args))
    blen = len(branch_args)
    # Get branching parameters:
    dest = branch_args[0]
    source = branch_args[1] if blen >= 2 else None
    name = branch_args[2] if blen == 3 else None
    return dest, source, name


def summarize_branch_cmd(destination, source, name, interactive):
    msg = "Executing 'git-bloom-branch " + str(destination)
    if source is not None:
        msg += " --src " + str(source)
    if name is not None:
        msg += " --package-name " + str(name)
    if interactive:
        msg += " --interactive"
    msg += "'"
    return msg


class CommandFailed(Exception):
    def __init__(self, returncode):
        self.returncode = returncode


def try_execute(msg, err_msg, func, *args, **kwargs):
    try:
        if inspect.ismethod(func):
            obj = args[0]
            args = args[1:]
            pycode = 'retcode = obj.{0}(*args, **kwargs)'.format(func.__name__)
            obj
            exec(pycode)
        else:
            retcode = func(*args, **kwargs)
        retcode = retcode if retcode is not None else 0
    except CalledProcessError as err:
        print_exc(traceback.format_exc())
        error("Error calling {0}: ".format(msg) + str(err))
        retcode = err.returncode
    if retcode != 0:
        error(msg + " returned exit code ({0})".format(str(retcode)))
        raise CommandFailed(retcode)


def run_generator(generator, args):
    generator.handle_arguments(args)
    generator.summarize()
    if args.interactive:
        if not maybe_continue('y'):
            error("Answered no to continue, aborting.")
            return code.ANSWERED_NO_TO_CONTINUE
    for branch_args in generator.branches():
        destination, source, name = parse_branch_args(branch_args)
        interactive = args.interactive
        # Summarize branch command
        msg = summarize_branch_cmd(destination, source, name, interactive)
        info(msg)
        try:
            gen = generator
            ### Run pre - branch - post
            # Pre branch
            try_execute('generator pre_branch', msg,
                        gen.pre_branch, gen, destination, source)
            # Branch
            try_execute('git-bloom-branch', msg,
                        execute_branch, source, destination, interactive)
            # Post branch
            try_execute('generator post_branch', msg,
                        gen.post_branch, gen, destination, source)

            ### Run pre - export patches - post
            # Pre patch
            try_execute('generator pre_export_patches', msg,
                        gen.pre_export_patches, gen, destination)
            # Export patches
            try_execute('git-bloom-patch export', msg, export_patches)
            # Post branch
            try_execute('generator post_export_patches', msg,
                        gen.post_export_patches, gen, destination)

            ### Run pre - rebase - post
            # Pre patch
            try_execute('generator pre_patch', msg,
                        gen.pre_patch, gen, destination)
            # Rebase
            try_execute('git-bloom-patch rebase', msg, rebase_patches)
            # Post branch
            try_execute('generator post_patch', msg,
                        gen.post_patch, gen, destination)

            ### Run pre - patch - post
            # Pre patch
            try_execute('generator pre_patch', msg,
                        gen.pre_patch, gen, destination)
            # Import patches
            try_execute('git-bloom-patch import', msg, import_patches)
            # Post branch
            try_execute('generator post_patch', msg,
                        gen.post_patch, gen, destination)
        except CommandFailed as err:
            return err.returncode
    return 0


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

    group = parser.add_argument_group('common generator parameters')
    add = group.add_argument
    add('-y', '--non-interactive', default=True, action='store_false',
        help="runs without user interaction", dest='interactive')

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

    # Run the generator that was selected
    with log_prefix('[git-bloom-generate {0}]: '.format(generator.title)):
        try:
            return run_generator(generator, args)
        except GeneratorError as err:
            return err.retcode
