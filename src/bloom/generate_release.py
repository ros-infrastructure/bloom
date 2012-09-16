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


def get_argument_parser():
    """Creates and returns the argument parser"""
    import argparse
    parser = argparse.ArgumentParser(description="""\
Creates or updates a git-buildpackage repository using a catkin project.\
""")
    parser.add_argument('--working', help='A scratch build path. Defaults to '
                                          'a temporary directory.')
    parser.add_argument('--debian-revision', dest='debian_revision',
                        help='Bump the changelog debian number.'
                             ' Please enter a monotonically increasing number '
                             'from the last upload.',
                        default=0)
    parser.add_argument('--install-prefix', dest='install_prefix',
                        help='The installation prefix')
    parser.add_argument('--distros', nargs='+',
                        help='A list of debian distros.',
                        default=[])

    #ros specific stuff.
    parser.add_argument('rosdistro',
                        help="The ros distro. Like 'electric', 'fuerte', "
                             "or 'groovy'. If this is set to backports then "
                             "the resulting packages will not have the "
                             "ros-<rosdistro>- prefix.")
    return parser


def main():
    pass
