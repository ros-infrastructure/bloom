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
import base64
import difflib
import httplib
import json
import netrc
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2
import webbrowser
import yaml

from bloom.commands.git.config import convert_old_bloom_conf
from bloom.commands.git.config import edit as edit_track_cmd
from bloom.commands.git.config import new as new_track_cmd
from bloom.commands.git.config import update_track

from bloom.config import get_tracks_dict_raw
from bloom.config import write_tracks_dict_raw

from bloom.git import get_branches
from bloom.git import inbranch
from bloom.git import ls_tree
from bloom.git import track_branches

from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import get_error_prefix
from bloom.logging import get_success_prefix
from bloom.logging import info
from bloom.logging import warning

from bloom.util import change_directory
from bloom.util import check_output
from bloom.util import maybe_continue

try:
    from vcstools.vcs_abstraction import get_vcs_client
except ImportError:
    error("vcstools was not detected, please install it.", file=sys.stderr,
          exit=True)

ROS_DISTRO_FILE = 'https://raw.github.com/ros/rosdistro/master/releases/{0}.yaml'

_repositories = {}

_success = get_success_prefix()
_error = get_error_prefix()

_user_provided_release_url = None


@atexit.register
def exit_cleanup():
    global _repositories
    for repo in _repositories.values():
        repo_path = repo.get_path()
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)


def fetch_distro_file(distro_file_url):
    try:
        raw_distro_file = urllib2.urlopen(distro_file_url)
    except urllib2.HTTPError as e:
        error("Failed to fetch ROS distro file at '{0}': {1}"
              .format(distro_file_url, e), exit=True)
    return raw_distro_file.read()


def get_repo_uri(repository, distro, distro_file_url=ROS_DISTRO_FILE):
    # Fetch the distro file
    distro_file_url = distro_file_url.format(distro)
    distro_file = yaml.load(fetch_distro_file(distro_file_url))
    url = None
    if repository not in distro_file['repositories']:
        error("Specified repository '{0}' is not in the distro file located at '{1}'"
              .format(repository, distro_file_url))
    elif 'url' not in distro_file['repositories'][repository] or not distro_file['repositories'][repository]['url']:
        error("'url' is not set for the given repository in the distro file located at '{0}'".format(distro_file_url))
    else:
        url = distro_file['repositories'][repository]['url']
    if not url:
        info("You can continue the release process by manually specifying the location of the RELEASE repository.")
        info("To be clear this is the url of the RELEASE repository not the upstream repository.")
        try:
            url = raw_input('Release repository url [press enter to abort]: ')
        except (KeyboardInterrupt, EOFError):
            url = None
        if not url:
            error("No release repository url given, aborting.", exit=True)
        global _user_provided_release_url
        _user_provided_release_url = url
    return url


def get_release_repo(repository, distro):
    global _repositories
    uri = get_repo_uri(repository, distro)
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
        error("Release repository '{0}' not initialized,".format(repository) +
              " please initialize the bloom repository before releasing from it.",
              exit=True)
    bloom_files = [f for f, t in bloom_ls.iteritems() if t == 'file']
    return 'bloom.conf' in bloom_files


def list_tracks(repository, distro):
    release_repo = get_release_repo(repository, distro)
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


