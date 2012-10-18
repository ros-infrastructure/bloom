from __future__ import print_function

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_current_branch

from bloom.logging import info

from bloom.util import code
from bloom.util import execute_command
from bloom.util import get_package_data

from bloom.commands.patch.trim_cmd import trim


class ReleaseGenerator(BloomGenerator):
    title = 'release'
    description = """\
Generates a release branch for each of the packages in the source branch.
The common use case for this generator is to produce release/* branches for
each package in the upstream repository, so the source branch should be set to
'upstream' and the prefix set to 'release'.
"""

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-s', '--src', '--source-branch', default=None, dest='src',
            help="git branch to branch from (defaults to 'upstream')")
        add('-n', '--package-name', default=None, dest='name',
            help="name of package being released (use if non catkin project)")
        add('-p', '--prefix', default='release', dest='prefix',
            help="prefix for target branch name(s)")
        BloomGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.prefix = args.prefix
        self.src = args.src if args.src is not None else get_current_branch()
        self.name = args.name

    def summarize(self):
        self.branch_list = self.detect_branches()
        if type(self.branch_list) not in [list, tuple]:
            self.exit(self.branch_list if self.branch_list is not None else 1)
        info(
            "Releasing package" + \
            ('' if len(self.branch_list) == 1 else 's') + ": " + \
            str(self.branch_list)
        )

    def get_branching_arguments(self):
        p, s, i = self.prefix, self.src, self.interactive
        self.branch_args = [['/'.join([p, b]), s, i] for b in self.branch_list]
        return self.branch_args

    def pre_rebase(self, destination):
        name = destination.split('/')[-1]
        info("Releasing package '" + name + "' to: '" + destination + "'")
        ret = trim(undo=True)
        if ret == code.NOTHING_TO_DO:
            return 0
        else:
            return ret

    def post_rebase(self, destination):
        # If self.packages is not a dict then this is a stack
        # and therefore no trim is needed
        if type(self.packages) is not dict:
            return 0
        # Figure out the trim sub dir
        name = destination.split('/')[-1]
        trim_d = [k for k, v in self.packages.iteritems() if v.name == name][0]
        # Execute trim
        if trim_d in ['', '.']:
            return 0
        return trim(trim_d)

    def post_patch(self, destination):
        # Figure out the version of the given package
        with inbranch(destination):
            package_data = get_package_data(destination)
            if type(package_data) not in [list, tuple]:
                return package_data
        name, version, packages = package_data
        # Execute git tag
        execute_command('git tag -f ' + destination + '/' + version)
        return 0

    def detect_branches(self):
        with inbranch(self.src):
            if self.name is not None:
                return [self.name]
            package_data = get_package_data(self.src)
            if type(package_data) not in [list, tuple]:
                return package_data
            name, version, packages = package_data
            self.packages = packages
            return name if type(name) is list else [name]
