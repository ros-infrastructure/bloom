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
from subprocess import check_call, Popen, PIPE
import tempfile
import shutil

from export_bloom_from_src import get_path_and_pythonpath

from vcstools import VcsClient


class BloomSetUpstreamTestSetups(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.current_directory = os.getcwd()
        self.root_directory = tempfile.mkdtemp()
        # helpful when setting tearDown to pass
        self.directories = dict(setUp=self.root_directory)
        self.git_repo = os.path.join(self.root_directory, "git_repo")
        os.makedirs(self.git_repo)

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


class BloomSetUpstreamTest(BloomSetUpstreamTestSetups):

    def test_check_git_init(self):
        if not os.path.exists(self.git_repo):
            os.makedirs(self.git_repo)
        # Initialize the git repo
        check_call("git init", shell=True, cwd=self.git_repo, stdout=PIPE)

        # Detect freshly initialized repo, decline
        cmd = 'git-bloom-set-upstream https://github.com/ros/example.git git'
        p = Popen(cmd, shell=True, cwd=self.git_repo, stdin=PIPE, stdout=PIPE)
        expected_response = 'Upstream \x1b[1mhttps://github.com/ros/example' \
                            '.git\x1b[22m type: \x1b[1mgit\x1b[22m\nFreshly ' \
                            'initialized git repository detected.\nAn ' \
                            'initial empty commit is going to be made.\n' \
                            '\x1b[1mContinue \x1b[33m[Y/n]? \x1b[0m\x1b[31m' \
                            '\x1b[1mExiting.\x1b[0m\n'
        stdout_reponse, _ = p.communicate('n')
        assert expected_response == stdout_reponse, \
               str(len(expected_response)) + ' == ' + str(len(stdout_reponse))
        assert p.returncode == 1

        # Detect freshly initialized repo, accept
        p = Popen(cmd, shell=True, cwd=self.git_repo, stdin=PIPE, stdout=PIPE)
        expected_response = 'Upstream \x1b[1mhttps://github.com/ros/example' \
                            '.git\x1b[22m type: \x1b[1mgit\x1b[22m\nFreshly ' \
                            'initialized git repository detected.\nAn ' \
                            'initial empty commit is going to be made.\n' \
                            '\x1b[1mContinue \x1b[33m[Y/n]? \x1b[0mUpstream ' \
                            'successively set.\n'
        stdout_reponse, _ = p.communicate('y')
        assert expected_response == stdout_reponse
        assert p.returncode == 0

        # Should not detect freshly initialized repo
        p = Popen(cmd, shell=True, cwd=self.git_repo, stdin=PIPE, stdout=PIPE)
        expected_response = 'Upstream \x1b[1mhttps://github.com/ros/example' \
                            '.git\x1b[22m type: \x1b[1mgit\x1b[22m\nUpstream' \
                            ' successively set.\n'
        stdout_reponse, _ = p.communicate()
        assert expected_response == stdout_reponse
        assert p.returncode == 0

    def test_set_upstream(self):
        # Initialize the git repo
        check_call("git init", shell=True, cwd=self.git_repo, stdout=PIPE)

        # Run the program and ok the initial commit option
        cmd = 'git-bloom-set-upstream https://github.com/ros/example.git git'
        p = Popen(cmd, shell=True, cwd=self.git_repo, stdin=PIPE, stdout=PIPE)
        p.communicate('y')
        assert p.returncode == 0

        # Ensure the proper branch was created by checking out to it
        client = VcsClient('git', self.git_repo)
        client.update('bloom')

        # Ensure the bloom.conf file exists and that it is correct
        bloom_conf_path = os.path.join(self.git_repo, 'bloom.conf')
        assert os.path.exists(bloom_conf_path)
        expected_contents = '[bloom]\n\tupstream = https://github.' \
                            'com/ros/example.git\n\tupstreamtype = git' \
                            '\n\tupstreambranch = \n'
        assert expected_contents == open(bloom_conf_path, 'r').read(), \
               open(bloom_conf_path, 'r').read()
