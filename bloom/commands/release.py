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
import datetime
import difflib
import getpass
import json
import os
import pkg_resources
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
import urllib2
import webbrowser

try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection

from urlparse import urlparse

import bloom

from bloom.commands.git.config import convert_old_bloom_conf
from bloom.commands.git.config import edit as edit_track_cmd
from bloom.commands.git.config import new as new_track_cmd
from bloom.commands.git.config import update_track

from bloom.config import get_tracks_dict_raw
from bloom.config import upconvert_bloom_to_config_branch
from bloom.config import write_tracks_dict_raw

from bloom.git import get_branches
from bloom.git import inbranch
from bloom.git import ls_tree
from bloom.git import track_branches

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import fmt
from bloom.logging import get_error_prefix
from bloom.logging import get_success_prefix
from bloom.logging import info
from bloom.logging import sanitize
from bloom.logging import warning

from bloom.packages import get_package_data
from bloom.packages import get_ignored_packages

from bloom.summary import commit_summary
from bloom.summary import get_summary_file

from bloom.util import add_global_arguments
from bloom.util import change_directory
from bloom.util import disable_git_clone
from bloom.util import safe_input
from bloom.util import get_rfc_2822_date
from bloom.util import handle_global_arguments
from bloom.util import load_url_to_file_handle
from bloom.util import maybe_continue
from bloom.util import quiet_git_clone_warning

try:
    import vcstools
except ImportError:
    debug(traceback.format_exc())
    error("vcstools was not detected, please install it.", file=sys.stderr,
          exit=True)
import vcstools.__version__
from vcstools.vcs_abstraction import get_vcs_client

try:
    import rosdistro
except ImportError:
    debug(traceback.format_exc())
    error("rosdistro was not detected, please install it.", file=sys.stderr,
          exit=True)
from rosdistro.writer import yaml_from_distribution_file

try:
    import rosdep2
except ImportError:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.",
          file=sys.stderr, exit=True)

try:
    import catkin_pkg
except ImportError:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr, exit=True)

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

_rosdistro_index = None
_rosdistro_distribution_files = {}


def get_index():
    global _rosdistro_index
    if _rosdistro_index is None:
        _rosdistro_index = rosdistro.get_index(rosdistro.get_index_url())
        if _rosdistro_index.version == 1:
            error("This version of bloom does not support rosdistro version "
                  "'{0}', please use an older version of bloom."
                  .format(_rosdistro_index.version), exit=True)
        if _rosdistro_index.version > 2:
            error("This version of bloom does not support rosdistro version "
                  "'{0}', please update bloom.".format(_rosdistro_index.version), exit=True)
    return _rosdistro_index


def get_distribution_file(distro):
    global _rosdistro_distribution_files
    if distro not in _rosdistro_distribution_files:
        _rosdistro_distribution_files[distro] = rosdistro.get_distribution_file(get_index(), distro)
    return _rosdistro_distribution_files[distro]

_rosdistro_distribution_file_urls = {}


def get_disitrbution_file_url(distro):
    global _rosdistro_distribution_file_urls
    if distro not in _rosdistro_distribution_file_urls:
        index = get_index()
        if distro not in index.distributions:
            error("'{0}' distro is not in the index file.".format(distro), exit=True)
        distro_file = index.distributions[distro]
        if 'distribution' not in distro_file:
            error("'{0}' distro does not have a distribution file.".format(distro), exit=True)
        _rosdistro_distribution_file_urls[distro] = distro_file['distribution']
    return _rosdistro_distribution_file_urls[distro]


