# Software License Agreement (BSD License)
#
# Copyright (c) 2014, Open Source Robotics Foundation, Inc.
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
from __future__ import unicode_literals

import os
import sys
import traceback

from pkg_resources import parse_version

# python2/3 compatibility
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from bloom.github import Github
from bloom.github import GithubException
from bloom.github import get_gh_info
from bloom.github import get_github_interface

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info


try:
    import rosdistro
    if parse_version(rosdistro.__version__) < parse_version('0.7.0'):
        error("rosdistro version 0.7.0 or greater is required, found '{0}' from '{1}'."
              .format(rosdistro.__version__, os.path.dirname(rosdistro.__file__)),
              exit=True)
except ImportError:
    debug(traceback.format_exc())
    error("rosdistro was not detected, please install it.", file=sys.stderr,
          exit=True)

_rosdistro_index = None
_rosdistro_distribution_files = {}
_rosdistro_index_commit = None
_rosdistro_index_original_branch = None


def get_index_url():
    global _rosdistro_index_commit, _rosdistro_index_original_branch
    index_url = rosdistro.get_index_url()
    pr = urlparse(index_url)
    if pr.netloc in ['raw.github.com', 'raw.githubusercontent.com']:
        # Try to determine what the commit hash was
        tokens = [x for x in pr.path.split('/') if x]
        if len(tokens) <= 3:
            debug("Failed to get commit for rosdistro index file: index url")
            debug(tokens)
            return index_url
        owner = tokens[0]
        repo = tokens[1]
        branch = tokens[2]
        gh = get_github_interface(quiet=True)
        if gh is None:
            # Failed to get it with auth, try without auth (may fail)
            gh = Github(username=None, auth=None)
        try:
            data = gh.get_branch(owner, repo, branch)
        except GithubException:
            debug(traceback.format_exc())
            debug("Failed to get commit for rosdistro index file: api")
            return index_url
        _rosdistro_index_commit = data.get('commit', {}).get('sha', None)
        if _rosdistro_index_commit is not None:
            info("ROS Distro index file associate with commit '{0}'"
                 .format(_rosdistro_index_commit))
            # Also mutate the index_url to use the commit (rather than the moving branch name)
            base_info = get_gh_info(index_url)
            base_branch = base_info['branch']
            rosdistro_index_commit = _rosdistro_index_commit  # Copy global into local for substitution
            middle = "{org}/{repo}".format(**base_info)
            index_url = index_url.replace("{pr.netloc}/{middle}/{base_branch}/".format(**locals()),
                                          "{pr.netloc}/{middle}/{rosdistro_index_commit}/".format(**locals()))
            info("New ROS Distro index url: '{0}'".format(index_url))
            _rosdistro_index_original_branch = base_branch
        else:
            debug("Failed to get commit for rosdistro index file: json")
    return index_url


def get_index():
    global _rosdistro_index
    if _rosdistro_index is None:
        _rosdistro_index = rosdistro.get_index(get_index_url())
        if _rosdistro_index.version == 1:
            error("This version of bloom does not support rosdistro version "
                  "'{0}', please use an older version of bloom."
                  .format(_rosdistro_index.version), exit=True)
        if _rosdistro_index.version > 4:
            error("This version of bloom does not support rosdistro version "
                  "'{0}', please update bloom.".format(_rosdistro_index.version), exit=True)
    return _rosdistro_index


def list_distributions():
    return sorted(get_index().distributions.keys())


def get_distribution_type(distro):
    return get_index().distributions[distro].get('distribution_type')


def get_python_version(distro):
    return get_index().distributions[distro].get('python_version')


def get_most_recent(thing_name, repository, reference_distro):
    reference_distro_type = get_distribution_type(reference_distro)
    distros_with_entry = {}
    get_things = {
        'release': lambda r: None if r.release_repository is None else r.release_repository,
        'doc': lambda r: None if r.doc_repository is None else r.doc_repository,
        'source': lambda r: None if r.source_repository is None else r.source_repository,
    }
    get_thing = get_things[thing_name]
    for distro in list_distributions():
        # skip distros with a different type if the information is available
        if reference_distro_type is not None:
            if get_distribution_type(distro) != reference_distro_type:
                continue
        distro_file = get_distribution_file(distro)
        if repository in distro_file.repositories:
            thing = get_thing(distro_file.repositories[repository])
            if thing is not None:
                distros_with_entry[distro] = thing
    # Choose the alphabetical last distro which contained a release of this repository
    default_distro = (sorted(distros_with_entry.keys()) or [None])[-1]
    default_thing = distros_with_entry.get(default_distro, None)
    return default_distro, default_thing


def get_distribution_file(distro):
    global _rosdistro_distribution_files
    if distro not in _rosdistro_distribution_files:
        # REP 143, get list of distribution files and take the last one
        files = rosdistro.get_distribution_files(get_index(), distro)
        if not files:
            error("No distribution files listed for distribution '{0}'."
                  .format(distro), exit=True)
        _rosdistro_distribution_files[distro] = files[-1]
    return _rosdistro_distribution_files[distro]


def get_rosdistro_index_commit():
    return _rosdistro_index_commit


def get_rosdistro_index_original_branch():
    return _rosdistro_index_original_branch
