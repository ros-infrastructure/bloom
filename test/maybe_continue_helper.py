import os
from export_bloom_from_src import get_path_and_pythonpath
# Setup environment for running commands
path, ppath = get_path_and_pythonpath()
os.putenv('PATH', path)
os.putenv('PYTHONPATH', ppath)

from bloom.util import maybe_continue
import sys

if __name__ == '__main__':
    sys.exit(0) if maybe_continue() else sys.exit(1)
