# Software License Agreement (BSD License)
#
# Copyright (c) 2022, Open Source Robotics Foundation, Inc.
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

from bloom.logging import debug
from bloom.logging import error

try:
    from vcstool import __version__ as vcs_version
    from vcstool.clients import vcstool_clients
    from vcstool.commands.import_ import ImportCommand
except ImportError:
    try:
        from vcstools import __version__ as vcs_version
        from vcstools.vcs_abstraction import get_vcs_client
    except ImportError:
        debug(traceback.format_exc())
        error("vcstool nor vcstools were detected, please install one.",
              file=sys.stderr, exit=True)
    else:
        vcs_name = 'vcstools'
else:
    vcs_name = 'vcstool'

    from argparse import Namespace

    def _checkout_adapter(self, url, version=None,
                          verbose=False, shallow=False, timeout=None):
        args = Namespace(force=False, retry=2, skip_existing=False, path=self.path)
        command = ImportCommand(args, url, version, True, shallow)
        return self.import_(command)['returncode'] == 0

    def get_vcs_client(vcs_type, path):
        vcs_class = [c for c in vcstool_clients if c.type == vcs_type]
        if not vcs_class:
            raise ValueError(
                'No Client type registered for vcs type "%s"' % vcs_type)

        client = vcs_class[0](path)
        client.checkout = lambda *args, **kwargs: _checkout_adapter(client, *args, **kwargs)
        client.get_path = lambda: client.path
        return client
