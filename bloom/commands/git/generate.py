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

import argparse
import sys
import traceback

from subprocess import CalledProcessError

from bloom.commands.git.branch import execute_branch

from bloom.generators import GeneratorError
from bloom.generators import list_generators
from bloom.generators import load_generator

from bloom.git import ensure_clean_working_env
from bloom.git import ensure_git_root
from bloom.git import GitClone

from bloom.logging import debug
from bloom.logging import error
# from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import warning

from bloom.commands.git.patch.export_cmd import export_patches
from bloom.commands.git.patch.import_cmd import import_patches
from bloom.commands.git.patch.rebase_cmd import rebase_patches

from bloom.util import add_global_arguments
from bloom.util import code
from bloom.util import handle_global_arguments
from bloom.util import maybe_continue
from bloom.util import print_exc


class CommandFailed(Exception):
    def __init__(self, returncode):
        self.returncode = returncode


def parse_branch_args(branch_args, interactive):
    if type(branch_args) not in [list, tuple] or \
       len(branch_args) not in [1, 2, 3]:
        error("Invalid branching arguments given: '" + str(branch_args) + "'")
        raise GeneratorError(code.INVALID_BRANCH_ARGS)
    blen = len(branch_args)
    # Get branching parameters:
    dest = branch_args[0]
    source = branch_args[1] if blen >= 2 else None
    interactive = interactive
    if blen == 3 and branch_args[2] is not None:
        interactive = branch_args[2]
    return dest, source, interactive


def summarize_branch_cmd(destination, source, interactive):
    msg = "Executing 'git-bloom-branch " + str(destination)
    if source is not None:
        msg += " --src " + str(source)
    if interactive:
        msg += " --interactive"
    msg += "'"
    return msg


def try_execute(msg, err_msg, func, *args, **kwargs):
    retcode = 0
    try:
        retcode = func(*args, **kwargs)
        retcode = retcode if retcode is not None else 0
    except CalledProcessError as err:
        print_exc(traceback.format_exc())
        error("Error calling {0}: {1}".format(msg, str(err)))
        retcode = err.returncode
    ret_msg = msg + " returned exit code ({0})".format(str(retcode))
    if retcode > 0:
        error(ret_msg)
        raise CommandFailed(retcode)
    elif retcode < 0:
        debug(ret_msg)
    return retcode


def run_generator(generator, arguments):
    try:
        gen = generator
        try_execute('generator handle arguments', '',
                    gen.handle_arguments, arguments)
        try_execute('generator summarize', '',
                    gen.summarize)
        if arguments.interactive:
            if not maybe_continue('y'):
                error("Answered no to continue, aborting.", exit=True)
        try_execute('generator pre_modify', '',
                    gen.pre_modify)
        for branch_args in generator.get_branching_arguments():
            parsed_branch_args = parse_branch_args(branch_args,
                                                   arguments.interactive)
            destination, source, interactive = parsed_branch_args
            # Summarize branch command
            msg = summarize_branch_cmd(destination, source, interactive)

            # Run pre - branch - post
            # Pre branch
            try_execute('generator pre_branch', msg,
                        gen.pre_branch, destination, source)
            # Branch
            try_execute('git-bloom-branch', msg,
                        execute_branch, source, destination, interactive)
            # Post branch
            try_execute('generator post_branch', msg,
                        gen.post_branch, destination, source)

            # Run pre - export patches - post
            # Pre patch
            try_execute('generator pre_export_patches', msg,
                        gen.pre_export_patches, destination)
            # Export patches
            try_execute('git-bloom-patch export', msg, export_patches)
            # Post branch
            try_execute('generator post_export_patches', msg,
                        gen.post_export_patches, destination)

            # Run pre - rebase - post
            # Pre rebase
            try_execute('generator pre_rebase', msg,
                        gen.pre_rebase, destination)
            # Rebase
            ret = try_execute('git-bloom-patch rebase', msg, rebase_patches)
            # Post rebase
            try_execute('generator post_rebase', msg,
                        gen.post_rebase, destination)

            # Run pre - import patches - post
            # Pre patch
            try_execute('generator pre_patch', msg,
                        gen.pre_patch, destination)
            if ret == 0:
                # Import patches
                try_execute('git-bloom-patch import', msg, import_patches)
            elif ret < 0:
                debug("Skipping patching because rebase did not run.")
            # Post branch
            try_execute('generator post_patch', msg,
                        gen.post_patch, destination)
    except CommandFailed as err:
        sys.exit(err.returncode or 1)


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
        generator = load_generator(generator_name)
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
    from bloom.config import upconvert_bloom_to_config_branch
    upconvert_bloom_to_config_branch()

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

    # Check that the current directory is a serviceable git/bloom repo
    try:
        ensure_clean_working_env()
        ensure_git_root()
    except SystemExit:
        parser.print_usage()
        raise

    # Run the generator that was selected in a clone
    # The clone protects the release repo state from mid change errors
    with log_prefix('[git-bloom-generate {0}]: '.format(generator.title)):
        git_clone = GitClone()
        with git_clone:
            run_generator(generator, args)
        git_clone.commit()