def generate_ros_distro_diff(track, repository, distro, distro_file_url, distro_file, distro_file_raw):
    with inbranch('upstream'):
        # Check for package.xml(s)
        try:
            from catkin_pkg.packages import find_packages
        except ImportError:
            error("catkin_pkg was not detected, please install it.",
                  file=sys.stderr, exit=True)
        packages = find_packages(os.getcwd())
        if len(packages) == 0:
            warning("No packages found, will not generate 'package: path' entries for rosdistro.")
        track_dict = get_tracks_dict_raw()['tracks'][track]
        last_version = track_dict['last_version']
        release_inc = track_dict['release_inc']
        if repository not in distro_file['repositories']:
            global _user_provided_release_url
            distro_file['repositories'][repository] = {'url': _user_provided_release_url or ''}
        distro_file['repositories'][repository]['version'] = '{0}-{1}'.format(last_version, release_inc)
        if packages and (len(packages) > 1 or packages.keys()[0] != '.'):
            distro_file['repositories'][repository]['packages'] = {}
            for path, package in packages.iteritems():
                if os.path.dirname(path) == package.name:
                    distro_file['repositories'][repository]['packages'][package.name] = None
                else:
                    distro_file['repositories'][repository]['packages'][package.name] = path
    distro_file_name = os.path.join('release', distro_file_url.split('/')[-1])
    distro_dump = yaml.dump(distro_file, indent=2, default_flow_style=False)
    if distro_file_raw != distro_dump:
        udiff = difflib.unified_diff(distro_file_raw.splitlines(), distro_dump.splitlines(),
                                     fromfile=distro_file_name, tofile=distro_file_name)
        temp_dir = tempfile.mkdtemp()
        version = distro_file['repositories'][repository]['version']
        udiff_file = os.path.join(temp_dir, repository + '-' + version + '.patch')
        udiff_raw = ''
        info("Unified diff for the ROS distro file located at '{0}':".format(udiff_file))
        for line in udiff:
            if line.startswith('@@'):
                udiff_raw += line
                line = fmt('@{cf}' + line)
            if line.startswith('+'):
                if not line.startswith('+++'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{gf}' + line)
            if line.startswith('-'):
                if not line.startswith('---'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{rf}' + line)
            if line.startswith(' '):
                line += '\n'
                udiff_raw += line
            info(line, use_prefix=False, end='')
        with open(udiff_file, 'w+') as f:
            f.write(udiff_raw)
        return udiff_file, distro_dump
    else:
        warning("This release resulted in no changes to the ROS distro file...")
    return None, None


def get_gh_info(url):
    from urlparse import urlparse
    o = urlparse(url)
    if 'raw.github.com' not in o.netloc:
        return None, None, None, None
    url_paths = o.path.split('/')
    if len(url_paths) < 5:
        return None, None, None, None
    return url_paths[1], url_paths[2], url_paths[3], '/'.join(url_paths[4:])


def fetch_github_api(url, data=None):
    try:
        if data is not None:
            req = urllib2.Request(url=url, data=data)
            raw_gh_api = urllib2.urlopen(req)
        else:
            raw_gh_api = urllib2.urlopen(url)
    except urllib2.HTTPError as e:
        error("Failed to fetch github API '{0}': {1}"
              .format(url, e))
        return None
    return json.loads(raw_gh_api.read())


def create_fork(org, repo, user, password):
    msg = "Creating fork: {0}:{1} => {2}:{1}".format(org, repo, user)
    info(fmt("@{bf}@!==> @|@!" + str(msg)))
    headers = {}
    headers["Authorization"] = "Basic {0}".format(base64.b64encode('{0}:{1}'.format(user, password)))
    conn = httplib.HTTPSConnection('api.github.com')
    conn.request('POST', '/repos/{0}/{1}/forks'.format(org, repo), json.dumps({}), headers)
    resp = conn.getresponse()
    if str(resp.status) != '202':
        error("Failed to create fork: {0} {1}".format(resp.status, resp.reason), exit=True)


def create_pull_request(org, repo, user, password, base_branch, head_branch, title):
    headers = {}
    headers["Authorization"] = "Basic {0}".format(base64.b64encode('{0}:{1}'.format(user, password)))
    conn = httplib.HTTPSConnection('api.github.com')
    data = {
        'title': title,
        'body': "",
        'head': "{0}:{1}".format(user, head_branch),
        'base': base_branch
    }
    conn.request('POST', '/repos/{0}/{1}/pulls'.format(org, repo), json.dumps(data), headers)
    resp = conn.getresponse()
    if str(resp.status) != '201':
        error("Failed to create pull request: {0} {1}".format(resp.status, resp.reason), exit=True)
    api_location = resp.msg.dict['location']
    api_dict = fetch_github_api(api_location)
    return api_dict['html_url']


def open_pull_request(track, repository, distro, distro_file_url=ROS_DISTRO_FILE):
    # Get the diff
    distro_file_url = distro_file_url.format(distro)
    distro_file_raw = fetch_distro_file(distro_file_url)
    distro_file = yaml.load(distro_file_raw)
    udiff_patch_file, updated_distro_file = generate_ros_distro_diff(track, repository, distro,
                                                                     distro_file_url, distro_file,
                                                                     distro_file_raw)
    if None in [udiff_patch_file, updated_distro_file]:
        # There were no changes, no pull request required
        return None
    version = distro_file['repositories'][repository]['version']
    # Determine if the distro file is hosted on github...
    distro_file_url = distro_file_url.format(distro)
    gh_org, gh_repo, gh_branch, gh_path = get_gh_info(distro_file_url)
    if None in [gh_org, gh_repo, gh_branch, gh_path]:
        warning("Automated pull request only available via github.com")
        return
    # Determine if we have a .netrc file
    gh_username = None
    try:
        netrc_hosts = netrc.netrc().hosts
    except Exception as e:
        error("Failed to parse ~/.netrc file: {0}".format(e))
        warning("Skipping the pull request...")
        return
    for host in netrc_hosts.keys():
        if 'github.com' in host:
            gh_username = netrc_hosts[host][0]
            gh_password = netrc_hosts[host][2]
        if None in [gh_username, gh_password]:
            error("Either github username or github password is not set in the netrc.")
            warning("Skipping the pull request...")
            return
    # Check for fork
    info(fmt("@{bf}@!==> @|@!Checking for rosdistro fork on github..."))
    gh_user_repos = fetch_github_api('https://api.github.com/users/{0}/repos'.format(gh_username))
    if gh_user_repos is None:
        error("Failed to get a list of repositories for user: '{0}'".format(gh_username))
        warning("Skipping the pull request...")
        return
    if 'rosdistro' not in [x['name'] for x in gh_user_repos if 'name' in x]:
        warning("Github user '{0}' does not have a fork ".format(gh_username) +
                "of the {0}:{1} repository, create one?".format(gh_org, gh_repo))
        if not maybe_continue():
            warning("Skipping the pull request...")
            return
        # Create a fork
        create_fork(gh_org, gh_repo, gh_username, gh_password)
    # Clone the fork
    info(fmt("@{bf}@!==> @|@!" + "Cloning {0}/{1}...".format(gh_username, gh_repo)))
    temp_dir = tempfile.mkdtemp()
    new_branch = None
    title = "{0}: update version to {1} in {2} [bloom]".format(repository, version, gh_path)
    with change_directory(temp_dir):
        def _my_run(cmd):
            info(fmt("@{bf}@!==> @|@!" + str(cmd)))
            out = check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            if out:
                info(out, use_prefix=False)
        _my_run('git clone https://github.com/{0}/{1}.git'.format(gh_username, gh_repo))
        with change_directory(gh_repo):
            _my_run('git remote add bloom https://github.com/{0}/{1}.git'.format(gh_org, gh_repo))
            _my_run('git remote update')
            _my_run('git fetch')
            track_branches()
            branches = get_branches()
            new_branch = 'bloom-patch-{0}'
            count = 0
            while new_branch.format(count) in branches:
                count += 1
            new_branch = new_branch.format(count)
            _my_run('git checkout -b {0} bloom/{1}'.format(new_branch, gh_branch))
            with open('{0}'.format(gh_path), 'w') as f:
                info(fmt("@{bf}@!==> @|@!Writing new distribution file: ") + str(gh_path))
                f.write(updated_distro_file)
            _my_run('git add {0}'.format(gh_path))
            _my_run('git commit -m "{0}"'.format(title))
            _my_run('git push origin {0}'.format(new_branch))
    # Final check
    msg = fmt("@!Open a @{cf}pull request@| @!@{kf}from@| @!'@|@{bf}" +
              "{gh_username}/{gh_repo}:{new_branch}".format(**locals()) +
              "@|@!' @!@{kf}into@| @!'@|@{bf}" +
              "{gh_org}/{gh_repo}:{gh_branch}".format(**locals()) +
              "@|@!'?")
    info(msg)
    if not maybe_continue():
        warning("Skipping the pull request...")
        return
    # Open the pull request
    return create_pull_request(gh_org, gh_repo, gh_username, gh_password, gh_branch, new_branch, title)


def perform_release(repository, track, distro, new_track, interactive, pretend):
    release_repo = get_release_repo(repository, distro)
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
            info("Old bloom.conf file detected.")
            info(fmt("@{gf}@!==> @|Converting to bloom.conf to track"))
            convert_old_bloom_conf(None if new_track else distro)
        # Check that the track is valid
        tracks_dict = get_tracks_dict_raw()
        # If new_track, create the new track first
        if new_track:
            if not track:
                error("You must specify a track when creating a new one.", exit=True)
            overrides = {'ros_distro': distro}
            if track in tracks_dict['tracks']:
                warning("Track '{0}' exists, editing instead...".format(track))
                edit_track_cmd(track)
            else:
                # Create a new track called <track>,
                # copying an existing track if possible,
                # and overriding the ros_distro
                new_track_cmd(track, copy_track='', overrides=overrides)
                tracks_dict = get_tracks_dict_raw()
        if track and track not in tracks_dict['tracks']:
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
        if pretend:
            cmd += ' --pretend'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Release failed, exiting.", exit=True)
        info(fmt(_success) +
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
        if pretend:
            cmd += ' --dry-run'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing changes failed, would you like to add '--force' to 'git push --all'?")
            if not maybe_continue():
                error("Pushing changes failed, exiting.", exit=True)
            cmd += ' --force'
            info(fmt("@{bf}@!==> @|@!" + str(cmd)))
            try:
                subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                error("Pushing changes failed, exiting.", exit=True)
        info(fmt(_success) + "Pushed changes successfully")
        # Push tags to the repository
        info(fmt("@{gf}@!==> @|") +
             "Pushing tags to release repository for '{0}'"
             .format(repository))
        cmd = 'git push --tags'
        if pretend:
            cmd += ' --dry-run'
        info(fmt("@{bf}@!==> @|@!" + str(cmd)))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Pushing changes failed, would you like to add '--force' to 'git push --tags'?")
            if not maybe_continue():
                error("Pushing tags failed, exiting.", exit=True)
            cmd += ' --force'
            info(fmt("@{bf}@!==> @|@!" + str(cmd)))
            try:
                subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                error("Pushing tags failed, exiting.", exit=True)
        info(fmt(_success) + "Pushed tags successfully")
        # Propose github pull request
        info(fmt("@{gf}@!==> @|") +
             "Generating pull request to distro file located at '{0}'"
             .format(ROS_DISTRO_FILE).format(distro))
        try:
            pull_request_url = open_pull_request(track, repository, distro)
            if pull_request_url:
                info(fmt(_success) + "Pull request opened at: '{0}'".format(pull_request_url))
                webbrowser.open(pull_request_url)
            else:
                info(fmt(_error) + "No pull request opened.")
        except Exception as e:
            error("Failed to open pull request: {0}".format(e), exit=True)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="Releases a repository which already exists in the ROS distro file.")
    add = parser.add_argument
    add('repository', help="repository to run bloom on")
    add('--list-tracks', '-l', action='store_true', default=False,
        help="list available tracks for repository")
    add('track', nargs='?', default=None, help="track to run")
    add('--non-interactive', '-y', action='store_true', default=False)
    add('--ros-distro', '-r', default='groovy', help="determines the ROS distro file used")
    add('--new-track', '-n', action='store_true', default=False,
        help="if used, a new track will be created before running bloom")
    add('--pretend', '-p', default=False, action='store_true',
        help="Pretends to push and release")
    return parser

_quiet = False


def main(sysargs=None):
    parser = get_argument_parser()
    args = parser.parse_args(sysargs)

    if args.list_tracks:
        list_tracks(args.repository, args.ros_distro)
        return

    perform_release(args.repository, args.track, args.ros_distro,
                    args.new_track, not args.non_interactive, args.pretend)
