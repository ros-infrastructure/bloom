# Software License Agreement (BSD License)
#
# Copyright (c) 2024, Open Source Robotics Foundation, Inc.
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

from bloom.generators.dynrpm import DynRpmGenerator
from bloom.generators.dynrpm.generator import generate_substitutions_from_package
from bloom.generators.dynrpm.generate_cmd import main as rpm_main
from bloom.generators.dynrpm.generate_cmd import prepare_arguments

from bloom.logging import info

from bloom.rosdistro_api import get_index
from bloom.rosdistro_api import get_non_eol_distros_prompt


class RosDynRpmGenerator(DynRpmGenerator):
    title = 'rosdynrpm'
    description = "Generates dynamic RPMs tailored for the given rosdistro"
    default_install_prefix = '/opt/ros'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (%s, etc.)" % get_non_eol_distros_prompt())
        return DynRpmGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        self.default_install_prefix += '/' + self.rosdistro
        ret = DynRpmGenerator.handle_arguments(self, args)
        return ret

    def summarize(self):
        ret = DynRpmGenerator.summarize(self)
        info("Releasing for rosdistro: " + self.rosdistro)
        return ret

    def get_subs(self, package, releaser_history):
        subs = generate_substitutions_from_package(
            package,
            self.rosdistro,
            self.install_prefix,
            self.rpm_inc,
            [p.name for p in self.packages.values()],
            releaser_history=releaser_history
        )
        subs['Rosdistro'] = self.rosdistro
        subs['Package'] = rosify_package_name(subs['Package'], self.rosdistro)

        return subs

    def generate_branching_arguments(self, package, branch):
        return [
            ['dynrpm/' + self.rosdistro + '/' + package.name, branch, False],
        ]

    def get_release_tag(self, data):
        return 'release/{0}/{1}/{2}-{3}'\
            .format(self.rosdistro, data['Name'], data['Version'], self.rpm_inc)


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


# This describes this command to the loader
description = dict(
    title='rosdynrpm',
    description="Generates ROS style dynamic RPM packaging files for a catkin package",
    main=rpm_main,
    prepare_arguments=prepare_arguments
)
