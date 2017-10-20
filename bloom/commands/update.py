# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
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

import argparse
import atexit
import bloom
import json
import os
import sys

try:
    # Python2
    from urllib2 import urlopen
except ImportError:
    # Python3
    from urllib.request import urlopen

from bloom.logging import warning

from bloom.util import add_global_arguments
from bloom.util import handle_global_arguments

from pkg_resources import parse_version
from threading import Lock

_updater_running = False
_updater_lock = Lock()

UPDATE_MSG = """\
This version of bloom is '{current}', but the newest available version is '{newest}'. Please update.\
"""


def start_updater():
    global _updater_running, _updater_lock
    with _updater_lock:
        if _updater_running:
            return
        _updater_running = True
        import subprocess
        subprocess.Popen('bloom-update --quiet', shell=True)


@atexit.register
def check_for_updates():
    if sys.argv[0].endswith('bloom-update'):
        return
    user_bloom = os.path.join(os.path.expanduser('~'), '.bloom')
    if os.path.exists(user_bloom):
        with open(user_bloom, 'r') as f:
            raw = f.read()
        if not raw:
            return
        version_dict = json.loads(raw)
        os.remove(user_bloom)  # Remove only on successful parse
        if type(version_dict) == dict and len(version_dict) == 2 and version_dict['current'] == bloom.__version__:
            warning(UPDATE_MSG.format(**version_dict))


def get_argument_parser():
    parser = argparse.ArgumentParser(description="Checks for updates")
    add_global_arguments(parser)
    return parser

_quiet = False


def info(msg):
    global _quiet
    if not _quiet:
        print(msg)


def fetch_update(user_bloom):
    if os.path.exists(user_bloom):
        return
    open(user_bloom, 'w').close()  # Touch the file
    resp = urlopen('https://pypi.python.org/pypi/bloom/json')
    if sys.version_info.major == 2:
        pypi_result = json.loads(resp.read())
    else:
        pypi_result = json.loads(resp.read().decode('utf-8'))

    newest_version = pypi_result['info']['version']
    current_version = bloom.__version__
    if newest_version and bloom.__version__ != 'unset':
        if parse_version(bloom.__version__) < parse_version(newest_version):
            version_dict = {
                'current': str(current_version),
                'newest': str(newest_version)
            }
            with open(user_bloom, 'w') as f:
                f.write(json.dumps(version_dict))
            info(UPDATE_MSG.format(**version_dict))
            if _quiet:
                return
        else:
            info("Bloom is up-to-date!")
    else:
        info("Cannot determine newest version of bloom.")
    os.remove(user_bloom)


def main(sysargs=None):
    global _quiet
    parser = get_argument_parser()
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)
    _quiet = args.quiet

    user_bloom = os.path.join(os.path.expanduser('~'), '.bloom')
    try:
        fetch_update(user_bloom)
    except Exception as e:
        if not _quiet:
            print('Error fetching latest version: ' + str(e), file=sys.stderr)
        if os.path.exists(user_bloom):
            os.remove(user_bloom)
