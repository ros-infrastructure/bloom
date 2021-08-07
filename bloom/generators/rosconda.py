# Software License Agreement (BSD License)
#
# Copyright (c) 2021, Open Source Robotics Foundation, Inc.
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

from bloom.generators.conda.generator import sanitize_package_name

from bloom.generators.conda import CondaGenerator
from bloom.generators.conda.generator import generate_substitutions_from_package
from bloom.generators.conda.generate_cmd import main as conda_main
from bloom.generators.conda.generate_cmd import prepare_arguments

from bloom.logging import info

from bloom.rosdistro_api import get_index

from bloom.util import get_distro_list_prompt


class RosCondaGenerator(CondaGenerator):
    title = 'rosconda'
    description = "Generates conda recipes tailored for the given rosdistro"

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (%s, etc.)" % get_distro_list_prompt())
        return CondaGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        ret = CondaGenerator.handle_arguments(self, args)
        return ret

    def summarize(self):
        ret = CondaGenerator.summarize(self)
        info("Releasing for rosdistro: " + self.rosdistro)
        return ret

    def get_subs(self, package, releaser_history):
        def fallback_resolver(key, peer_packages, rosdistro=self.rosdistro):
            if key in peer_packages:
                return [sanitize_package_name(rosify_package_name(key, rosdistro))]
            return default_fallback_resolver(key, peer_packages)
        subs = generate_substitutions_from_package(
            package,
            self.rosdistro,
            self.conda_inc,
            [p.name for p in self.packages.values()],
            releaser_history=releaser_history,
            fallback_resolver=fallback_resolver,
            skip_keys=self.skip_keys
        )
        subs['Rosdistro'] = self.rosdistro
        subs['Package'] = rosify_package_name(subs['Package'], self.rosdistro)

        # Virtual packages
        subs['Provides'] += [
            '%%{name}-%s = %%{version}-%%{release}' % subpackage for subpackage in [
                'devel', 'doc', 'runtime']]

        # Group membership
        subs['Provides'].extend(
            sanitize_package_name(rosify_package_name(g.name, self.rosdistro)) +
            '(member)' for g in package.member_of_groups)
        subs['Supplements'].extend(
            sanitize_package_name(rosify_package_name(g.name, self.rosdistro)) +
            '(all)' for g in package.member_of_groups)

        # ROS 2 specific bloom extensions.
        ros2_distros = [
            name for name, values in get_index().distributions.items()
            if values.get('distribution_type') == 'ros2']
        if self.rosdistro in ros2_distros:
            # Add ros-workspace package as a dependency to any package other
            # than ros_workspace and its dependencies.
            if package.name not in ['ament_cmake_core', 'ament_package', 'ros_workspace']:
                workspace_pkg_name = rosify_package_name('ros-workspace', self.rosdistro)
                subs['BuildDepends'].append(workspace_pkg_name)
                subs['Depends'].append(workspace_pkg_name)

            # Add packages necessary to build vendor typesupport for rosidl_interface_packages to their
            # build dependencies.
            if self.rosdistro in ros2_distros and \
                    'rosidl_interface_packages' in [p.name for p in package.member_of_groups]:
                ROS2_VENDOR_TYPESUPPORT_DEPENDENCIES = [
                    'rosidl-typesupport-fastrtps-c',
                    'rosidl-typesupport-fastrtps-cpp',
                ]

                subs['BuildDepends'] += [
                    rosify_package_name(name, self.rosdistro) for name in ROS2_VENDOR_TYPESUPPORT_DEPENDENCIES]
        return subs

    def generate_branching_arguments(self, package, branch):
        conda_branch = 'conda/' + self.rosdistro + '/' + package.name
        args = [[conda_branch, branch, False]]
        n, r, b, ds = package.name, self.rosdistro, conda_branch, self.distros
        args.extend([
            ['conda/' + r + '/' + d + '/' + n, b, False] for d in ds
        ])
        return args

    def get_release_tag(self, data):
        return 'release/{0}/{1}/{2}-{3}'\
            .format(self.rosdistro, data['Name'], data['Version'], self.conda_inc)


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


def get_subs(pkg, ros_distro):
    # No fallback_resolver provided because peer packages not considered.
    subs = generate_substitutions_from_package(
        pkg,
        ros_distro
    )
    subs['Package'] = rosify_package_name(subs['Package'], ros_distro)
    return subs


def main(args=None):
    conda_main(args, get_subs)


# This describes this command to the loader
description = dict(
    title='rosconda',
    description="Generates ROS style Conda recipes for a catkin package",
    main=main,
    prepare_arguments=prepare_arguments
)
