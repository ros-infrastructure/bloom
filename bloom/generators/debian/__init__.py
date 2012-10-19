from __future__ import print_function

import datetime
import json
import os
import pkg_resources
import re
import shutil
import sys

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_branches
from bloom.git import get_commit_hash
from bloom.git import get_current_branch
from bloom.git import has_changes
from bloom.git import show
from bloom.git import tag_exists

from bloom.logging import ansi
from bloom.logging import enable_drop_first_log_prefix
enable_drop_first_log_prefix(True)
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

from bloom.commands.patch.common import get_patch_config
from bloom.commands.patch.common import set_patch_config
from bloom.commands.patch.remove_cmd import remove_patches

from bloom.util import change_directory
from bloom.util import code
from bloom.util import execute_command
from bloom.util import get_package_data
from bloom.util import maybe_continue

try:
    from rosdep2.platforms.debian import APT_INSTALLER
    from rosdep2.catkin_support import get_ubuntu_targets
except ImportError as err:
    error("rosdep was not detected, please install it.")
    sys.exit(code.ROSDEP_NOT_FOUND)

try:
    import em
except ImportError:
    error("empy was not detected, please install it.")
    sys.exit(code.EMPY_NOT_FOUND)


def match_branches_with_prefix(prefix, get_branches):
    branches = []
    # Match branches
    existing_branches = get_branches()
    for branch in existing_branches:
        if branch.startswith('remotes/origin/'):
            branch = branch.split('/', 2)[-1]
        if branch.startswith(prefix):
            branches.append(branch)
    return list(set(branches))


def get_stackage_from_branch(branch):
    with inbranch(branch):
        package_data = get_package_data(branch)
        if type(package_data) not in [list, tuple]:
            # It is a ret code
            DebianGenerator.exit(package_data)
    name, version, packages = package_data
    if type(name) is list and len(name) > 1:
        error("Debian generator does not support generating "
              "from branches with multiple packages in them, use "
              "the release generator first to split packages into "
              "individual branches.")
        DebianGenerator.exit(code.DEBIAN_MULTIPLE_PACKAGES_FOUND)
    if type(packages) is dict:
        return packages.values()[0], 'package'
    return packages, 'stack'


def debianize_string(value):
    markup_remover = re.compile(r'<.*?>')
    value = markup_remover.sub('', value)
    value = re.sub('\s+', ' ', value)
    value = value.strip()
    return value


def is_meta_package(package):
    metapack = [True for e in package.exports if e.tagname == 'metapackage']
    if len(metapack) > 0:
        return True
    else:
        return False


def sanitize_package_name(name):
    return name.replace('_', '-')


