#!/usr/bin/env python
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

import sys

from argparse import ArgumentParser

from . import main as gendeb_main
from ... branch.branch import branch_packages

from ... git import get_branches
from ... git import track_branches
from ... util import maybe_continue
from ... logging import info, error


def get_argument_parser():
    parser = ArgumentParser(description="""\
Batch call to git-bloom-generate-debian.

Example: 'git-bloom-generate-debian-all groovy release'
""")
    parser.add_argument('rosdistro',
                        help="The ros distro")
    parser.add_argument('prefix',
                        help="Something like release will match release/a and "
                             "release/b (must be branches)")
    parser.add_argument('--debian-revision', '-r', dest='debian_revision',
                        help='Bump the changelog debian number.'
                             ' Please enter a monotonically increasing number '
                             'from the last upload.',
                        default=0)
    return parser


def main(sysargs=None):
    parser = get_argument_parser()
    args = parser.parse_args(sysargs)
    track_branches()
    branches = get_branches(local_only=True)
    targets = []
    for branch in branches:
        if branch.startswith(args.prefix):
            targets.append(branch)
    info("This will run git-bloom-generate-debian on these "
         "pacakges: " + str(targets))
    if not maybe_continue():
        error("Answered no to continue, exiting.")
        sys.exit(1)
    for index, target in enumerate(targets):
        # Branch first
        package = target[len('release/'):]
        new_target = 'debian/' + args.rosdistro
        info("Branching to debian prefix with: git-bloom-branch --src " + \
             target + " " + new_target + '/' + package)
        ret = branch_packages(target, new_target, True, False)
        ret = ret if ret is not None else 0
        if ret != 0:
            error("Command git-bloom-branch failed with return code: " + \
                  str(ret))
            sys.exit(ret)
        # Then generate
        gen_args = ['-t', new_target + '/' + package,
                    args.rosdistro, '--debian-revision',
                    str(args.debian_revision)]
        if index != 0:
            gen_args.append('--do-not-update-rosdep')
        info("Calling git-bloom-generate-debian-all " + " ".join(gen_args))
        gendeb_main(gen_args)
