from __future__ import print_function

import os
import sys

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_current_branch

from bloom.logging import ansi
from bloom.logging import error
from bloom.logging import info
from bloom.logging import warning

try:
    from catkin_pkg.packages import find_packages
    from catkin_pkg.packages import verify_equal_package_versions
except ImportError:
    error("catkin_pkg was not detected, please install it.",
          file=sys.stderr)
    sys.exit(1)

has_rospkg = False
try:
    import rospkg
    has_rospkg = True
except ImportError:
    warning("rospkg was not detected, stack.xml discovery is disabled",
            file=sys.stderr)


def get_meta_data(source_branch, name=None, directory=None):
    ## Determine the branching method
    # First check for arguments
    if name is not None:
        info("Using specified name " + ansi('boldon') + name + \
             ansi('reset'))
        return name, None, 'name'
    # Check for package.xml(s)
    repo_dir = directory if directory else os.getcwd()
    packages = find_packages(repo_dir)
    if type(packages) == dict and packages != {}:
        info("Found " + str(len(packages)) + " packages.")
        version = verify_equal_package_versions(packages.values())
        return [p.name for p in packages.values()], version, 'package.xml'
    # Check for stack.xml
    if not has_rospkg:
        error("No package.xml(s) found, and no name specified with "
              "'--package-name', aborting.")
        return 1
    stack_path = os.path.join(repo_dir, 'stack.xml')
    if os.path.exists(stack_path):
        info("Found stack.xml.")
        stack = rospkg.stack.parse_stack_file(stack_path)
        return stack.name, stack.version, 'stack.xml'
    # Otherwise we have a problem
    error("No package.xml(s) or stack.xml found, and not name "
          "specified with '--package-name', aborting.")
    return 1


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
        add('-s', '--source-branch', default=None, dest='src',
            help="git branch to branch from (defaults to 'upstream')")
        add('-n', '--package-name', default=None, dest='name',
            help="name of package being released (use if non catkin project)")
        add('prefix', help="prefix for target branch name(s)")
        BloomGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        # self.interactive = not args.non_interactive
        self.prefix = args.prefix
        self.src = args.src if args.src is not None else get_current_branch()
        self.name = args.name

    def summarize(self):
        info("Looking for packages to release...")
        self.branch_list = self.detect_branches()
        if type(self.branch_list) not in [list, tuple]:
            self.exit(self.branch_list if self.branch_list is not None else -1)
        info(
            "Releasing package" + \
            ('' if len(self.branch_list) == 1 else 's') + ": " + \
            str(self.branch_list)
        )

    def detect_branches(self):
        with inbranch(self.src):
            meta_data = get_meta_data(self.src, self.name)
            if type(meta_data) not in [list, tuple]:
                return meta_data
            name, version, package_type = meta_data
            self.version = version
            self.package_type = package_type
            return name if type(name) is list else list(name)

    def branches(self):
        p, s, n = self.prefix, self.src, self.name
        self.branch_args = [['/'.join([p, b]), s, n] for b in self.branch_list]
        return self.branch_args
