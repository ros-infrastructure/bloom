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

from .. branch.branch import branch_packages
from .. generators.debian.main_all import main as gendeb_all_main

from .. util import add_global_arguments
from .. util import handle_global_arguments
from .. logging import ansi
from .. logging import info
from .. logging import error
from .. logging import push_log_prefix
from .. logging import pop_log_prefix


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Preforms the standard release procedure after a call to bloom-import-upstream.

This script makes a few assumptions about your release repository, such that
the commands you would call would be:

    git-bloom-branch --interactive --src upstream release
    git-bloom-generate-debian-all <rosdistro> release \
--debian-revision <debian_revision>

You will be prompted at the beginning of each of those commands.

Example:

    git-bloom-release groovy --debian-revision 1
""", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('rosdistro',
                        help="The ros distro")
    parser.add_argument('--debian-revision', '-r', dest='debian_revision',
                        help='Bump the changelog debian number.\n'
                             'Please enter a monotonically increasing \n'
                             'number from the last upload.',
                        default=0)
    return parser


def release_main(sysargs=None):
    # Do argparse stuff
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    # Set logging prefix
    push_log_prefix('[git-bloom-release]: ')

    # Run git-bloom-branch
    info("Running git-bloom-branch --src upstream release --interactive")
    ret = branch_packages('upstream', 'release', True, True)
    ret = ret if ret is not None else 0
    # If successful, run git-bloom-generate-debian-all
    if ret == 0:
        # Setup arguments for the debian generator
        gda_args = []
        if args.debian_revision is not None:
            gda_args.append('--debian-revision')
            gda_args.append(str(args.debian_revision))
        gda_args.extend([args.rosdistro, 'release'])
        # Execute debian generator
        info("Running git-bloom-generate-debian-all " + " ".join(gda_args))
        ret = gendeb_all_main(gda_args)
        ret = ret if ret is not None else 0
        # Handle failure
        if ret != 0:
            error("Command git-bloom-generate-debian-all failed with "
                  "retcode: " + str(ret))
            return 0
    else:
        error("Command git-bloom-branch failed with return code: " + str(ret))
        return ret

    # Close out logging prefix
    pop_log_prefix()

    # Notify the user of success and next action suggestions
    print('\n\n')
    info(ansi('greenf') + ansi('boldon') + "Everything went as expected, "
         "you should check that the new tags match your expectations, and "
         "then push to the gbp repo with:" + ansi('reset'))
    info("  git push --force --all && git push --tags")
    return 0
