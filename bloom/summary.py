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

"""Implements the summarizing of actions on the master branch.
"""

from __future__ import print_function

import atexit
import os

from bloom.logging import _get_summary_file_path

from bloom.git import inbranch
from bloom.git import get_root
from bloom.git import has_changes

from bloom.util import execute_command

_summary_file = None


def commit_summary():
    global _summary_file
    if get_root() is None:
        return
    if _summary_file is None:
        return
    if not os.path.exists(_summary_file.name):
        return
    try:
        with inbranch('master'):
            readme_name = 'README.md'
            readme = ''
            if os.path.isfile(readme_name):
                with open(readme_name, 'r') as f:
                    readme = f.read()
            _summary_file.close()
            with open(_summary_file.name, 'r') as f:
                readme = f.read() + "\n\n" + readme
            with open(readme_name, 'w') as f:
                f.write(readme)
            execute_command('git add ' + readme_name)
            if has_changes():
                execute_command('git commit -m "Updating README.md"')
    finally:
        if _summary_file is not None:
            _summary_file.close()
            if os.path.exists(_summary_file.name):
                os.remove(_summary_file.name)


def get_summary_file():
    global _summary_file
    if _summary_file is None:
        _summary_file = open(_get_summary_file_path(), 'a')
        atexit.register(commit_summary)
    return _summary_file
