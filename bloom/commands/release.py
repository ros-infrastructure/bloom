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
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2
import yaml

from bloom.commands.git.config import convert_old_bloom_conf
from bloom.commands.git.config import update_track

from bloom.config import get_tracks_dict_raw
from bloom.config import write_tracks_dict_raw

from bloom.git import ls_tree

from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import info

from bloom.util import change_directory
from bloom.util import check_output
from bloom.util import maybe_continue

try:
    from vcstools.vcs_abstraction import get_vcs_client
except ImportError:
    error("vcstools was not detected, please install it.", file=sys.stderr,
        exit=True)

ROS_DISTRO = 'groovy'
ROS_DISTRO_FILE = 'https://raw.github.com/ros/rosdistro/master/releases/{0}.yaml'.format(ROS_DISTRO)

_repositories = {}


@atexit.register
def exit_cleanup():
    global _repositories
    for repo in _repositories.values():
        repo_path = repo.get_path()
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)


def get_repo_uri(repository, distro_file_url=ROS_DISTRO_FILE):
    # Fetch the DISTRO_FILE
    raw_distro_file = urllib2.urlopen(distro_file_url)
    distro_file = yaml.load(raw_distro_file.read())
    if repository not in distro_file['repositories']:
        error("Specified repository '{0}' is not in the distro file located at '{1}'".format(repository, distro_file_url),
            exit=True)
    return distro_file['repositories'][repository]['url']


def get_release_repo(repository):
    global _repositories
    uri = get_repo_uri(repository)
    if repository not in _repositories.values():
        temp_dir = tempfile.mkdtemp()
        _repositories[repository] = get_vcs_client('git', temp_dir)
        info(fmt("@{gf}@!==> @|") +
            "Fetching '{0}' repository from '{1}'".format(repository, uri))
        _repositories[repository].checkout(uri, 'master')
    return _repositories[repository]


def check_for_bloom_conf(repository):
    bloom_ls = ls_tree('bloom')
    if bloom_ls is None:
        error("Release repository '{0}' not initialized, please initialize the bloom repository before releasing from it."
            .format(repository), exit=True)
    bloom_files = [f for f, t in bloom_ls.iteritems() if t == 'file']
    return 'bloom.conf' in bloom_files


def list_tracks(repository):
    release_repo = get_release_repo(repository)
    tracks_dict = None
    with change_directory(release_repo.get_path()):
        if check_for_bloom_conf(repository):
            info("No tracks, but old style bloom.conf available for conversion")
        else:
            tracks_dict = get_tracks_dict_raw()
            if tracks_dict and tracks_dict['tracks'].keys():
                info("Available tracks: " + str(tracks_dict['tracks'].keys()))
            else:
                error("Release repository has no tracks nor an old style bloom.conf file.", exit=True)
    return tracks_dict['tracks'].keys() if tracks_dict else None


def perform_release(repository, track, interactive):
    release_repo = get_release_repo(repository)
    with change_directory(release_repo.get_path()):
        # Check for push permissions
        try:
            info(fmt("@{gf}@!==> @|Testing for push permission on release repository"))
            check_output('git push', shell=True)
        except subprocess.CalledProcessError:
            error("Cannot push to remote release repository.", exit=True)
        # Check to see if the old bloom.conf exists
        if check_for_bloom_conf(repository):
            # Convert to a track
            info("Old bloom.conf file detected, up converting...")
            convert_old_bloom_conf(ROS_DISTRO)
        # Check that the track is valid
        tracks_dict = get_tracks_dict_raw()
        if track and track not in [tracks_dict['tracks']]:
            error("Given track '{0}' does not exist in release repository."
                .format(track))
            error("Available tracks: " + str(tracks_dict['tracks'].keys()),
                exit=True)
        elif not track:
            tracks = tracks_dict['tracks'].keys()
            # Error out if there are no tracks
            if len(tracks) == 0:
                error("Release repository has no tracks.")
                info("Manually clone the repository:")
                info("  git clone {0}".format(release_repo.get_url()))
                info("And then create a new track:")
                info("  git-bloom-config new <track name>")
                error("Run again after creating a track.", exit=True)
            # Error out if there is more than one track
            if len(tracks) != 1:
                error("No track specified and there is not just one track.")
                error("Please specify one of the available tracks: " +
                    str(tracks), exit=True)
            # Get the only track
            track = tracks[0]
        # Ensure the track is complete
        track_dict = tracks_dict['tracks'][track]
        update_track(track_dict)
        tracks_dict['tracks'][track] = track_dict
        write_tracks_dict_raw(tracks_dict)
        # Run the release
        info(fmt("@{gf}@!==> @|") +
            "Releasing '{0}' using release track '{1}'"
            .format(repository, track))
        cmd = 'git-bloom-release ' + str(track)
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Release failed, exiting.", exit=True)
        info(fmt("@{gf}<== @|") +
            "Released '{0}' using release track '{1}' successfully"
            .format(repository, track))
        # Check for pushing
        if interactive:
            info("Releasing complete, push?")
            if not maybe_continue():
                error("User answered no to continue prompt, aborting.",
                    exit=True)
        # Push changes to the repository
        info(fmt("@{gf}@!==> @|") +
            "Pushing changes to release repository for '{0}'"
            .format(repository))
        cmd = 'git push --all'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing changes failed, exiting.", exit=True)
        info(fmt("@{gf}<== @|") + "Pushed changes successfully")
        # Push tags to the repository
        info(fmt("@{gf}@!==> @|") +
            "Pushing tags to release repository for '{0}'"
            .format(repository))
        cmd = 'git push --all'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing tags failed, exiting.", exit=True)
        info(fmt("@{gf}<== @|") + "Pushed tags successfully")
        # Propose github pull request
        info(fmt("@{gf}@!==> @|") +
            "Generating pull request to distro file located at '{0}'"
            .format(ROS_DISTRO_FILE))
        info("In the future this will create a pull request for you, done for now...")
        info(fmt("@{gf}<== @|") + "Pull request opened at: '{0}'".format('Not yet Implemented'))


def get_argument_parser():
    parser = argparse.ArgumentParser(description="Releases a repository which already exists in the ROS distro file.")
    add = parser.add_argument
    add('repository', help="repository to run bloom on")
    add('--list-tracks', '-l', action='store_true', default=False,
        help="list available tracks for repository")
    add('track', nargs='?', default=None, help="track to run")
    add('--non-interactive', '-y', action='store_true', default=False)
    return parser

_quiet = False


def main(sysargs=None):
    parser = get_argument_parser()
    args = parser.parse_args(sysargs)

    if args.list_tracks:
        list_tracks(args.repository)
        return

    perform_release(args.repository, args.track, not args.non_interactive)
