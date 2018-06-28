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

from bloom.generators.debian.generator import sanitize_package_name

from bloom.generators.debian import DebianGenerator
from bloom.generators.debian.generator import generate_substitutions_from_package
from bloom.generators.debian.generate_cmd import main as debian_main
from bloom.generators.debian.generate_cmd import prepare_arguments

from bloom.logging import info

from bloom.util import get_distro_list_prompt


class RosDebianGenerator(DebianGenerator):
    title = 'rosdebian'
    description = "Generates debians tailored for the given rosdistro"
    default_install_prefix = '/opt/ros/'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('rosdistro', help="ROS distro to target (%s, etc.)" % get_distro_list_prompt())
        return DebianGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.rosdistro = args.rosdistro
        self.default_install_prefix += self.rosdistro
        ret = DebianGenerator.handle_arguments(self, args)
        return ret

    def summarize(self):
        ret = DebianGenerator.summarize(self)
        info("Releasing for rosdistro: " + self.rosdistro)
        return ret

    def get_subs(self, package, debian_distro, releaser_history, native=False):
        def fallback_resolver(key, peer_packages, rosdistro=self.rosdistro):
            if key in peer_packages:
                return [sanitize_package_name(rosify_package_name(key, rosdistro))]
            return default_fallback_resolver(key, peer_packages)
        subs = generate_substitutions_from_package(
            package,
            self.os_name,
            debian_distro,
            self.rosdistro,
            self.install_prefix,
            self.debian_inc,
            [p.name for p in self.packages.values()],
            releaser_history=releaser_history,
            fallback_resolver=fallback_resolver
        )
        subs['Package'] = rosify_package_name(subs['Package'], self.rosdistro)

        # ROS 2 specific bloom extensions.
        # TODO(nuclearsandwich) explore other ways to enable these extensions, reduce their necessity,
        # or make them configurable rather than relying on distro names.
        if self.rosdistro in ['r2b2', 'r2b3', 'ardent', 'bouncy']:
            # Add ros-workspace package as a dependency to any package other
            # than ros_workspace and its dependencies.
            if package.name not in ['ament_cmake_core', 'ament_package', 'ros_workspace']:
                workspace_pkg_name = rosify_package_name('ros-workspace', self.rosdistro)
                subs['BuildDepends'].append(workspace_pkg_name)
                subs['Depends'].append(workspace_pkg_name)

            # Add packages necessary to build vendor typesupport for rosidl_interface_packages to their
            # build dependencies.
            if self.rosdistro in ['bouncy'] and \
                    'rosidl_interface_packages' in [p.name for p in package.member_of_groups]:
                ROS2_VENDOR_TYPESUPPORT_DEPENDENCIES = [
                    'rmw-connext-cpp',
                    'rmw-fastrtps-cpp',
                    'rmw-implementation',
                    'rmw-opensplice-cpp',
                    'rosidl-typesupport-connext-c',
                    'rosidl-typesupport-connext-cpp',
                    'rosidl-typesupport-opensplice-c',
                    'rosidl-typesupport-opensplice-cpp',
                ]

                subs['BuildDepends'] += [
                    rosify_package_name(name, self.rosdistro) for name in ROS2_VENDOR_TYPESUPPORT_DEPENDENCIES]
        return subs

    def generate_branching_arguments(self, package, branch):
        deb_branch = 'debian/' + self.rosdistro + '/' + package.name
        args = [[deb_branch, branch, False]]
        n, r, b, ds = package.name, self.rosdistro, deb_branch, self.distros
        args.extend([
            ['debian/' + r + '/' + d + '/' + n, b, False] for d in ds
        ])
        return args

    def get_release_tag(self, data):
        return 'release/{0}/{1}/{2}-{3}'\
            .format(self.rosdistro, data['Name'], data['Version'], self.debian_inc)


def rosify_package_name(name, rosdistro):
    return 'ros-{0}-{1}'.format(rosdistro, name)


def get_subs(pkg, os_name, os_version, ros_distro, native):
    # No fallback_resolver provided because peer packages not considered.
    subs = generate_substitutions_from_package(
        pkg,
        os_name,
        os_version,
        ros_distro,
        RosDebianGenerator.default_install_prefix + ros_distro,
        native=native
    )
    subs['Package'] = rosify_package_name(subs['Package'], ros_distro)
    return subs


def main(args=None):
    debian_main(args, get_subs)


# This describes this command to the loader
description = dict(
    title='rosdebian',
    description="Generates ROS style debian packaging files for a catkin package",
    main=main,
    prepare_arguments=prepare_arguments
)
