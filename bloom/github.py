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
import json
import socket


try:
    # Python2
    from urllib import urlencode
    from urllib2 import HTTPError
    from urllib2 import Request, urlopen
    from urllib2 import URLError
    from urlparse import urlunsplit
except ImportError:
    # Python3
    from urllib.error import HTTPError
    from urllib.error import URLError
    from urllib.parse import urlunsplit
    from urllib.request import Request, urlopen

import bloom


def auth_header_from_basic_auth(user, password):
    return "Basic {0}".format(base64.b64encode('{0}:{1}'.format(user, password)))


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
        request = Request(url, data=json.dumps(data), headers=headers)  # POST

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

    def create_new_bloom_authorization(self, note=None, note_url=None, scopes=None, update_auth=False):
        payload = {
            "scopes": ['public_repo'] if scopes is None else scopes,
            "note": note or "bloom-{0} for {1} created on {2}".format(
                bloom.__version__,
                socket.gethostname(),
                datetime.datetime.now().isoformat()),
            "note_url": 'http://bloom.readthedocs.org/' if note_url is None else note_url
        }
        resp = do_github_post_req('/authorizations', payload, self.auth)
        resp_data = json_loads(resp)
        resp_code = '{0}'.format(resp.getcode())
        if resp_code not in ['201', '202'] or 'token' not in resp_data:
            raise GithubException("Failed to create a new oauth authorization", resp)
        token = resp_data['token']
        if update_auth:
            self.auth = auth_header_from_oauth_token(token)
            self.token = token
        return token

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