class DebianGenerator(BloomGenerator):
    title = 'debian'
    description = "Generates debians from the catkin meta data"
    has_run_rosdep = False
    default_install_prefix = '/usr/local'
    # TODO: defaults to 'groovy' rosdistro, make it rosdistro independent
    rosdistro = 'groovy'

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-i', '--debian-inc', help="debian increment number", default='0')
        add('-p', '--prefix', required=True,
            help="branch prefix to match, and from which create debians"
                 " hint: if you want to match 'release/foo' use 'release'")
        add('--distros', nargs='+', required=False, default=[],
            help='A list of debian distros to generate for')
        add('--install-prefix', default=None,
            help="overrides the default installation prefix")
        add('--os-name', default='ubuntu',
            help="overrides os_name, set to 'debian' for vanilla distros")

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.debian_inc = args.debian_inc
        self.os_name = args.os_name
        self.distros = args.distros
        if self.distros in [None, []]:
            self.distros = get_ubuntu_targets(self.rosdistro)
        self.install_prefix = args.install_prefix
        if args.install_prefix is None:
            self.install_prefix = self.default_install_prefix
        self.prefix = args.prefix
        self.branches = match_branches_with_prefix(self.prefix, get_branches)
        if len(self.branches) == 0:
            error("No packages found, check your --prefix or --src arguments.")
            return code.NO_PACKAGE_XML_FOUND
        self.packages = {}
        self.tag_names = {}
        self.names = []
        self.branch_args = []
        for branch in self.branches:
            stackage, kind = get_stackage_from_branch(branch)
            self.packages[stackage.name] = (stackage, kind)
            self.names.append(stackage.name)
            args = self.generate_branching_arguments(stackage, branch)
            self.branch_args.extend(args)

    def summarize(self):
        info("Generating source debs for the packages: " + str(self.names))
        info("Debian Incremental Version: " + str(self.debian_inc))
        info("Debian Distributions: " + str(self.distros))

    def get_branching_arguments(self):
        return self.branch_args

    def pre_branch(self, destination, source):
        # Run rosdep update is needed
        if not self.has_run_rosdep:
            info("Running 'rosdep update'...")
            from rosdep2.catkin_support import update_rosdep
            update_rosdep()
            self.has_run_rosdep = True
        # Determine the current package being generated
        name = destination.split('/')[-1]
        distro = destination.split('/')[-2]
        # Retrieve the stackage
        stackage, kind = self.packages[name]
        # Report on this package
        self.summarize_package(stackage, kind, distro)

    def pre_rebase(self, destination):
        # Get the stored configs is any
        patches_branch = 'patches/' + destination
        config = self.load_original_config(patches_branch)
        if config is not None:
            set_patch_config(patches_branch, config)
        # Remove back to the base
        remove_patches()

    def post_rebase(self, destination):
        # Determine the current package being generated
        name = destination.split('/')[-1]
        distro = destination.split('/')[-2]
        # Retrieve the stackage
        stackage, kind = self.packages[name]
        # Ask to continue if interactive
        if self.interactive:
            if not maybe_continue('y'):
                error("Answered no to continue, aborting.")
                return code.ANSWERED_NO_TO_CONTINUE
        ### Start debian generation
        # Get time of day
        from dateutil import tz
        stamp = datetime.datetime.now(tz.tzlocal())
        # Convert stackage to debian data
        data = self.convert_stackage_to_debian_data(stackage, kind)
        # Get apt_installer from rosdep
        from rosdep2.catkin_support import get_installer
        self.apt_installer = get_installer(APT_INSTALLER)
        # Create debians for each distro
        with inbranch(destination):
            self.generate_debian(data, stamp, distro)
            # Create the tag name for later
            self.tag_names[destination] = self.generate_tag_name(data)
        # Update the patch configs
        patches_branch = 'patches/' + destination
        config = get_patch_config(patches_branch)
        # Store it
        self.store_original_config(config, patches_branch)
        # Modify the base so import/export patch works
        config['base'] = get_commit_hash(get_current_branch())
        # Set it
        set_patch_config(patches_branch, config)

    def post_patch(self, destination, color='bluef'):
        # Tag after patches have been applied
        with inbranch(destination):
            # Tag
            tag_name = self.tag_names[destination]
            if tag_exists(tag_name):
                if self.interactive:
                    warning("Tag exists: " + tag_name)
                    warning("Do you wish to overwrite it?")
                    if not maybe_continue('y'):
                        error("Answered no to continue, aborting.")
                        return code.ANSWERED_NO_TO_CONTINUE
                else:
                    warning("Overwriting tag: " + tag_name)
            else:
                info("Creating tag: " + tag_name)
            execute_command('git tag -f ' + tag_name)
        # Report of success
        name = destination.split('/')[-1]
        stackage, kind = self.packages[name]
        distro = destination.split('/')[-2]
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### " + ansi('greenf') + "Successfully" + \
            ansi(color) + " generated '" + ansi('boldon') + distro + \
            ansi('boldoff') + "' debian for " + kind + \
            " '" + ansi('boldon') + stackage.name + ansi('boldoff') + "'" + \
            " at version '" + ansi('boldon') + stackage.version + \
            "-" + str(self.debian_inc) + ansi('boldoff') + "'" + \
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####\n" + ansi('reset'), use_prefix=False)

    def store_original_config(self, config, patches_branch):
        with inbranch(patches_branch):
            with open('debian.store', 'w+') as f:
                f.write(json.dumps(config))
            execute_command('git add debian.store')
            if has_changes():
                execute_command('git commit -m "Store original patch config"')

    def load_original_config(self, patches_branch):
        config_store = show(patches_branch, 'debian.store')
        if config_store is None:
            return config_store
        return json.loads(config_store)

    def summarize_dependency_mapping(self, data, deps, build_deps):
        if len(deps) == 0 and len(build_deps) == 0:
            return
        info("Package '" + data['Package'] + "' has dependencies:")
        header = "  " + ansi('boldoff') + ansi('ulon') + \
                 "rosdep key           => " + data['Distribution'] + \
                 " key" + ansi('reset')
        template = "  " + ansi('cyanf') + "{0:<20} " + ansi('purplef') + \
                   "=> " + ansi('cyanf') + "{1}" + ansi('reset')
        if len(deps) != 0:
            info(ansi('purplef') + "Run Dependencies:" + \
                 ansi('reset'))
            info(header)
            for key in deps:
                info(template.format(key, data['Depends'][key]))
        if len(build_deps) != 0:
            info(ansi('purplef') + \
                 "Build and Build Tool Dependencies:" + ansi('reset'))
            info(header)
            for key in build_deps:
                info(template.format(key, data['BuildDepends'][key]))

    def generate_debian(self, data, stamp, debian_distro):
        info("Generating debian for {0}...".format(debian_distro))
        # Resolve dependencies
        deps = data['Depends']
        build_deps = data['BuildDepends']
        data = self.resolve_dependencies(data, debian_distro)
        # Set the distribution
        data['Distribution'] = debian_distro
        # Use the time stamp to set the date strings
        data['Date'] = stamp.strftime('%a, %d %b %Y %T %z')
        data['YYYY'] = stamp.strftime('%Y')
        self.summarize_dependency_mapping(data, deps, build_deps)
        deps_list = []
        for dep in data['Depends'].values():
            deps_list.extend(dep)
        data['Depends'] = deps_list
        build_deps_list = []
        for dep in data['BuildDepends'].values():
            build_deps_list.extend(dep)
        data['BuildDepends'] = build_deps_list
        # Create/Clean the debian folder
        debian_dir = 'debian'
        if os.path.exists(debian_dir):
            if self.interactive:
                warning("Debian directory exists: " + debian_dir)
                warning("Do you wish to overwrite it?")
                if not maybe_continue('y'):
                    error("Answered no to continue, aborting.")
                    return code.ANSWERED_NO_TO_CONTINUE
            else:
                warning("Overwriting Debian directory: " + debian_dir)
            execute_command('git rm -rf ' + debian_dir)
            execute_command('git commit -m "Clearing previous debian folder"')
            if os.path.exists(debian_dir):
                shutil.rmtree(debian_dir)
        os.makedirs(debian_dir)
        # Generate the control file from the template
        self.create_from_template('control', data, debian_dir)
        # Generate the changelog file
        self.create_from_template('changelog', data, debian_dir)
        # Generate the rules file
        if data['BuildType'] == 'cmake':
            self.create_from_template('rules.cmake', data, debian_dir,
                                      chmod=0755, outfile='rules')
        elif data['BuildType'] == 'metapackage':
            self.create_from_template('rules.metapackage', data, debian_dir,
                                      chmod=0755, outfile='rules')
        else:
            error("Unrecognized BuildType (" + data['BuildType'] + \
                  ") for package: " + data['Name'])
            return code.DEBIAN_UNRECOGNIZED_BUILD_TYPE
        # Generate the gbp.conf file
        self.create_from_template('gbp.conf', data, debian_dir)
        # Create the compat file
        compat_path = os.path.join(debian_dir, 'compat')
        with open(compat_path, 'w+') as f:
            print("7", file=f)
        # Create the source/format file
        source_dir = os.path.join(debian_dir, 'source')
        os.makedirs(source_dir)
        format_path = os.path.join(source_dir, 'format')
        with open(format_path, 'w+') as f:
            print("3.0 (quilt)", file=f)
        # Commit results
        execute_command('git add ' + debian_dir)
        execute_command('git commit -m "Generated debian files for ' + \
                        debian_distro + '"')

    def create_from_template(self, template_name, data, directory,
                             chmod=None, outfile=None):
        # Configure template name
        extention = '.em'
        if not template_name.endswith(extention):
            template_file = template_name + extention
        else:
            template_file = template_name
            template_name = template_name[:len(extention)]
        template_path = os.path.join('templates', template_file)
        # Get the template contents using pkg_resources
        group = 'bloom.generators.debian'
        # info("Looking for template: " + group + ':' + template_path)
        try:
            template = pkg_resources.resource_string(group, template_path)
        except IOError as err:
            error("Failed to load template "
                  "'{0}': {1}".format(template_name, str(err)))
            self.exit(code.DEBIAN_FAILED_TO_LOAD_TEMPLATE)
        # Expand template
        outfile = outfile if outfile is not None else template_name
        info("Expanding template: '" + template_file + "' to '" + \
             outfile + "'")
        result = em.expand(template, **data)
        # Write the template out
        with change_directory(directory):
            with open(outfile, 'w+') as f:
                f.write(result)
            # Set permissions if needed
            if chmod is not None:
                os.chmod(outfile, chmod)

    def resolve_dependencies(self, data, debian_distro):
        os_name = self.os_name
        rosdep_view = self.get_rosdep_view(debian_distro, os_name)

        def resolve_rosdep_key(rosdep_key):
            from rosdep2.catkin_support import resolve_for_os
            from rosdep2.lookup import ResolutionError
            try:
                return resolve_for_os(rosdep_key, rosdep_view,
                                      self.apt_installer, os_name,
                                      debian_distro)
            except KeyError:
                error("Could not resolve rosdep key '" + rosdep_key + "'")
                self.exit(code.DEBIAN_NO_SUCH_ROSDEP_KEY)
            except ResolutionError as err:
                error("Could not resolve the rosdep key '" + rosdep_key + \
                      "' for distro '" + debian_distro + "': \n")
                print(str(err))
                self.exit(code.DEBIAN_NO_ROSDEP_KEY_FOR_DISTRO)

        resolved_depends = {}
        for rosdep_key in data['Depends']:
            resolved_depends[rosdep_key] = resolve_rosdep_key(rosdep_key)
        data['Depends'] = resolved_depends
        resolved_build_depends = {}
        for rosdep_key in data['BuildDepends']:
            resolved_build_depends[rosdep_key] = resolve_rosdep_key(rosdep_key)
        data['BuildDepends'] = resolved_build_depends
        return data

    def get_rosdep_view(self, debian_distro, os_name):
        rosdistro = self.rosdistro
        from rosdep2.catkin_support import get_catkin_view
        return get_catkin_view(rosdistro, os_name, debian_distro, update=False)

    def convert_package_to_debian_data(self, package):
        data = {}
        # Name, Version, Description
        data['Name'] = package.name
        data['Version'] = package.version
        data['Description'] = debianize_string(package.description)
        # Websites
        websites = [str(url) for url in package.urls if url.type == 'website']
        homepage = websites[0] if websites else ''
        if homepage == '':
            warning("No homepage set, defaulting to ''")
        data['Homepage'] = homepage
        # Build rule templates
        if is_meta_package(package):
            data['BuildType'] = 'metapackage'
        else:
            data['BuildType'] = 'cmake'
        # Debian Increment Number
        data['DebianInc'] = self.debian_inc
        # Package name
        data['Package'] = self.get_stackage_name(package)
        # Installation prefix
        data['InstallationPrefix'] = self.install_prefix
        # Dependencies
        data['Depends'] = set([d.name for d in package.run_depends])
        build_deps = (package.build_depends + package.buildtool_depends)
        data['BuildDepends'] = set([d.name for d in build_deps])
        # Maintainers
        maintainers = []
        for m in package.maintainers:
            maintainers.append(str(m))
        data['Maintainer'] = ', '.join(maintainers)
        return data

    def convert_stack_to_debian_data(self, stack):
        data = {}
        # Name, Version, Description
        data['Name'] = stack.name
        data['Version'] = stack.version
        data['Description'] = debianize_string(stack.description)
        # Website
        data['Homepage'] = stack.url
        # Build rule template
        data['BuildType'] = 'cmake'
        # Copyright
        data['Copyright'] = stack.copyright
        # Debian Increment Number
        data['DebianInc'] = self.debian_inc
        # Package name
        data['Package'] = self.get_stackage_name(stack)
        # Installation prefix
        data['InstallationPrefix'] = self.install_prefix
        # Dependencies
        data['Depends'] = set([d.name for d in stack.depends])
        data['BuildDepends'] = set([d.name for d in stack.build_depends])
        # Maintainers
        maintainers = []
        for m in stack.maintainers:
            maintainer = m.name
            if m.email:
                maintainer += ' <%s>' % m.email
            maintainers.append(maintainer)
        data['Maintainer'] = ', '.join(maintainers)
        ### Augment Description with Package list
        # Go over the different subfolders and find all the packages
        package_descriptions = {}
        # search for manifest in current folder and direct subfolders
        cwd = os.getcwd()
        for dir_name in [cwd] + os.listdir(cwd):
            if not os.path.isdir(dir_name):
                continue
            dir_path = os.path.join('.', dir_name)
            for file_name in os.listdir(dir_path):
                if file_name == 'manifest.xml':
                    # Can cold import,
                    # because bloom.util already checked for rospkg
                    import rospkg
                    # parse the manifest, in case it is not valid
                    manifest = rospkg.parse_manifest_file(dir_path, file_name)
                    # remove markups
                    if manifest.description is None:
                        manifest.description = ''
                    description = debianize_string(manifest.description)
                    if dir_name == '.':
                        dir_name = stack.name
                    package_descriptions[dir_name] = description
        # Enhance the description with the list of packages in the stack
        if package_descriptions:
            if data['Description']:
                data['Description'] += '\n .\n'
            data['Description'] += ' This stack contains the packages:'
            for name, description in package_descriptions.items():
                data['Description'] += '\n * %s: %s' % (name, description)
        return data

    def get_stackage_name(self, stackage):
        return sanitize_package_name(str(stackage.name))

    def convert_stackage_to_debian_data(self, stackage, kind):
        if kind == 'package':
            return self.convert_package_to_debian_data(stackage)
        if kind == 'stack':
            return self.convert_stack_to_debian_data(stackage)

    def generate_tag_name(self, data):
        tag_name = '{Package}_{Version}-{DebianInc}_{Distribution}'
        tag_name = 'debian/' + tag_name.format(**data)
        return tag_name

    def generate_branching_arguments(self, stackage, branch):
        n = stackage.name
        return [['debian/' + d + '/' + n, branch, False] for d in self.distros]

    def summarize_package(self, stackage, kind, distro, color='bluef'):
        info(ansi(color) + "\n####" + ansi('reset'), use_prefix=False)
        info(
            ansi(color) + "#### Generating '" + ansi('boldon') + distro + \
            ansi('boldoff') + "' debian for " + kind + \
            " '" + ansi('boldon') + stackage.name + ansi('boldoff') + "'" + \
            " at version '" + ansi('boldon') + stackage.version + \
            "-" + str(self.debian_inc) + ansi('boldoff') + "'" + \
            ansi('reset'),
            use_prefix=False
        )
        info(ansi(color) + "####" + ansi('reset'), use_prefix=False)
