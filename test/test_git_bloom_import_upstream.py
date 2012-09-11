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

from __future__ import unicode_literals

import os
import unittest
from subprocess import Popen, PIPE
import tempfile
import shutil

from bloom.util import check_output
from bloom.util import execute_command
from export_bloom_from_src import get_path_and_pythonpath


class BloomImportUpstreamTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.current_directory = os.getcwd()
        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.git_repo = os.path.join(self.root_directory, "git_repo")

        # Setup environment for running commands
        path, ppath = get_path_and_pythonpath()
        os.putenv('PATH', path)
        os.putenv('PYTHONPATH', ppath)

    @classmethod
    def tearDownClass(self):
        for d in self.directories:
            shutil.rmtree(self.directories[d])
        os.chdir(self.current_directory)

    def tearDown(self):
        os.chdir(self.current_directory)

gself = None


class BloomImportUpstreamTest(BloomImportUpstreamTestSetups):

    def test_convert_catkin_to_bloom(self):
        os.makedirs(self.git_repo)
        # Setup the repo
        execute_command('git init .', cwd=self.git_repo)
        f = open(os.path.join(self.git_repo, 'catkin.conf'), 'w+')
        f.write('[catkin]\n\tupstream = git://github.com/ros/langs.git'
                '\n\tupstreamtype = git\n')
        f.close()
        execute_command('git add ./*', cwd=self.git_repo)
        execute_command('git commit -m "Init"', cwd=self.git_repo)
        execute_command('git branch catkin', cwd=self.git_repo)
        # Execute the converter
        from bloom.import_upstream import convert_catkin_to_bloom
        convert_catkin_to_bloom(self.git_repo)
        # Assert correct behavior
        output = check_output('git branch --no-color', shell=True,
                              cwd=self.git_repo)
        assert output.count('catkin') == 0
        assert output.count('* bloom') == 1, output
        expected_str = '[bloom]\n\tupstream = git://github.com/ros/langs.git' \
                       '\n\tupstreamtype = git\n'
        conf_path = os.path.join(self.git_repo, 'bloom.conf')
        assert os.path.exists(conf_path)
        assert open(conf_path, 'r').read() == expected_str
        from shutil import rmtree
        rmtree(self.git_repo)

    def test_check_for_bloom(self):
        os.makedirs(self.git_repo)
        # Setup the repo
        execute_command('git init .', cwd=self.git_repo)
        f = open(os.path.join(self.git_repo, 'catkin.conf'), 'w+')
        f.write('[catkin]\n\tupstream = git://github.com/ros/langs.git'
                '\n\tupstreamtype = git\n')
        f.close()
        execute_command('git add catkin.conf', cwd=self.git_repo)
        execute_command('git commit -m "Init"', cwd=self.git_repo)
        execute_command('git branch catkin', cwd=self.git_repo)
        # Take over the subroutines
        import bloom.import_upstream
        global gself
        gself = self
        gself.not_a_bloom_release_repo = False

        def mock_not_a_bloom_release_repo():
            global gself
            gself.not_a_bloom_release_repo = True

        bloom.import_upstream.not_a_bloom_release_repo = \
            mock_not_a_bloom_release_repo

        # Execute the check
        from bloom.import_upstream import check_for_bloom
        check_for_bloom(self.git_repo)
        assert gself.not_a_bloom_release_repo == False
        check_for_bloom(self.git_repo)
        assert gself.not_a_bloom_release_repo == False

        # Remove the bloom repo
        execute_command('git checkout master', cwd=self.git_repo)
        execute_command('git branch -D bloom', cwd=self.git_repo)

        check_for_bloom(self.git_repo)
        assert gself.not_a_bloom_release_repo == True
        from shutil import rmtree
        rmtree(self.git_repo)

    def test_parse_bloom_conf(self):
        os.makedirs(self.git_repo)
        # Setup the repo
        execute_command('git init .', cwd=self.git_repo)
        f = open(os.path.join(self.git_repo, 'bloom.conf'), 'w+')
        f.write('[bloom]\n\tupstream = git://github.com/ros/langs.git'
                '\n\tupstreamtype = git\n')
        f.close()
        execute_command('git add bloom.conf', cwd=self.git_repo)
        execute_command('git commit -m "Init"', cwd=self.git_repo)
        execute_command('git branch bloom', cwd=self.git_repo)
        execute_command('git checkout bloom', cwd=self.git_repo)
        # Parse the config file
        from bloom.import_upstream import parse_bloom_conf
        config = parse_bloom_conf(self.git_repo)
        # Assert correct behavior
        assert config[0] == 'git://github.com/ros/langs.git', config
        assert config[1] == 'git', config
        assert config[2] == '', config
        # Clean up
        from shutil import rmtree
        rmtree(self.git_repo)

    def test_get_tarball_name(self):
        pkg_name = 'cpp_common'
        full_version = '1.2.3'
        from bloom.import_upstream import get_tarball_name
        tarball_name = get_tarball_name(pkg_name, full_version)
        assert tarball_name == 'cpp-common-1.2.3', tarball_name

    def test_create_initial_upstream_branch(self):
        os.makedirs(self.git_repo)
        # Setup the repo
        execute_command('git init .', cwd=self.git_repo)
        # Execute
        from bloom.import_upstream import create_initial_upstream_branch
        cmd = 'git branch --no-color'
        out = check_output(cmd, shell=True, cwd=self.git_repo)
        assert out.count('upstream') == 0
        create_initial_upstream_branch(self.git_repo)
        out = check_output(cmd, shell=True, cwd=self.git_repo)
        assert out.count('upstream') == 1
        # Clean up
        from shutil import rmtree
        rmtree(self.git_repo)

    def test_import_upstream(self):
        os.makedirs(self.git_repo)
        # Setup upstream repo
        src = os.path.join(self.root_directory, "upstream_repo")
        os.makedirs(src)
        try:
            execute_command('git init .', cwd=src)
            f = open(os.path.join(src, 'stack.xml'), 'w+')
            f.write("""\
<stack>
  <name>langs</name>
  <version>0.4.0</version>
  <description>Meta package modeling the run-time...</description>
  <author>The ROS Ecosystem</author>
  <maintainer email="dthomas@willowgarage.com">Dirk Thomas</maintainer>
  <license>BSD</license>
  <copyright>Willow Garage</copyright>
  <url>http://www.ros.org</url>

  <build_depends>catkin</build_depends>

  <depends>catkin</depends>
  <!-- required for messages generated by gencpp -->
  <depends>roscpp_core</depends>

  <!-- workaround to provide the generators to dry downstream packages -->
  <depends>langs-dev</depends>
</stack>
    """)
            f.close()
            execute_command('git add stack.xml', cwd=src)
            execute_command('git commit -m "stack"', cwd=src)
            execute_command('git tag 0.4.0', cwd=src)
            # Setup the gbp repo
            execute_command('git init .', cwd=self.git_repo)
            cmd = 'git-bloom-set-upstream file://{0} git'.format(src)
            p = Popen(cmd, shell=True, cwd=self.git_repo,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate('y')
            # Test the import of upstream
            cmd = 'git-bloom-import-upstream'
            p = Popen(cmd, shell=True, cwd=self.git_repo,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            assert p.returncode == 0
            assert out.count("I'm happy") > 0
            p = Popen(cmd, shell=True, cwd=self.git_repo,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            assert p.returncode == 1
            assert out.count("if you want to replace") > 0
            cmd += ' --replace'
            p = Popen(cmd, shell=True, cwd=self.git_repo,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            assert p.returncode == 0
            assert out.count("Removing conflicting tag before continuing") > 0
        finally:
            # Clean up
            from shutil import rmtree
            rmtree(self.git_repo)
            rmtree(src)
