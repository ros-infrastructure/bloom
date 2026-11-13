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


import argparse
import binascii
import hashlib
import os
import subprocess
import sys
import tarfile
import traceback

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.git import branch_exists
from bloom.git import tag_exists

from bloom.util import add_global_arguments
from bloom.util import change_directory
from bloom.util import handle_global_arguments
from bloom.util import temporary_directory

try:
    from vcstools.vcs_abstraction import get_vcs_client
except ImportError:
    debug(traceback.format_exc())
    error("vcstools was not detected, please install it.", file=sys.stderr,
          exit=True)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="""\
Creates a tarball from an upstream repository, which can be given to
git-bloom-import-upstream to be imported into the release repository.
""")
    add = parser.add_argument
    add('uri', help="uri of the upstream repository")
    add('type', choices=['git', 'hg', 'svn'],
        help="vcs type of upstream repository")
    add('--tag', '-t',
        help="release tag to be exported (can be other types of references)")
    add('--output-dir', '-o', help="destination of the tarball")
    add('--display-uri', help="uri to use in messages (original upstream)")
    add('--name', '-n',
        help="name of the repository being exported (used in tarball name)")
    add('--submodule-recursion-depth', type=int, default=None, metavar='DEPTH',
        help="how many levels of git submodules to include in the tarball: "
             "0 for none, 1 for only the top-level submodules, etc. "
             "(default: all levels, git only)")
    return parser


def calculate_file_md5(path, block_size=2 ** 20):
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
    digest = binascii.hexlify(md5.digest())
    if not isinstance(digest, str):
        digest = digest.decode('utf-8')
    return digest


def _run_git(args, cwd, error_msg):
    cmd = ['git'] + args
    debug("Running '{0}'".format(' '.join(cmd)))
    try:
        subprocess.check_call(cmd, cwd=cwd)
    except subprocess.CalledProcessError:
        error(error_msg, exit=True)


def export_git_with_submodule_depth(uri, tag, repo_path, tarball_path, depth):
    """Export a git repository, including submodules up to the given depth.

    vcstools always initializes submodules recursively, which can explode for
    repositories where every submodule vendors the same dependencies again.
    """
    _run_git(['clone', '--quiet', '--no-checkout', uri, repo_path], None,
             "Failed to clone repository at '{0}'".format(uri))
    _run_git(['checkout', '--quiet', '--detach', tag or 'HEAD'], repo_path,
             "Failed to checkout reference '{0}'".format(tag))
    for level in range(depth):
        cmd = ['submodule', 'update', '--init']
        if level > 0:  # initialize the next level inside every already initialized submodule
            cmd = ['submodule', 'foreach', '--recursive', '--quiet', 'git submodule update --init']
        _run_git(cmd, repo_path, "Failed to initialize the submodules")
    with tarfile.open(tarball_path + '.tar.gz', 'w:gz') as tar:
        for entry in os.listdir(repo_path):
            tar.add(os.path.join(repo_path, entry), arcname=entry,
                    filter=lambda ti: None if os.path.basename(ti.name) == '.git' else ti)


def export_upstream(uri, tag, vcs_type, output_dir, show_uri, name,
                    submodule_recursion_depth=None):
    tag = tag if tag != ':{none}' else None
    if submodule_recursion_depth is not None:
        if vcs_type != 'git':
            error("--submodule-recursion-depth is only supported for git repositories",
                  exit=True)
        if submodule_recursion_depth < 0:
            error("--submodule-recursion-depth must not be negative", exit=True)
    output_dir = os.path.abspath(output_dir or os.getcwd())
    if uri.startswith('git@'):
        uri_is_path = False
    else:
        uri_parsed = urlparse(uri)
        uri = uri if uri_parsed.scheme else uri_parsed.path
        uri_is_path = False if uri_parsed.scheme else True
    name = name or 'upstream'
    with temporary_directory() as tmp_dir:
        info("Checking out repository at '{0}'".format(show_uri or uri) +
             (" to reference '{0}'.".format(tag) if tag else '.'))
        tarball_prefix = '{0}-{1}'.format(name, tag) if tag else name
        tarball_path = os.path.join(output_dir, tarball_prefix)
        full_tarball_path = tarball_path + '.tar.gz'
        if submodule_recursion_depth is not None:
            info("Exporting to archive (submodule recursion depth {0}): '{1}'"
                 .format(submodule_recursion_depth, full_tarball_path))
            export_git_with_submodule_depth(uri, tag, os.path.join(tmp_dir, 'upstream'),
                                            tarball_path, submodule_recursion_depth)
        else:
            export_with_vcstools(uri, uri_is_path, tag, vcs_type, tmp_dir,
                                 tarball_path, show_uri)
        if not os.path.exists(full_tarball_path):
            error("Tarball was not created.", exit=True)
        info("md5: {0}".format(calculate_file_md5(full_tarball_path)))


def export_with_vcstools(uri, uri_is_path, tag, vcs_type, tmp_dir, tarball_path, show_uri):
    if uri_is_path:
        upstream_repo = get_vcs_client(vcs_type, uri)
    else:
        repo_path = os.path.join(tmp_dir, 'upstream')
        upstream_repo = get_vcs_client(vcs_type, repo_path)
        if not upstream_repo.checkout(uri, tag or ''):
            error("Failed to clone repository at '{0}'".format(uri) +
                  (" to reference '{0}'.".format(tag) if tag else '.'),
                  exit=True)
    info("Exporting to archive: '{0}.tar.gz'".format(tarball_path))
    if not upstream_repo.export_repository(tag or '', tarball_path):
        error("Failed to create archive of upstream repository at '{0}'"
              .format(show_uri))
        if tag and vcs_type == 'git':  # can only check for git repos
            with change_directory(upstream_repo.get_path()):
                if not tag_exists(tag):
                    warning("'{0}' is not a tag in the upstream repository..."
                            .format(tag))
                if not branch_exists(tag):
                    warning("'{0}' is not a branch in the upstream repository..."
                            .format(tag))


def main(sysargs=None):
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    export_upstream(args.uri, args.tag, args.type, args.output_dir,
                    args.display_uri, args.name, args.submodule_recursion_depth)
