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

import argparse
import copy
import sys

from bloom.commands.import_upstream import main as iu_main

from bloom.commands.generate import GeneratorError
from bloom.commands.generate import create_generators
from bloom.commands.generate import create_subparsers
from bloom.commands.generate import run_generator

from bloom.generators import list_generators

from bloom.git import GitClone

from bloom.logging import ansi
from bloom.logging import error
from bloom.logging import info
from bloom.logging import log_prefix
from bloom.logging import push_log_prefix
from bloom.logging import pop_log_prefix
from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Preforms the standard release procedure: import, release, generate platform

The normal process for releasing catkin packages with bloom is as follows:

    $ git bloom-import-upstream
    $ git bloom-generate -y release --source upstream
    $ git bloom-generate -y <generator> --prefix release <generator args>

Where <generator> is one of the available platform generators, e.g. debian,
rosdebian, fedora, homebrew, etc...

Example:

    git bloom-release rosdebian groovy --debian-revision 1
""", formatter_class=argparse.RawTextHelpFormatter)
    return parser


def execute_generator(generator, arguments):
    # Run the generator that was selected in a clone
    # The clone protects the release repo state from mid change errors
    with log_prefix('[git-bloom-generate {0}]: '.format(generator.title)):
        git_clone = GitClone()
        try:
            with git_clone:
                ret = run_generator(generator, arguments)
            if ret > 0:
                return ret
            git_clone.commit()
            return ret
        except GeneratorError as err:
            return err.retcode


def main(sysargs=None):
    # Do argparse stuff
    parser = get_argument_parser()
    parser = add_global_arguments(parser)

    # List the generators
    generator_names = list_generators()

    # Create the generators
    generators = create_generators(generator_names)

    # Setup a subparser for each generator
    create_subparsers(parser, generators.values())

    # Inject into sys.argv
    if '--prefix' not in sys.argv:
        sys.argv.extend(['--prefix', 'release'])
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Set logging prefix
    push_log_prefix('[git-bloom-release]: ')

    # Run import upstream
    info("###")
    msg = "### Running 'git bloom-import-upstream --replace'... "
    info(msg)
    info("###")
    ret = iu_main(['--replace'])
    msg += "returned (" + str(ret) + ")"
    if ret > 0:
        error(msg)
        return 0
    if ret < 0:
        warning(msg)
    else:
        info(msg)
    print('\n')

    # Run release generator
    info("###")
    msg = "### Running 'git bloom-generate -y release --src upstream'... "
    info(msg)
    info("###")
    generator = generators['release']
    args.interactive = False
    release_args = copy.deepcopy(args)
    release_args.src = 'upstream'
    release_args.name = None
    ret = execute_generator(generator, release_args)
    msg += "returned (" + str(ret) + ")"
    if ret > 0:
        error(msg)
        return 0
    if ret < 0:
        warning(msg)
    else:
        info(msg)
    print('\n')

    # Run release generator
    info("###")
    msg = "### Running 'git bloom-generate -y release --src upstream'... "
    info(msg)
    info("###")
    generator = generators[args.generator]
    ret = execute_generator(generator, args)
    msg += "returned (" + str(ret) + ")"
    if ret > 0:
        error(msg)
        return 0
    if ret < 0:
        warning(msg)
    else:
        info(msg)
    print('\n')

    # Undo log prefix
    pop_log_prefix()

    # Notify the user of success and next action suggestions
    print('\n\n')
    warning("Tip: Check to ensure that the debian tags created have the same "
            "version as the upstream version you are releasing.")
    info(ansi('greenf') + ansi('boldon') + "Everything went as expected, "
         "you should check that the new tags match your expectations, and "
         "then push to the release repo with:" + ansi('reset'))
    info("  git push --all && git push --tags")
    return 0