def get_repo_uri(repository, distro):
    url = None
    # Fetch the distro file
    distribution_file = get_distribution_file(distro)
    if repository in distribution_file.repositories and \
       distribution_file.repositories[repository].release_repository is not None:
        url = distribution_file.repositories[repository].release_repository.url
    else:
        error("Specified repository '{0}' is not in the distribution file located at '{1}'"
              .format(repository, get_disitrbution_file_url(distro)))
        matches = difflib.get_close_matches(repository, distribution_file.repositories)
        if matches:
            info(fmt("@{yf}Did you mean one of these: '" + "', '".join([m for m in matches]) + "'?"))
    if not url:
        info("Could not determine release repository url for repository '{0}' of distro '{1}'"
             .format(repository, distro))
        info("You can continue the release process by manually specifying the location of the RELEASE repository.")
        info("To be clear this is the url of the RELEASE repository not the upstream repository.")
        try:
            url = safe_input('Release repository url [press enter to abort]: ')
        except (KeyboardInterrupt, EOFError):
            url = None
            info('', use_prefix=False)
        if not url:
            error("No release repository url given, aborting.", exit=True)
        global _user_provided_release_url
        _user_provided_release_url = url
    return url


def get_release_repo(repository, distro):
    global _repositories
    url = get_repo_uri(repository, distro)
    if repository not in _repositories.values():
        temp_dir = tempfile.mkdtemp()
        _repositories[repository] = get_vcs_client('git', temp_dir)
        info(fmt("@{gf}@!==> @|") +
             "Fetching '{0}' repository from '{1}'".format(repository, url))
        _repositories[repository].checkout(url, 'master')
    return _repositories[repository]


def check_for_bloom_conf(repository):
    bloom_ls = ls_tree('bloom')
    if bloom_ls is None:
        return False
    bloom_files = [f for f, t in bloom_ls.items() if t == 'file']
    return 'bloom.conf' in bloom_files


def list_tracks(repository, distro):
    release_repo = get_release_repo(repository, distro)
    tracks_dict = None
    with change_directory(release_repo.get_path()):
        upconvert_bloom_to_config_branch()
        if check_for_bloom_conf(repository):
            info("No tracks, but old style bloom.conf available for conversion")
        else:
            tracks_dict = get_tracks_dict_raw()
            if tracks_dict and tracks_dict['tracks'].keys():
                info("Available tracks: " + str(tracks_dict['tracks'].keys()))
            else:
                error("Release repository has no tracks nor an old style bloom.conf file.", exit=True)
    return tracks_dict['tracks'].keys() if tracks_dict else None


def get_relative_distribution_file_path(distro):
    distribution_file_url = urlparse(get_disitrbution_file_url(distro))
    index_file_url = urlparse(rosdistro.get_index_url())
    return os.path.relpath(distribution_file_url.path,
                           os.path.commonprefix([index_file_url.path, distribution_file_url.path]))


