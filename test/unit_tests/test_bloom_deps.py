# Software License Agreement (BSD License)
#
# Copyright (c) 2026, Open Source Robotics Foundation, Inc.
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

import importlib.util
import os
import sys
import unittest
from unittest.mock import patch

from catkin_pkg.package import Dependency
from catkin_pkg.package import parse_package

"""This will be imported during setUpModule."""
bloom_deps = None


def setUpModule():
    """
    Load the bloom-deps.py script as a Python module for testing.

    The script is loaded dynamically to allow testing its internal functions
    and classes. This is done in setUpModule to ensure it is only loaded
    once for all tests in this module, and to allow skipping the tests
    if the required 'rpm' module is not available.
    """
    if not importlib.util.find_spec('rpm'):
        raise unittest.SkipTest('rpm module is not available')

    global bloom_deps
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'etc', 'rpm', 'bloom-deps.py')
    spec = importlib.util.spec_from_file_location("bloom_deps", path)
    bloom_deps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bloom_deps)


class TestBloomDeps(unittest.TestCase):

    @property
    def package_xml_path(self):
        return os.path.join(
            os.path.dirname(__file__),
            'test_bloom_deps_data',
            self.id().split('.')[-1],
            'package.xml',
        )

    def test_parse_args(self):
        # Basic
        argv = ['package.xml', 'ros-rolling-my-pkg']
        args = bloom_deps._parse_args(argv)
        self.assertEqual(args.manifest_path, 'package.xml')
        self.assertEqual(args.rpm_name, 'ros-rolling-my-pkg')
        self.assertEqual(args.ros_distro, 'rolling')
        self.assertFalse(args.is_devel)
        self.assertFalse(args.is_runtime)

        # Devel
        argv = ['package.xml', 'ros-foxy-my-pkg-devel']
        args = bloom_deps._parse_args(argv)
        self.assertEqual(args.ros_distro, 'foxy')
        self.assertTrue(args.is_devel)
        self.assertFalse(args.is_runtime)

        # Runtime
        argv = ['package.xml', 'ros-humble-my-pkg-runtime']
        args = bloom_deps._parse_args(argv)
        self.assertEqual(args.ros_distro, 'humble')
        self.assertFalse(args.is_devel)
        self.assertTrue(args.is_runtime)

    def test_enumerate_constraints(self):
        dep = Dependency('my_pkg', version_lt='2.0', version_eq='1.0', version_gt='0.5')

        constraints = bloom_deps.DependencyResolver.enumerate_constraints(dep)
        self.assertCountEqual(constraints, ('< 2.0', '== 1.0', '>= 0.5'))

    def test_implicit_deps_ament_python(self):
        pkg = parse_package(self.package_xml_path)
        deps = bloom_deps.DependencyResolver.enumerate_implicit_buildtool_deps(pkg)
        self.assertCountEqual(deps, ('python3-setuptools',))

    def test_implicit_deps_ament_cmake(self):
        pkg = parse_package(self.package_xml_path)
        deps = bloom_deps.DependencyResolver.enumerate_implicit_buildtool_deps(pkg)
        self.assertCountEqual(deps, ())

    def test_enumerate_rosdeps(self):
        pkg = parse_package(self.package_xml_path)

        # conflicts
        deps = bloom_deps.DependencyResolver.enumerate_rosdeps(pkg, conflicts=True)
        dep_names = (getattr(d, 'name', d) for d in deps)
        self.assertCountEqual(dep_names, ('conflict_a',))

        # requires
        deps = bloom_deps.DependencyResolver.enumerate_rosdeps(pkg, requires=True)
        dep_names = (getattr(d, 'name', d) for d in deps)
        self.assertCountEqual(dep_names, ('exec_a', 'ros_workspace'))

        # requires_build
        deps = bloom_deps.DependencyResolver.enumerate_rosdeps(pkg, requires_build=True)
        dep_names = (getattr(d, 'name', d) for d in deps)
        self.assertCountEqual(dep_names, ('build_a', 'buildtool_a', 'ros_workspace'))

        # requires_devel
        deps = bloom_deps.DependencyResolver.enumerate_rosdeps(pkg, requires_devel=True)
        dep_names = (getattr(d, 'name', d) for d in deps)
        self.assertCountEqual(dep_names, ('export_a', 'tool_export_a'))

    def test_resolve_dep_string(self):
        resolver = bloom_deps.DependencyResolver()

        with patch.object(resolver, 'resolve_rosdep', return_value=['system_pkg_1', 'system_pkg_2']):
            with patch.object(bloom_deps, 'is_ros_package', return_value=True):
                res = list(resolver.resolve_dep('my_dep', 'rolling'))
                self.assertEqual(res, [('ros-rolling(my_dep)', set())])

            with patch.object(bloom_deps, 'is_ros_package', return_value=False):
                res = list(resolver.resolve_dep('my_dep', 'rolling'))
                self.assertEqual(res, [('system_pkg_1', set()), ('system_pkg_2', set())])

    def test_resolve_dep_object(self):
        resolver = bloom_deps.DependencyResolver()

        dep = Dependency('my_dep', version_eq='1.0')
        dep.evaluated_condition = True

        with patch.object(bloom_deps, 'is_ros_package', return_value=True):
            res = list(resolver.resolve_dep(dep, 'rolling', '(devel)'))
            self.assertEqual(res, [('ros-rolling(my_dep)(devel)', {'== 1.0'})])

            # Test evaluated_condition False
            dep.evaluated_condition = False
            res = list(resolver.resolve_dep(dep, 'rolling'))
            self.assertEqual(res, [])

    def test_get_condition_context(self):
        resolver = bloom_deps.DependencyResolver()
        with patch.object(resolver._meta_db, 'get', side_effect=lambda k: {
            'ROS_PYTHON_VERSION': {'rolling': '3'},
            'ROS_VERSION': {'rolling': '2'},
        }.get(k)):
            ctx = resolver.get_condition_context('rolling')
            self.assertDictEqual(ctx, {
                'DISABLE_GROUPS_WORKAROUND': '1',
                'ROS_DISTRO': 'rolling',
                'ROS_PYTHON_VERSION': '3',
                'ROS_VERSION': '2',
            })

    def test_enumerate_msg_pkg_workaround_deps(self):
        pkg = parse_package(self.package_xml_path)
        resolver = bloom_deps.DependencyResolver()
        resolver.evaluate_conditions(pkg, 'rolling')
        deps = bloom_deps.DependencyResolver.enumerate_msg_pkg_workaround_deps(pkg)
        self.assertCountEqual(deps, ('rosidl_default_generators',))
