from __future__ import print_function

from bloom.generators import BloomGenerator


class ReleaseGenerator(BloomGenerator):
    title = 'release'
    description = "Generates a release branch for each of " \
                  "the pacakges found in the repository"

    def prepare_arguments(self, parser):
        # Add command line arguments for this generator
        add = parser.add_argument
        add('--debian-inc', '-i', help="debian increment number", default='0')
