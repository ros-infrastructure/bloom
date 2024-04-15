#!/usr/bin/python3

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
from collections import defaultdict
import os
from pathlib import Path
import sys

from catkin_pkg.package import parse_package
from catkin_pkg.package import parse_package_string
from rosdep2 import create_default_installer_context
from rosdep2.lookup import ResolutionError
from rosdep2.lookup import RosdepLookup
from rosdep2.meta import MetaDatabase
from rosdep2.rosdistrohelper import get_index
from rosdep2.rospack import is_ros_package
from rosdep2.rospkg_loader import DEFAULT_VIEW_KEY
from rosdistro import get_cached_distribution
from rpm import expandMacro


_BOOTSTRAP_PKGS = (
    'ament_cmake_core',
    'ament_package',
    'ros_workspace',
)


class DependencyResolver:

    def __init__(self):
        self._meta_db = MetaDatabase()
        self._lookup = RosdepLookup.create_from_rospkg()
        installer_context = create_default_installer_context()
        os_name, os_version = installer_context.get_os_name_and_version()
        self._view = self._lookup.get_rosdep_view(DEFAULT_VIEW_KEY)
        self._platform_args = [
            os_name, os_version, ('dnf', 'yum'), 'dnf',
        ]
        self._dist_pkgs = {}

    def _get_dist_pkgs(self, ros_distro):
        condition_context = self.get_condition_context(ros_distro)
        if ros_distro not in self._dist_pkgs:
            index = get_index()
            dist = get_cached_distribution(index, ros_distro)
            pkgs = []
            for pkg_name in dist.release_packages.keys():
                pkg_xml = dist.get_release_package_xml(pkg_name)
                if not pkg_xml:
                    continue
                pkg = parse_package_string(pkg_xml)
                for group_membership in pkg.member_of_groups:
                    group_membership.evaluate_condition(condition_context)
                pkgs.append(pkg)
            self._dist_pkgs[ros_distro] = pkgs
        return self._dist_pkgs[ros_distro]

    def get_condition_context(self, ros_distro):
        conditions = {
            'DISABLE_GROUPS_WORKAROUND': '1',
            'ROS_DISTRO': ros_distro,
        }

        ros_python_version = self._meta_db.get('ROS_PYTHON_VERSION')
        if ros_python_version and ros_python_version.get(ros_distro):
            conditions['ROS_PYTHON_VERSION'] = ros_python_version[ros_distro]

        ros_version = self._meta_db.get('ROS_VERSION')
        if ros_version and ros_version.get(ros_distro):
            conditions['ROS_VERSION'] = ros_version[ros_distro]

        return conditions

    def evaluate_conditions(self, pkg, ros_distro):
        condition_context = self.get_condition_context(ros_distro)
        pkg.evaluate_conditions(condition_context)

    def extract_group_members(self, pkg, ros_distro):
        for group_depend in pkg.group_depends:
            if group_depend.evaluated_condition is not True:
                continue
            group_depend.extract_group_members(
                self._get_dist_pkgs(ros_distro))

    def resolve_rosdep(self, dep_name):
        rosdep = self._view.lookup(dep_name)
        resolved_names = rosdep.get_rule_for_platform(*self._platform_args)[1]
        if isinstance(resolved_names, dict):
            resolved_names = resolved_names.get('packages', tuple())
        for resolved_name in resolved_names:
            resolved_name = expandMacro(resolved_name)
            yield resolved_name

    def resolve_dep(self, dep, ros_distro, ros_pkg_suffix=None):
        if isinstance(dep, str):
            name = dep
            constraints = set()
        else:
            name = dep.name
            if dep.evaluated_condition is not True:
                return

            constraints = set(self.enumerate_constraints(dep))

        if is_ros_package(self._view, name):
            yield (
                f"ros-{ros_distro}({name}){ros_pkg_suffix or ''}",
                constraints,
            )
        else:
            for resolved_name in self.resolve_rosdep(name):
                yield (resolved_name, constraints)

    @staticmethod
    def enumerate_constraints(dep):
        if dep.version_lt:
            yield f'< {dep.version_lt}'
        if dep.version_lte:
            yield f'<= {dep.version_lte}'
        if dep.version_eq:
            yield f'== {dep.version_eq}'
        if dep.version_gte:
            yield f'>= {dep.version_gte}'
        if dep.version_gt:
            yield f'>= {dep.version_gt}'

    @staticmethod
    def enumerate_implicit_buildtool_deps(pkg):
        implicit_deps = {
            'ament_python': (
                'python3-setuptools',
            ),
        }

        yield from implicit_deps.get(pkg.get_build_type(), tuple())

    @staticmethod
    def enumerate_msg_pkg_workaround_deps(pkg):
        for group in pkg.member_of_groups:
            if group.evaluated_condition is not True:
                continue
            if group.name == 'rosidl_interface_packages':
                break
        else:
            return ()

        for dep in pkg.buildtool_depends:
            if dep.evaluated_condition is not True:
                continue
            if dep.name == 'rosidl_default_generators':
                break
        else:
            return ()

        print(
            'WARNING: Injecting message package workaround dependency',
            file=sys.stderr)
        yield 'rosidl_default_generators'

    @classmethod
    def enumerate_rosdeps(
        cls, pkg, *, conflicts=False, obsoletes=False, requires=False,
        requires_check=False, requires_doc=False, requires_build=False,
        requires_devel=False, resolve_groups=False,
    ):
        if conflicts:
            yield from pkg.conflicts
        if obsoletes:
            yield from pkg.replaces
        if requires:
            yield from pkg.exec_depends
            if pkg.name not in _BOOTSTRAP_PKGS:
                yield 'ros_workspace'
            if resolve_groups:
                for group_depend in pkg.group_depends:
                    yield from group_depend.members
        if requires_check:
            yield from pkg.test_depends
        if requires_doc:
            yield from pkg.doc_depends
        if requires_build:
            yield from pkg.build_depends
            yield from pkg.buildtool_depends
            yield from cls.enumerate_implicit_buildtool_deps(pkg)
            if pkg.name not in _BOOTSTRAP_PKGS:
                yield 'ros_workspace'
            if resolve_groups:
                for group_depend in pkg.group_depends:
                    yield from group_depend.members
        if requires_devel:
            yield from pkg.build_export_depends
            yield from pkg.buildtool_export_depends
            if resolve_groups:
                for group_depend in pkg.group_depends:
                    yield from group_depend.members
            yield from cls.enumerate_msg_pkg_workaround_deps(pkg)


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    # required
    parser.add_argument('manifest_path')
    parser.add_argument('rpm_name')

    # outputs
    parser.add_argument('--conflicts', action='store_true')
    parser.add_argument('--obsoletes', action='store_true')
    parser.add_argument('--provides', action='store_true')
    parser.add_argument('--requires', action='store_true')
    parser.add_argument('--requires-doc', action='store_true')
    parser.add_argument('--requires-build', action='store_true')
    parser.add_argument('--requires-check', action='store_true')
    parser.add_argument('--requires-devel', action='store_true')
    parser.add_argument('--supplements', action='store_true')

    # options
    parser.add_argument('--resolve-groups', action='store_true')
    parser.add_argument('--skip-keys', nargs='*')

    # derivative/indirect
    parser.add_argument('--is-devel', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--is-runtime', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--ros-distro', default=None, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    # resolve derivative arguments
    rpm_name_split = args.rpm_name.split('-')
    if len(rpm_name_split) < 3 or rpm_name_split[0] != 'ros':
        print("Ignoring non-ROS package '{args.rpm_name}'", file=sys.stderr)
        sys.exit(0)
    args.ros_distro = rpm_name_split[1]
    args.is_devel = rpm_name_split[-1] == 'devel'
    args.is_runtime = rpm_name_split[-1] == 'runtime'

    return args


def main(argv=sys.argv[1:]):
    args = _parse_args(argv)
    skip_keys = set(args.skip_keys or ())

    if os.environ.get('ROS_DISTRO') not in (None, '', args.ros_distro):
        print(
            "Environment variable 'ROS_DISTRO' does not package name",
            file=sys.stderr)
        return 1

    os.environ['ROS_DISTRO'] = args.ros_distro

    resolver = DependencyResolver()

    pkg = parse_package(args.manifest_path)
    resolver.evaluate_conditions(pkg, args.ros_distro)
    if args.resolve_groups:
        resolver.extract_group_members(pkg, args.ros_distro)
    sysdeps = defaultdict(set)

    # Runtime deps
    if not args.is_devel:
        for dep in resolver.enumerate_rosdeps(
            pkg, conflicts=args.conflicts, obsoletes=args.obsoletes,
            requires=args.requires, resolve_groups=args.resolve_groups,
        ):
            if str(dep) in skip_keys:
                print(f'Skipping dependency: {dep}', file=sys.stderr)
                continue

            for sysdep, constraints in resolver.resolve_dep(
                dep, args.ros_distro,
            ):
                sysdeps[sysdep].update(constraints)

    # Devel deps
    if not args.is_runtime:
        for dep in resolver.enumerate_rosdeps(
            pkg, conflicts=args.conflicts, obsoletes=args.obsoletes,
            requires_devel=args.requires_devel,
            resolve_groups=args.resolve_groups,
        ):
            if str(dep) in skip_keys:
                print(f'Skipping dependency: {dep}', file=sys.stderr)
                continue

            for sysdep, constraints in resolver.resolve_dep(
                dep, args.ros_distro, '(devel)',
            ):
                sysdeps[sysdep].update(constraints)
        
    # Build deps
    for dep in resolver.enumerate_rosdeps(
        pkg, 
        requires_check=args.requires_check,
        requires_doc=args.requires_doc,
        requires_build=args.requires_build,
        resolve_groups=args.resolve_groups,
    ):
        if str(dep) in skip_keys:
            print(f'Skipping dependency: {dep}', file=sys.stderr)
            continue

        for sysdep, constraints in resolver.resolve_dep(
            dep, args.ros_distro, '(devel)',
        ):
            sysdeps[sysdep].update(constraints)

    if args.provides:
        if not args.is_devel:
            pkgprov = f'ros-{args.ros_distro}({pkg.name})'
            sysdeps[pkgprov].add(f'= {pkg.version}')

            for group in pkg.member_of_groups:
                if group.evaluated_condition is not True:
                    continue
                groupprov = f'ros-{args.ros_distro}({group})(member)'
                sysdeps.setdefault(groupprov, set())

        if not args.is_runtime:
            pkgprov = f'ros-{args.ros_distro}({pkg.name})(devel)'
            sysdeps[pkgprov].add(f'= {pkg.version}')

            for group in pkg.member_of_groups:
                if group.evaluated_condition is not True:
                    continue
                groupprov = f'ros-{args.ros_distro}({group})(devel)(member)'
                sysdeps.setdefault(groupprov, set())

    if args.supplements:
        if not args.is_devel:
            for group in pkg.member_of_groups:
                if group.evaluated_condition is not True:
                    continue
                groupprov = f'ros-{args.ros_distro}({group})(all)'
                sysdeps.setdefault(groupprov, set())

        if not args.is_runtime:
            for group in pkg.member_of_groups:
                if group.evaluated_condition is not True:
                    continue
                groupprov = f'ros-{args.ros_distro}({group})(devel)(all)'
                sysdeps.setdefault(groupprov, set())

    for sysdep, constraints in sorted(sysdeps.items()):
        if not constraints:
            print(sysdep)
        else:
            for constraint in sorted(constraints):
                print(f'{sysdep} {constraint}')


if __name__ == '__main__':
    sys.exit(main())
