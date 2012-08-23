from bloom.util import maybe_continue
import sys

if __name__ == '__main__':
    sys.exit(0) if maybe_continue() else sys.exit(1)
