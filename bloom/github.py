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

"""
Provides functions for interating with github
"""

from __future__ import print_function

import base64
import datetime
import getpass
import json
import os
import socket
import sys

from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.util import maybe_continue
from bloom.util import safe_input


try:
    # Python2
    from urllib import urlencode
    from urllib2 import HTTPError
    from urllib2 import Request, urlopen
    from urllib2 import URLError
    from urlparse import urlparse
    from urlparse import urlunsplit
except ImportError:
    # Python3
    from urllib.error import HTTPError
    from urllib.error import URLError
    from urllib.parse import urlparse
    from urllib.parse import urlunsplit
    from urllib.request import Request, urlopen

import bloom


def auth_header_from_basic_auth(user, password):
    auth_str = '{0}:{1}'.format(user, password)
    if sys.version_info >= (3, 0):
        auth_str = auth_str.encode()
    b64_encoded = base64.b64encode(auth_str)
    if sys.version_info >= (3, 0):
        b64_encoded = b64_encoded.decode()
    return "Basic {0}".format(b64_encoded)


def auth_header_from_token(username, token):
    # Handle new GitHub personal access tokens
    # which are used with basic authentication.
    if token.startswith('ghp_'):
        return auth_header_from_basic_auth(username, token)
    else:
        return auth_header_from_oauth_token(token)


def auth_header_from_oauth_token(token):
    return "token " + token


def get_bloom_headers(auth=None):
    headers = {}
    headers['Content-Type'] = "application/json;charset=utf-8"
    headers['User-Agent'] = 'bloom ' + bloom.__version__
    if auth:
        headers['Authorization'] = auth
    return headers


def do_github_get_req(path, auth=None, site='api.github.com'):
    return do_github_post_req(path, None, auth, site)


def do_github_post_req(path, data=None, auth=None, site='api.github.com'):
    headers = get_bloom_headers(auth)
    url = urlunsplit(['https', site, path, '', ''])
    if data is None:
        request = Request(url, headers=headers)  # GET
    else:
        data = json.dumps(data)
        if sys.version_info[0] >= 3:
            data = data.encode('utf-8')
        request = Request(url, data=data, headers=headers)  # POST

    try:
        response = urlopen(request, timeout=120)
    except HTTPError as e:
        if e.code in [401]:
            raise GitHubAuthException(str(e) + ' (%s)' % url)
        else:
            raise GithubException(str(e) + ' (%s)' % url)
    except URLError as e:
        raise GithubException(str(e) + ' (%s)' % url)

    return response


def json_loads(resp):
    """Handle parsing json from an HTTP response for both Python 2 and Python 3."""
    try:
        charset = resp.headers.getparam('charset')
        charset = 'utf8' if not charset else charset
    except AttributeError:
        charset = resp.headers.get_content_charset()

    return json.loads(resp.read().decode(charset))


class GithubException(Exception):
    def __init__(self, msg, resp=None):
        if resp:
            msg = "{msg}: {resp.getcode()}".format(**locals())
        else:
            msg = "{msg}: {resp}".format(**locals())
        super(GithubException, self).__init__(msg)
        if resp:
            self.resp = resp


class GitHubAuthException(GithubException):
    def __init__(self, msg):
        super(GithubException, self).__init__(msg)


class Github(object):
    def __init__(self, username, auth, token=None):
        self.username = username
        self.auth = auth
        self.token = token

    def check_token_validity(self, username, token, update_auth=False):
        resp = do_github_get_req('/user', self.auth)
        resp_data = json_loads(resp)
        if resp.getcode() != 200 or 'login' not in resp_data:
            raise GithubException('Token authorization unsuccessful', resp)
        if update_auth:
            self.username = username
            self.token = token

    def get_repo(self, owner, repo):
        resp = do_github_get_req('/repos/{owner}/{repo}'.format(**locals()), auth=self.auth)
        if '{0}'.format(resp.getcode()) not in ['200']:
            raise GithubException(
                "Failed to get information for repository '{owner}/{repo}'".format(**locals()), resp)
        resp_data = json_loads(resp)
        return resp_data

    def list_repos(self, user, start_page=None):
        page = start_page or 1
        repos = []
        while True:
            url = '/users/{user}/repos?page={page}'.format(**locals())
            resp = do_github_get_req(url, auth=self.auth)
            if '{0}'.format(resp.getcode()) not in ['200']:
                raise GithubException(
                    "Failed to list repositories for user '{user}' using url '{url}'".format(**locals()), resp)
            new_repos = json_loads(resp)
            if not new_repos:
                return repos
            repos.extend(new_repos)
            page += 1

    def get_branch(self, owner, repo, branch):
        url = '/repos/{owner}/{repo}/branches/{branch}'.format(**locals())
        resp = do_github_get_req(url, auth=self.auth)
        if '{0}'.format(resp.getcode()) not in ['200']:
            raise GithubException("Failed to get branch information for '{branch}' on '{owner}/{repo}' using '{url}'"
                                  .format(**locals()),
                                  resp)
        return json_loads(resp)

    def list_branches(self, owner, repo, start_page=None):
        page = start_page or 1
        branches = []
        while True:
            url = '/repos/{owner}/{repo}/branches?page={page}&per_page=2'.format(**locals())
            resp = do_github_get_req(url, auth=self.auth)
            if '{0}'.format(resp.getcode()) not in ['200']:
                raise GithubException(
                    "Failed to list branches for '{owner}/{repo}' using url '{url}'".format(**locals()), resp)
            new_branches = json_loads(resp)
            if not new_branches:
                return branches
            branches.extend(new_branches)
            page += 1

    def create_fork(self, parent_org, parent_repo):
        resp = do_github_post_req('/repos/{parent_org}/{parent_repo}/forks'.format(**locals()), {}, auth=self.auth)
        if '{0}'.format(resp.getcode()) not in ['200', '202']:
            raise GithubException(
                "Failed to create a fork of '{parent_org}/{parent_repo}'".format(**locals()), resp)
        return json_loads(resp)

    def list_forks(self, org, repo, start_page=None):
        page = start_page or 1
        forks = []
        while True:
            url = '/repos/{org}/{repo}/forks?page={page}'.format(**locals())
            resp = do_github_get_req(url, auth=self.auth)
            if '{0}'.format(resp.getcode()) not in ['200', '202']:
                raise GithubException(
                    "Failed to list forks of '{org}/{repo}'".format(**locals()), resp)
            new_forks = json_loads(resp)
            if not new_forks:
                return forks
            forks.extend(new_forks)
            page += 1

    def create_pull_request(self, org, repo, branch, fork_org, fork_branch, title, body=""):
        data = {
            'title': title,
            'body': body,
            'head': "{0}:{1}".format(fork_org, fork_branch),
            'base': branch
        }
        resp = do_github_post_req('/repos/{org}/{repo}/pulls'.format(**locals()), data, self.auth)
        if '{0}'.format(resp.getcode()) not in ['200', '201']:
            raise GithubException("Failed to create pull request", resp)
        resp_json = json_loads(resp)
        return resp_json['html_url']


