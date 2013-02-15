from __future__ import print_function

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_current_branch

from bloom.logging import info
from bloom.logging import warning

from bloom.util import execute_command
from bloom.util import get_package_data

from bloom.commands.git.patch.trim_cmd import trim


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
        add('--release-increment', '-i', default=0,
            help="release increment number")
        return BloomGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.interactive = args.interactive
        self.prefix = args.prefix
        self.src = args.src if args.src is not None else get_current_branch()
        self.name = args.name
        self.release_inc = args.release_increment

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

    def pre_rebase(self, destination, msg=None):
        name = destination.split('/')[-1]
        msg = msg if msg is not None else (
            "Releasing package '" + name + "' to: '" + destination + "'"
        )
        info(msg)
        ret = trim(undo=True)
        return 0 if ret < 0 else ret  # Ret < 0 indicates nothing was done

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
            return
        return trim(trim_d)

    def post_patch(self, destination):
        # Figure out the version of the given package
        if self.name is not None:
            warning("""\
Cannot automatically tag the release because this is not a catkin project."""
            )
            warning("""\
Please checkout the release branch and then create a tag manually with:"""
            )
            warning("  git checkout release/" + str(self.name))
            warning("  git tag -f release/" + str(self.name) + "/<version>")
            return
        with inbranch(destination):
            name, version, packages = get_package_data(destination)
        # Execute git tag
        execute_command('git tag -f ' + destination + '/' + version +
            '-' + self.release_inc)

    def detect_branches(self):
        self.packages = None
        with inbranch(self.src):
            if self.name is not None:
                self.packages = [self.name]
                return [self.name]
            name, version, packages = get_package_data(self.src)
            self.packages = packages
            return name if type(name) is list else [name]
