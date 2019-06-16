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
import os
import re
import sys
import traceback

from dateutil import tz
from pkg_resources import parse_version

from bloom.generators.common import PackageManagerGenerator
from bloom.generators.common import process_template_files

from bloom.logging import debug
from bloom.logging import enable_drop_first_log_prefix
from bloom.logging import error
from bloom.logging import info
from bloom.logging import is_debug
from bloom.logging import warning

from bloom.util import to_unicode
from bloom.util import execute_command
from bloom.util import get_rfc_2822_date
from bloom.util import maybe_continue

try:
    from catkin_pkg.changelog import get_changelog_from_path
    from catkin_pkg.changelog import CHANGELOG_FILENAME
except ImportError as err:
    debug(traceback.format_exc())
    error("catkin_pkg was not detected, please install it.", exit=True)

# Drop the first log prefix for this command
enable_drop_first_log_prefix(True)


def format_depends(depends, resolved_deps):
    versions = {
        'version_lt': '<<',
        'version_lte': '<=',
        'version_eq': '=',
        'version_gte': '>=',
        'version_gt': '>>'
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
                    formatted.append("{0} ({1} {2})".format(
                        resolved_dep, versions[v], getattr(d, v)))
    return formatted


def debianize_string(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = value.strip()
    return value


def format_description(value):
    """
    Format proper <synopsis, long desc> string following Debian control file
    formatting rules. Treat first line in given string as synopsis, everything
    else as a single, large paragraph.

    Future extensions of this function could convert embedded newlines and / or
    html into paragraphs in the Description field.

    https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Description
    """
    value = debianize_string(value)
    # NOTE: bit naive, only works for 'properly formatted' pkg descriptions (ie:
    #       'Text. Text'). Extra space to avoid splitting on arbitrary sequences
    #       of characters broken up by dots (version nrs fi).
    parts = value.split('. ', 1)
    if len(parts) == 1 or len(parts[1]) == 0:
        # most likely single line description
        return value
    # format according to rules in linked field documentation
    return u"{0}.\n {1}".format(parts[0], parts[1].strip())


def get_changelogs(package, releaser_history=None):
    if releaser_history is None:
        warning("No historical releaser history, using current maintainer name "
                "and email for each versioned changelog entry.")
        releaser_history = {}
    if is_debug():
        import logging
        logging.basicConfig()
        import catkin_pkg
        catkin_pkg.changelog.log.setLevel(logging.DEBUG)
    package_path = os.path.abspath(os.path.dirname(package.filename))
    changelog_path = os.path.join(package_path, CHANGELOG_FILENAME)
    if os.path.exists(changelog_path):
        changelog = get_changelog_from_path(changelog_path)
        changelogs = []
        maintainer = (package.maintainers[0].name, package.maintainers[0].email)
        for version, date, changes in changelog.foreach_version(reverse=True):
            changes_str = []
            date_str = get_rfc_2822_date(date)
            for item in changes:
                changes_str.extend(['  ' + i for i in to_unicode(item).splitlines()])
            # Each entry has (version, date, changes, releaser, releaser_email)
            releaser, email = releaser_history.get(version, maintainer)
            changelogs.append((
                version, date_str, '\n'.join(changes_str), releaser, email
            ))
        return changelogs
    else:
        warning("No {0} found for package '{1}'"
                .format(CHANGELOG_FILENAME, package.name))
        return []


class DebianGenerator(PackageManagerGenerator):
    title = 'debian'
    package_manager = 'debian'
    description = "Generates debians from the catkin meta data"

    def prepare_arguments(self, parser):
        add = parser.add_argument
        add('--os-name', default='ubuntu',
            help="overrides os_name, set to 'ubuntu' by default")
        add('--os-not-required', default=False, action="store_true",
            help="Do not error if this os is not in the platforms "
                 "list for rosdistro")
        return PackageManagerGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.os_name = args.os_name
        self.os_not_required = args.os_not_required
        ret = PackageManagerGenerator.handle_arguments(self, args)
        return ret

    def pre_modify(self):
        error_msg = ''.join([
            "Some of the dependencies for packages in this repository could not be resolved by rosdep.\n",
            "You can try to address the issues which appear above and try again if you wish."
        ])
        PackageManagerGenerator.check_all_keys_are_valid(self, error_msg)

    def generate_package(self, package, os_version):
        info("Generating {0} for {1}...".format(self.package_manager, os_version))
        # Try to retrieve the releaser_history
        releaser_history = self.get_releaser_history()
        # Generate substitution values
        subs = self.get_subs(package, os_version, format_description, format_depends, releaser_history)
        # Use subs to create and store releaser history
        releaser_history = [(v, (n, e)) for v, _, _, n, e in subs['changelogs']]
        self.set_releaser_history(dict(releaser_history))
        # Template files
        template_files = process_template_files(".", subs, self.package_manager)
        # Remove any residual template files
        execute_command('git rm -rf ' + ' '.join("'{}'".format(t) for t in template_files))
        # Add changes to the package system folder
        execute_command('git add {0}'.format(self.package_manager))
        # Commit changes
        execute_command('git commit -m "Generated {0} files for {1}"'
                        .format(self.package_manager, os_version))
        # Return the subs for other use
        return subs

    @staticmethod
    def get_subs_hook(subs, package, rosdistro, releaser_history=None):
        # Use the time stamp to set the date strings
        stamp = datetime.datetime.now(tz.tzlocal())
        subs['Date'] = stamp.strftime('%a, %d %b %Y %T %z')
        subs['YYYY'] = stamp.strftime('%Y')

        # Changelog
        changelogs = get_changelogs(package, releaser_history)
        if changelogs and package.version not in [x[0] for x in changelogs]:
            warning("")
            warning("A CHANGELOG.rst was found, but no changelog for this version was found.")
            warning("You REALLY should have a entry (even a blank one) for each version of your package.")
            warning("")
        if not changelogs:
            # Ensure at least a minimal changelog
            changelogs = []
        if package.version not in [x[0] for x in changelogs]:
            changelogs.insert(0, (
                package.version,
                get_rfc_2822_date(datetime.datetime.now()),
                '  * Autogenerated, no changelog for this version found in CHANGELOG.rst.',
                package.maintainers[0].name,
                package.maintainers[0].email
            ))
        bad_changelog = False
        # Make sure that the first change log is the version being released
        if package.version != changelogs[0][0]:
            error("")
            error("The version of the first changelog entry '{0}' is not the "
                  "same as the version being currently released '{1}'."
                  .format(package.version, changelogs[0][0]))
            bad_changelog = True
        # Make sure that the current version is the latest in the changelog
        for changelog in changelogs:
            if parse_version(package.version) < parse_version(changelog[0]):
                error("")
                error("There is at least one changelog entry, '{0}', which has a "
                      "newer version than the version of package '{1}' being released, '{2}'."
                      .format(changelog[0], package.name, package.version))
                bad_changelog = True
        if bad_changelog:
            error("This is almost certainly by mistake, you should really take a "
                  "look at the changelogs for the package you are releasing.")
            error("")
            if not maybe_continue('n', 'Continue anyways'):
                sys.exit("User quit.")
        subs['changelogs'] = changelogs

        # Use debhelper version 7 for oneric, otherwise 9
        subs['debhelper_version'] = 7 if subs['Distribution'] in ['oneiric'] else 9

        # Copyright
        licenses = []
        separator = '\n' + '=' * 80 + '\n\n'
        for l in package.licenses:
            if hasattr(l, 'file') and l.file is not None:
                license_file = os.path.join(os.path.dirname(package.filename), l.file)
                if not os.path.exists(license_file):
                    error("License file '{}' is not found.".
                          format(license_file), exit=True)
                license_text = open(license_file, 'r').read()
                if not license_text.endswith('\n'):
                    license_text += '\n'
                licenses.append(license_text)
        subs['Copyright'] = separator.join(licenses)

        # Handle gbp.conf
        release_tag = 'release/{0}/{1}-{2}'.format(subs['Name'], subs['Version'], subs['Inc'])
        subs['release_tag'] = release_tag

        # Debian Package Format
        subs['format'] = 'quilt'

        return subs

    def generate_tag_name(self, subs):
        tag_name = '{Package}_{Version}{Inc}_{Distribution}'
        tag_name = self.package_manager + '/' + tag_name.format(**subs)
        return tag_name