def generate_ros_distro_diff(track, repository, distro):
    distribution_dict = get_distribution_file(distro).get_data()
    # Get packages
    packages = get_packages()
    if len(packages) == 0:
        warning("No packages found, will not generate 'package: path' entries for rosdistro.")
    # Get version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    last_version = track_dict['last_version']
    release_inc = track_dict['release_inc']
    version = '{0}-{1}'.format(last_version, release_inc)
    # Create a repository if there isn't already one
    if repository not in distribution_dict['repositories']:
        global _user_provided_release_url
        distribution_dict['repositories'][repository] = {}
        distribution_dict['repositories'][repository]['release'] = {
            'url': _user_provided_release_url
        }
    # Update the repository
    repo = distribution_dict['repositories'][repository]['release']
    if 'tags' not in repo:
        repo['tags'] = {}
    repo['tags']['release'] = 'release/%s/{package}/{version}' % distro
    repo['version'] = version
    if 'packages' not in repo:
        repo['packages'] = []
    for path, pkg in packages.items():
        if pkg.name not in repo['packages']:
            repo['packages'].append(pkg.name)
    # Remove any missing packages
    packages_being_released = [p.name for p in packages.values()]
    for pkg_name in list(repo['packages']):
        if pkg_name not in packages_being_released:
            repo['packages'].remove(pkg_name)
    repo['packages'].sort()

    # Do the diff
    distro_file_name = get_relative_distribution_file_path(distro)
    updated_distribution_file = rosdistro.DistributionFile(distro, distribution_dict)
    distro_dump = yaml_from_distribution_file(updated_distribution_file)
    distro_file_raw = load_url_to_file_handle(get_disitrbution_file_url(distro)).read()
    if distro_file_raw != distro_dump:
        udiff = difflib.unified_diff(distro_file_raw.splitlines(), distro_dump.splitlines(),
                                     fromfile=distro_file_name, tofile=distro_file_name)
        temp_dir = tempfile.mkdtemp()
        udiff_file = os.path.join(temp_dir, repository + '-' + version + '.patch')
        udiff_raw = ''
        info("Unified diff for the ROS distro file located at '{0}':".format(udiff_file))
        for line in udiff:
            if line.startswith('@@'):
                udiff_raw += line
                line = fmt('@{cf}' + sanitize(line))
            if line.startswith('+'):
                if not line.startswith('+++'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{gf}' + sanitize(line))
            if line.startswith('-'):
                if not line.startswith('---'):
                    line += '\n'
                udiff_raw += line
                line = fmt('@{rf}' + sanitize(line))
            if line.startswith(' '):
                line += '\n'
                udiff_raw += line
            info(line, use_prefix=False, end='')
        with open(udiff_file, 'w+') as f:
            f.write(udiff_raw)
        return updated_distribution_file
    else:
        warning("This release resulted in no changes to the ROS distro file...")
    return None


def get_gh_info(url):
    from urlparse import urlparse
    o = urlparse(url)
    if 'raw.github.com' not in o.netloc:
        return None, None, None, None
    url_paths = o.path.split('/')
    if len(url_paths) < 5:
        return None, None, None, None
    return url_paths[1], url_paths[2], url_paths[3], '/'.join(url_paths[4:])


def __fetch_github_api(url, data):
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
    return json.load(raw_gh_api)


def fetch_github_api(url, data=None, use_pagination=False, only_page=None):
    if not use_pagination:
        return __fetch_github_api(url, data)
    items = []
    page_count = only_page or 1
    while True:
        url_ = url + "?page=" + str(page_count)
        page_count += 1
        page_items = __fetch_github_api(url_, data)
        if page_items is None:
            return page_items
        items.extend(page_items)
        if not page_items or only_page:
            break
    return items


def create_fork(org, repo, user, password):
    msg = "Creating fork: {0}:{1} => {2}:{1}".format(org, repo, user)
    info(fmt("@{bf}@!==> @|@!" + str(msg)))
    headers = {}
    headers["Authorization"] = "Basic {0}".format(base64.b64encode('{0}:{1}'.format(user, password)))
    conn = HTTPSConnection('api.github.com')
    conn.request('POST', '/repos/{0}/{1}/forks'.format(org, repo), json.dumps({}), headers)
    resp = conn.getresponse()
    if str(resp.status) != '202':
        error("Failed to create fork: {0} {1}".format(resp.status, resp.reason), exit=True)


def create_pull_request(org, repo, user, password, base_branch, head_branch, title, body=""):
    headers = {}
    headers["Authorization"] = "Basic {0}".format(base64.b64encode('{0}:{1}'.format(user, password)))
    headers['User-Agent'] = 'bloom-{0}'.format(bloom.__version__)
    conn = HTTPSConnection('api.github.com')
    data = {
        'title': title,
        'body': body,
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


def open_pull_request(track, repository, distro, ssh_pull_request):
    # Get the diff
    distribution_file = get_distribution_file(distro)
    if repository in distribution_file.repositories and \
       distribution_file.repositories[repository].release_repository is not None:
        orig_version = distribution_file.repositories[repository].release_repository.version
    else:
        orig_version = None
    updated_distribution_file = generate_ros_distro_diff(track, repository, distro)
    if updated_distribution_file is None:
        # There were no changes, no pull request required
        return None
    version = updated_distribution_file.repositories[repository].release_repository.version
    updated_distro_file_yaml = yaml_from_distribution_file(updated_distribution_file)
    # Determine if the distro file is hosted on github...
    gh_org, gh_repo, gh_branch, gh_path = get_gh_info(get_disitrbution_file_url(distro))
    if None in [gh_org, gh_repo, gh_branch, gh_path]:
        warning("Automated pull request only available via github.com")
        return
    # Get the github user name
    gh_username = None
    bloom_user_path = os.path.join(os.path.expanduser('~'), '.bloom_user')
    if os.path.exists(bloom_user_path):
        with open(bloom_user_path, 'r') as f:
            gh_username = f.read().strip()
    gh_username = gh_username or getpass.getuser()
    response = safe_input("github user name [{0}]: ".format(gh_username))
    if response:
        gh_username = response
        info("Would you like bloom to store your github user name (~/.bloom_user)?")
        if maybe_continue():
            with open(bloom_user_path, 'w') as f:
                f.write(gh_username)
        else:
            with open(bloom_user_path, 'w') as f:
                f.write(' ')
            warning("If you want to have bloom store it in the future remove the ~/.bloom_user file.")
    # Get the github password
    gh_password = getpass.getpass("github password (This is not stored):")
    if not gh_password or not gh_username:
        error("Either the github username or github password is not set.")
        warning("Skipping the pull request...")
        return
    # Check for fork
    info(fmt("@{bf}@!==> @|@!Checking for rosdistro fork on github..."))
    gh_user_repos = fetch_github_api('https://api.github.com/users/{0}/repos'.format(gh_username), use_pagination=True)
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
    title = "{0}: {1} in '{2}' [bloom]".format(repository, version, gh_path)
    body = """\
Increasing version of package(s) in repository `{0}`:
- previous version: `{1}`
- new version: `{2}`
- distro file: `{3}`
- bloom version: `{4}`
""".format(repository, orig_version or 'null', version, gh_path, bloom.__version__)
    with change_directory(temp_dir):
        def _my_run(cmd):
            info(fmt("@{bf}@!==> @|@!" + str(cmd)))
            # out = check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            out = None
            from subprocess import call
            call(cmd, shell=True)
            if out:
                info(out, use_prefix=False)
        if ssh_pull_request:
            rosdistro_git_fork = 'git@github.com/{0}/{1}.git'.format(gh_username, gh_repo)
        else:
            rosdistro_git_fork = 'https://github.com/{0}/{1}.git'.format(gh_username, gh_repo)
        _my_run('git clone {0}'.format(rosdistro_git_fork))
        with change_directory(gh_repo):
            _my_run('git remote add bloom https://github.com/{0}/{1}.git'.format(gh_org, gh_repo))
            _my_run('git remote update')
            _my_run('git fetch')
            track_branches()
            branches = get_branches()
            new_branch = 'bloom-{repository}-{count}'
            count = 0
            while new_branch.format(repository=repository, count=count) in branches:
                count += 1
            new_branch = new_branch.format(repository=repository, count=count)
            # Final check
            info(fmt("@{cf}Pull Request Title: @{yf}" + title))
            info(fmt("@{cf}Pull Request Body : \n@{yf}" + body))
            msg = fmt("@!Open a @|@{cf}pull request@| @!@{kf}from@| @!'@|@!@{bf}" +
                      "{gh_username}/{gh_repo}:{new_branch}".format(**locals()) +
                      "@|@!' @!@{kf}into@| @!'@|@!@{bf}" +
                      "{gh_org}/{gh_repo}:{gh_branch}".format(**locals()) +
                      "@|@!'?")
            info(msg)
            if not maybe_continue():
                warning("Skipping the pull request...")
                return
            _my_run('git checkout -b {0} bloom/{1}'.format(new_branch, gh_branch))
            with open('{0}'.format(gh_path), 'w') as f:
                info(fmt("@{bf}@!==> @|@!Writing new distribution file: ") + str(gh_path))
                f.write(updated_distro_file_yaml)
            _my_run('git add {0}'.format(gh_path))
            _my_run('git commit -m "{0}"'.format(title))
            _my_run('git push origin {0}'.format(new_branch))
    # Open the pull request
    return create_pull_request(gh_org, gh_repo, gh_username, gh_password, gh_branch, new_branch, title, body)

_original_version = None


def start_summary(track):
    global _original_version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    if 'last_version' not in track_dict or 'release_inc' not in track_dict:
        _original_version = 'null'
    else:
        last_version = track_dict['last_version']  # Actually current version now
        release_inc = track_dict['release_inc']
        _original_version = "{0}-{1}".format(last_version, release_inc)


def get_packages():
    with inbranch('upstream'):
        _, _, packages = get_package_data('upstream')
    return packages


def update_summary(track, repository, distro):
    global _original_version
    track_dict = get_tracks_dict_raw()['tracks'][track]
    last_version = track_dict['last_version']  # Actually current version now
    release_inc = track_dict['release_inc']
    version = "{0}-{1}".format(last_version, release_inc)
    summary_file = get_summary_file()
    msg = """\
## {repository} - {version}

User `{user}@{hostname}` released the packages in the `{repository}` repository by running `{cmd}` on `{date}`

""".format(**{
        'repository': repository,
        'date': get_rfc_2822_date(datetime.datetime.now()),
        'user': getpass.getuser(),
        'hostname': socket.gethostname(),
        'cmd': ' '.join(sys.argv),
        'version': version
    })
    packages = [p.name for p in get_packages().values()]
    if len(packages) > 1:
        msg += "These packages were released:\n"
        for p in sorted(packages):
            msg += "- `{0}`\n".format(p)
    else:
        package_name = packages[0]
        msg += "The `{0}` package was released.\n".format(package_name)
    ignored_packages = get_ignored_packages()
    if ignored_packages:
        msg += "\nThese packages were explicitly ignored:\n"
        for ip in ignored_packages:
            msg += "- `{0}`\n".format(ip)
    summary_file = get_summary_file()
    release_file = get_distribution_file(distro)
    reps = release_file.repositories
    distro_version = None
    if repository in reps and reps[repository].release_repository is not None:
        distro_version = reps[repository].release_repository.version
    msg += """
Version of package(s) in repository `{repo}`:
- rosdistro version: `{rosdistro_pv}`
- old version: `{old_pv}`
- new version: `{new_pv}`

Versions of tools used:
- bloom version: `{bloom_v}`
- catkin_pkg version: `{catkin_pkg_v}`
- rosdep version: `{rosdep_v}`
- rosdistro version: `{rosdistro_v}`
- vcstools version: `{vcstools_v}`
""".format(**dict(
        repo=repository,
        rosdistro_pv=distro_version or 'null',
        old_pv=_original_version,
        new_pv=version,
        bloom_v=bloom.__version__,
        catkin_pkg_v=catkin_pkg.__version__,
        # Until https://github.com/ros-infrastructure/rosdistro/issues/16
        rosdistro_v=pkg_resources.require("rosdistro")[0].version,
        rosdep_v=rosdep2.__version__,
        vcstools_v=vcstools.__version__.version
    ))
    summary_file.write(msg)


def perform_release(repository, track, distro, new_track, interactive, pretend, ssh_pull_request):
    release_repo = get_release_repo(repository, distro)
    with change_directory(release_repo.get_path()):
        # Check to see if the old bloom.conf exists
        if check_for_bloom_conf(repository):
            # Convert to a track
            info("Old bloom.conf file detected.")
            info(fmt("@{gf}@!==> @|Converting to bloom.conf to track"))
            convert_old_bloom_conf(None if new_track else distro)
        upconvert_bloom_to_config_branch()
        # Check that the track is valid
        tracks_dict = get_tracks_dict_raw()
        # If new_track, create the new track first
        if new_track:
            if not track:
                error("You must specify a track when creating a new one.", exit=True)
            if track in tracks_dict['tracks']:
                warning("Track '{0}' exists, editing...".format(track))
                edit_track_cmd(track)
                tracks_dict = get_tracks_dict_raw()
            else:
                # Create a new track called <track>,
                # copying an existing track if possible,
                # and overriding the ros_distro
                warning("Creating track '{0}'...".format(track))
                overrides = {'ros_distro': distro}
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
        start_summary(track)
        # Ensure the track is complete
        track_dict = tracks_dict['tracks'][track]
        track_dict = update_track(track_dict)
        tracks_dict['tracks'][track] = track_dict
        # Set the release repositories' remote if given
        release_repo_url = track_dict.get('release_repo_url', None)
        if release_repo_url is not None:
            info(fmt("@{gf}@!==> @|") +
                 "Setting release repository remote url to '{0}'"
                 .format(release_repo_url))
            cmd = 'git remote set-url origin ' + release_repo_url
            info(fmt("@{bf}@!==> @|@!") + str(cmd))
            try:
                subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                error("Setting the remote url failed, exiting.", exit=True)
        # Check for push permissions
        try:
            info(fmt(
                "@{gf}@!==> @|Testing for push permission on release repository"
            ))
            cmd = 'git remote -v'
            info(fmt("@{bf}@!==> @|@!") + str(cmd))
            subprocess.check_call(cmd, shell=True)
            # Dry run will authenticate, but not push
            cmd = 'git push --dry-run'
            info(fmt("@{bf}@!==> @|@!") + str(cmd))
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            error("Cannot push to remote release repository.", exit=True)
        # Write the track config before releasing
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
        # Commit the summary
        update_summary(track, repository, distro)
        commit_summary()
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
             .format(get_disitrbution_file_url(distro)))
        try:
            pull_request_url = open_pull_request(track, repository, distro, ssh_pull_request)
            if pull_request_url:
                info(fmt(_success) + "Pull request opened at: {0}".format(pull_request_url))
                if 'BLOOM_NO_WEBBROWSER' in os.environ and platform.system() not in ['Darwin']:
                    webbrowser.open(pull_request_url)
            else:
                info("The release of your packages was successful, but the pull request failed.")
                info("Please manually open a pull request by editing the file here: '{0}'"
                     .format(get_disitrbution_file_url(distro)))
                info(fmt(_error) + "No pull request opened.")
        except Exception as e:
            debug(traceback.format_exc())
            error("Failed to open pull request: {0} - {1}".format(type(e).__name__, e), exit=True)


def get_argument_parser():
    parser = argparse.ArgumentParser(description="Releases a repository which already exists in the ROS distro file.")
    add = parser.add_argument
    add('repository', help="repository to run bloom on")
    add('--list-tracks', '-l', action='store_true', default=False,
        help="list available tracks for repository")
    add('--track', '-t', required=True, help="track to run")
    add('--non-interactive', '-y', action='store_true', default=False)
    add('--ros-distro', '--rosdistro', '-r', required=True,
        help="determines the ROS distro file used")
    add('--new-track', '--edit-track', '-n', '-e', action='store_true', default=False,
        help="if used, a new track will be created before running bloom")
    add('--pretend', '-p', default=False, action='store_true',
        help="Pretends to push and release")
    add('--no-web', default=False, action='store_true',
        help="prevents a web browser from being opened at the end")
    add('--ssh-pr', default=False, action='store_true',
        help="Do rosdistro updates using ssh keys")
    return parser

_quiet = False


def main(sysargs=None):
    parser = get_argument_parser()
    parser = add_global_arguments(parser)
    args = parser.parse_args(sysargs)
    handle_global_arguments(args)

    if args.list_tracks:
        list_tracks(args.repository, args.ros_distro)
        return

    if args.no_web:
        os.environ['BLOOM_NO_WEBBROWSER'] = '1'

    try:
        os.environ['BLOOM_TRACK'] = args.track
        disable_git_clone(True)
        quiet_git_clone_warning(True)
        perform_release(args.repository, args.track, args.ros_distro,
                        args.new_track, not args.non_interactive, args.pretend,
                        args.ssh_pr)
    except (KeyboardInterrupt, EOFError) as exc:
        error("\nReceived '{0}', aborting.".format(type(exc).__name__))
