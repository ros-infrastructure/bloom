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

import datetime
import re
import textwrap

from dateutil import tz
from distutils.version import LooseVersion
from time import strptime

from bloom.generators.common import PackageManagerGenerator
from bloom.generators.common import process_template_files

from bloom.logging import enable_drop_first_log_prefix
from bloom.logging import error
from bloom.logging import info

from bloom.util import execute_command

# Drop the first log prefix for this command
enable_drop_first_log_prefix(True)


def format_depends(depends, resolved_deps):
    versions = {
        'version_lt': '<',
        'version_lte': '<=',
        'version_eq': '=',
        'version_gte': '>=',
        'version_gt': '>'
    }
    formatted = []
    for d in depends:
        for resolved_dep in resolved_deps[d.name]:
            version_depends = [k
                               for k in versions.keys()
                               if getattr(d, k, None) is not None]
            if not version_depends:
                formatted.append(resolved_dep)
            else:
                for v in version_depends:
                    formatted.append("{0} {1} {2}".format(
                        resolved_dep, versions[v], getattr(d, v)))
    return formatted


def format_description(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = '\n'.join([v.strip() for v in
                      textwrap.TextWrapper(width=80, break_long_words=False, replace_whitespace=False).wrap(value)])
    return value


class RpmGenerator(PackageManagerGenerator):
    title = 'rpm'
    package_manager = 'rpm'
    description = "Generates RPMs from the catkin meta data"

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('--os-name', default='fedora',
            help="overrides os_name, set to 'fedora' by default")
        return PackageManagerGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.os_name = args.os_name
        ret = PackageManagerGenerator.handle_arguments(self, args)
        return ret

    def pre_modify(self):
        error_msg = ''.join([
            "Some of the dependencies for packages in this repository could not be resolved by rosdep.\n",
            "You can try to address the issues which appear above and try again if you wish, ",
            "or continue without releasing into RPM-based distributions (e.g. Fedora 24)."
        ])
        PackageManagerGenerator.check_all_keys_are_valid(self, error_msg)

        for package in self.packages.values():
            if not package.licenses or not package.licenses[0]:
                error("No license set for package '{0}', aborting.".format(package.name), exit=True)

    def generate_package(self, package, os_version):
        info("Generating {0} for {1}...".format(self.package_manager, os_version))
        # Generate substitution values
        subs = self.get_subs(package, os_version, format_description, format_depends)
        # Use subs to create and store releaser history
        self.set_releaser_history(dict(subs['changelogs']))
        # Template files
        template_files = process_template_files('.', subs, self.package_manager)
        # Remove any residual template files
        execute_command('git rm -rf ' + ' '.join("'{}'".format(t) for t in template_files))
        # Add marker file to tell mock to archive the sources
        open('.write_tar', 'a').close()
        # Add marker file changes to the rpm folder
        execute_command('git add .write_tar ' + self.package_manager)
        # Commit changes
        execute_command('git commit -m "Generated {0} files for {1}"'
                        .format(self.package_manager, os_version))
        # Rename the template spec file
        execute_command('git mv {0}/template.spec {1}/{2}.spec'
                        .format(self.package_manager, self.package_manager, subs['Package']))
        # Commit changes
        execute_command('git commit -m "Renamed {0} spec files for {1}"'
                        .format(self.package_manager, os_version))
        # Return the subs for other use
        return subs

    @staticmethod
    def get_subs_hook(subs, package, rosdistro, releaser_history=None):
        # Use the time stamp to set the date strings
        stamp = datetime.datetime.now(tz.tzlocal())
        subs['Date'] = stamp.strftime('%a %b %d %Y')
        # Maintainers
        maintainers = []
        for m in package.maintainers:
            maintainers.append(str(m))
        # Changelog
        if releaser_history:
            sorted_releaser_history = sorted(releaser_history,
                                             key=lambda k: LooseVersion(k), reverse=True)
            sorted_releaser_history = sorted(sorted_releaser_history,
                                             key=lambda k: strptime(releaser_history.get(k)[0], '%a %b %d %Y'),
                                             reverse=True)
            changelogs = [(v, releaser_history[v]) for v in sorted_releaser_history]
        else:
            # Ensure at least a minimal changelog
            changelogs = []
        if package.version + '-' + str(subs['Inc']) not in [x[0] for x in changelogs]:
            changelogs.insert(0, (
                package.version + '-' + str(subs['Inc']), (
                    subs['Date'],
                    package.maintainers[0].name,
                    package.maintainers[0].email
                )
            ))
        exported_tags = [e.tagname for e in package.exports]
        subs['NoArch'] = 'metapackage' in exported_tags or 'architecture_independent' in exported_tags
        subs['changelogs'] = changelogs

        # License
        if not package.licenses or not package.licenses[0]:
            error("No license set for package '{0}', aborting.".format(package.name), exit=True)
        subs['License'] = package.licenses[0]

        return subs

    def generate_tag_name(self, subs):
        tag_name = '{Package}-{Version}-{Inc}_{Distribution}'
        tag_name = self.package_manager + '/' + tag_name.format(**subs)
        return tag_name
