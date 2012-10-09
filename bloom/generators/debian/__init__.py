from __future__ import print_function

from bloom.generators import BloomGenerator

from bloom.git import get_current_branch

from bloom.logging import info


class DebianGenerator(BloomGenerator):
    title = 'debian'
    description = "Generates debians from the catkin meta data"

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('-i', '--debian-inc', help="debian increment number", default='0')
        add('-s', '--src-branch', default=None,
            help="branch to branch from and create debian")

    def handle_arguments(self, args):
        self.interactive = not args.non_interactive
        self.debian_inc = args.debian_inc
        self.src = args.src if args.src is not None else get_current_branch()

    def summarize(self):
        info("Generating source debs for ")
        info("Debian Incremental Version: " + str(self.debian_inc))
