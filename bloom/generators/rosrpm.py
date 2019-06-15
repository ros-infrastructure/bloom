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

from bloom.generators.common import default_fallback_resolver
from bloom.generators.common import generate_substitutions_from_package
from bloom.generators.common import sanitize_package_name

from bloom.generators.rpm import RpmGenerator
from bloom.generators.rpm import format_depends
from bloom.generators.rpm import format_description

from bloom.generators.rpm.generate_cmd import main as rpm_main
from bloom.generators.rpm.generate_cmd import prepare_arguments

from bloom.logging import info

from bloom.util import get_distro_list_prompt


class RosRpmGenerator(RpmGenerator):
    title = 'rosrpm'
    description = "Generates RPMs tailored for the given rosdistro"
    default_install_prefix = '/opt/ros/'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (%s, etc.)" % get_distro_list_prompt())
        return RpmGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        self.default_install_prefix += self.rosdistro
        ret = RpmGenerator.handle_arguments(self, args)
        return ret

    def summarize(self):
        ret = RpmGenerator.summarize(self)
        info("Releasing for rosdistro: " + self.rosdistro)
        return ret

    @staticmethod
    def missing_dep_resolver(key, peer_packages, os_name, os_version, ros_distro):
        if key in peer_packages:
            return [sanitize_package_name(rosify_package_name(key, ros_distro))]
        return default_fallback_resolver(key, peer_packages)

    @staticmethod
    def get_subs_hook(subs, package, rosdistro, releaser_history=None):
        subs = RpmGenerator.get_subs_hook(subs, package, releaser_history)
        subs['Package'] = rosify_package_name(subs['Package'], rosdistro)
        return subs

    def generate_branching_arguments(self, package, branch):
        package_branch = self.package_manager + '/' + self.rosdistro + '/' + package.name
        args = [[package_branch, branch, False]]
        n, r, b, ds = package.name, self.rosdistro, package_branch, self.distros
        args.extend([
            [self.package_manager + '/' + r + '/' + d + '/' + n, b, False] for d in ds
        ])
        return args

    def get_release_tag(self, data):
        return 'release/{0}/{1}/{2}-{3}'\
            .format(self.rosdistro, data['Name'], data['Version'], self.inc)


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


def get_subs(pkg, os_name, os_version, ros_distro):
    # No fallback_resolver provided because peer packages not considered.
    subs = generate_substitutions_from_package(
        pkg,
        os_name,
        os_version,
        ros_distro,
        format_description,
        format_depends,
        RosRpmGenerator.default_install_prefix + ros_distro,
    )
    subs = RosRpmGenerator.get_subs_hook(subs, pkg, ros_distro)
    return subs


def main(args=None):
    rpm_main(args, get_subs)


# This describes this command to the loader
description = dict(
    title='rosrpm',
    description="Generates ROS style RPM packaging files for a catkin package",
    main=main,
    prepare_arguments=prepare_arguments
)