def get_gh_info(url):
    o = urlparse(url)
    if 'raw.github.com' not in o.netloc and 'raw.githubusercontent.com' not in o.netloc:
        return None
    url_paths = o.path.split('/')
    if len(url_paths) < 5:
        return None
    return {'server': 'github.com',
            'org': url_paths[1],
            'repo': url_paths[2],
            'branch': url_paths[3],
            'path': '/'.join(url_paths[4:])}


_gh = None


def get_github_interface(quiet=False):
    def mfa_prompt(oauth_config_path, username):
        """Explain how to create a token for users with Multi-Factor Authentication configured."""
        warning("Receiving 401 when trying to create an oauth token can be caused by the user "
                "having two-factor authentication enabled.")
        warning("If 2FA is enabled, the user will have to create an oauth token manually.")
        warning("A token can be created at https://github.com/settings/tokens")
        warning("The resulting token can be placed in the '{oauth_config_path}' file as such:"
                .format(**locals()))
        info("")
        warning('{{"github_user": "{username}", "oauth_token": "TOKEN_GOES_HERE"}}'
                .format(**locals()))
        info("")

    global _gh
    if _gh is not None:
        return _gh
    # First check to see if the oauth token is stored
    oauth_config_path = os.path.join(os.path.expanduser('~'), '.config', 'bloom')
    config = {}
    if os.path.exists(oauth_config_path):
        with open(oauth_config_path, 'r') as f:
            config = json.loads(f.read())
            token = config.get('oauth_token', None)
            username = config.get('github_user', None)
            if token and username:
                return Github(username, auth=auth_header_from_token(username, token), token=token)
    if not os.path.isdir(os.path.dirname(oauth_config_path)):
        os.makedirs(os.path.dirname(oauth_config_path))
    if quiet:
        return None
    # Ok, now we have to ask for the user name and pass word
    info("")
    warning("Looks like bloom doesn't have an oauth token for you yet.")
    warning("You can create a token by visiting https://github.com/settings/tokens in your browser.")
    warning("For bloom to work the token must have at least `public_repo` scope.")
    warning("If you want bloom to be able to automatically update your fork of ros/rosdistro (recommended)")
    warning("then you must also enable the workflow scope for the token.")
    warning("If you need to unauthorize it, remove it from the 'Tokens' menu in your GitHub account settings.")
    info("")
    if not maybe_continue('y', 'Would you like to enter an access token now'):
        return None
    token = None
    while token is None:
        try:
            username = getpass.getuser()
            username = safe_input("GitHub username [{0}]: ".format(username)) or username
            token = getpass.getpass("GitHub access token: ").strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if not token:
            error("No token was given, aborting.")
            return None
        gh = Github(username, auth=auth_header_from_token(username, token))
        try:
            gh.check_token_validity(username, token, update_auth=True)
            with open(oauth_config_path, 'w') as f:
                config.update({'oauth_token': token, 'github_user': username})
                f.write(json.dumps(config))
            info("The token '{token}' was created and stored in the bloom config file: '{oauth_config_path}'"
                 .format(**locals()))
        except GitHubAuthException as exc:
            error("{0}".format(exc))
            mfa_prompt(oauth_config_path, username)
        except GithubException as exc:
            error("{0}".format(exc))
            info("")
            if hasattr(exc, 'resp') and '{0}'.format(exc.resp.status) in ['401']:
                mfa_prompt(oauth_config_path, username)
            warning("This sometimes fails when the username or password are incorrect, try again?")
            if not maybe_continue():
                return None
    _gh = gh
    return gh
