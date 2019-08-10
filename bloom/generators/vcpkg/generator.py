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

import re
import traceback

from bloom.generators.common import PackageManagerGenerator
from bloom.generators.common import process_template_files

from bloom.logging import debug
from bloom.logging import enable_drop_first_log_prefix
from bloom.logging import error
from bloom.logging import info

from bloom.util import execute_command

try:
    from catkin_pkg.changelog import get_changelog_from_path
    from catkin_pkg.changelog import CHANGELOG_FILENAME
except ImportError:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.", exit=True)

try:
    import rosdistro
except ImportError:
    debug(traceback.format_exc())
    error("rosdistro was not detected, please install it.", exit=True)

# Drop the first log prefix for this command
enable_drop_first_log_prefix(True)

NORMAL_DEPENDENCY_TEMPLATE = '\t\t<dependency id="{0}"/>\n'
SEMANTIC_VERSION_DEPENDENCY_TEMPLATE = '\t\t<dependency id="{0}" version="{1}"/>\n'


def format_depend(id, version=None):
    if version is None:
        return NORMAL_DEPENDENCY_TEMPLATE.format(id)
    else:
        return SEMANTIC_VERSION_DEPENDENCY_TEMPLATE.format(id, version)


def format_depends(depends, resolved_deps):
    # you can see NuGet's semantic version documents via
    # https://docs.microsoft.com/en-us/nuget/reference/package-versioning#version-ranges-and-wildcards
    versions = {
        'version_lt': '(,{0})',
        'version_lte': '(,{0}]',
        'version_eq': '[{0}]',
        'version_gte': '{0}',
        'version_gt': '({0},)'
    }

    formatted = []
    for d in depends:
        for resolved_dep in resolved_deps[d.name]:
            version_depends = [k
                               for k in versions.keys()
                               if getattr(d, k, None) is not None]
            if not version_depends:
                formatted.append(format_depend(resolved_dep))
            else:
                for v in version_depends:
                    formatted.append(format_depend(resolved_dep, versions[v].format(getattr(d, v))))
    return formatted


def format_description(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)

    parts = value.split('. ', 1)
    if len(parts) == 1 or len(parts[1]) == 0:
        # most likely single line description
        return value
    # format according to rules in linked field documentation
    return u"{0}.\n {1}".format(parts[0], parts[1].strip())


class VcpkgGenerator(PackageManagerGenerator):
    title = 'vcpkg'
    package_manager = 'vcpkg'
    description = "Generates vcpkg from the catkin meta data"

    def prepare_arguments(self, parser):
        add = parser.add_argument
        add('--os-name', default='windows',
            help="overrides os_name, set to 'windows' by default")
        return PackageManagerGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.os_name = args.os_name
        ret = PackageManagerGenerator.handle_arguments(self, args)
        return ret

    def generate_package(self, package, os_version):
        info("Generating {0} for {1}...".format(self.package_manager, os_version))
        # Generate substitution values
        subs = self.get_subs(package, os_version, format_description, format_depends)
        # Template files
        template_files = process_template_files(".", subs, self.package_manager)
        # Remove any residual template files
        execute_command('git rm -rf ' + ' '.join("'{}'".format(t) for t in template_files))
        # Add changes to the package system folder
        execute_command('git add {0}'.format(self.package_manager))
        # Commit changes
        execute_command('git commit -m "Generated {0} files for {1}"'
                        .format(self.package_manager, os_version))
        # Rename the template nuspec file
        execute_command('git mv {0}/template.nuspec {1}/{2}.nuspec'.
                        format(self.package_manager, self.package_manager, subs['Package']))
        # Commit changes
        execute_command('git commit -m "Renamed {0} nuspec files for {1}"'
                        .format(self.package_manager, subs['Package']))
        # Return the subs for other use
        return subs

    @staticmethod
    def get_subs_hook(subs, package, ros_distro, releaser_history=None):
        # Get pacakge's release url from rosdistro repository
        index = rosdistro.get_index(rosdistro.get_index_url())
        distribution_file = rosdistro.get_distribution_file(index, ros_distro)
        try:
            repo = distribution_file.repositories[package.name]
        except KeyError as e:
            # The current package is exist in a meta-package,
            # Notice that the type of distribution_file.repositories is dict
            for meta_repo in distribution_file.repositories.values():
                if package.name in meta_repo.release_repository.package_names:
                    repo = meta_repo
                    break
            else:
                raise e
        release_url = repo.release_repository.url

        vcpkg_support_git_sources = ["github", "gitlab", "bitbucket"]
        for git_source in vcpkg_support_git_sources:
            if git_source in release_url:
                subs['GitSource'] = git_source
                break
        else:
            error("Currently Bloom don't support release url: {0} currently"
                  .format(release_url), exit=True)
        # release url format: https://github.com/<user_name>/<repo_name><maybe .git>
        subs["UserName"] = release_url.split('/')[-2]
        subs["RepoName"] = release_url.split('/')[-1]
        if ".git" in subs["RepoName"]:
            subs["RepoName"] = subs["RepoName"][:-4]

        subs['TagName'] = VcpkgGenerator.generate_tag_name(subs)
        subs['RosDistro'] = ros_distro

        # We only use fist maintainer's name, because full string of maintainer contains
        # '@' in email part, which will cause NuGet parse error
        subs['Authors'] = package.maintainers[0].name

        subs['BuildDependenciesConfig'] = [
            d.replace("<dependency", "<package").replace("version=", "allowedVersions=")
            for d in subs['BuildDepends']
        ]

        return subs

    @staticmethod
    def generate_tag_name(subs):
        tag_name = '{Package}_{Version}-{Inc}_{Distribution}'
        tag_name = VcpkgGenerator.package_manager + '/' + tag_name.format(**subs)
        return tag_name
