# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Open Source Robotics Foundation, Inc.
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
#  * Neither the name of Open Source Robotics Foundation, Inc. nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
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


def prepare_arguments(parser):
    add = parser.add_argument
    add('package_path', nargs='?', help="path to or containing the package.xml of a package")
    action = parser.add_mutually_exclusive_group(required=False)
    add = action.add_argument
    add('--place-template-files', action='store_true', help="places debian/* template files only")
    add('--process-template-files', action='store_true', help="processes templates in debian/* only")
    return parser


def place_template_files():
    pass


def process_template_files():
    pass


def main(args=None):
    if args is None:
        package_path = os.getcwd()
        do_place_template_files = True
        do_process_template_files = True
    else:
        package_path = args.package_path or os.getcwd()
        do_place_template_files = args.place_template_files
        do_process_template_files = args.process_template_files
        # If neither, do both
        if not do_place_template_files and not do_process_template_files:
            do_place_template_files = True
            do_process_template_files = True

    if do_place_template_files:
        # Place template files
        place_template_files()
    if do_process_template_files:
        # Just process existing template files
        process_template_files()

    print(package_path)

# This describes this command to the loader
description = dict(
    title='debian',
    description="Generates debian packaging files for a catkin package",
    main=main,
    prepare_arguments=prepare_arguments
)
