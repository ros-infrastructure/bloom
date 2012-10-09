from __future__ import print_function

from bloom.generators import BloomGenerator

from bloom.git import inbranch
from bloom.git import get_current_branch

from bloom.logging import info


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
        add('-s', '--src-branch', default=None,
            help="git branch to branch from (defaults to 'upstream')")
        add('prefix', help="prefix for target branch name(s)")
        BloomGenerator.prepare_arguments(self, parser)

    def handle_arguments(self, args):
        self.interactive = not args.non_interactive
        self.src = args.src if args.src is not None else get_current_branch()

    def summarize(self):
        info("Generating release branches")
        info("")

    def detect_branches(self):
        with inbranch(self.src):
            pass

    def branches(self):
        self.branches = self.detect_branches()
