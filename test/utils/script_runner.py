import os
from subprocess import Popen


def popen_bloom_script(cmd, **kwargs):
    this_location = os.path.abspath(os.path.dirname(__file__))
    bin_location = os.path.join(this_location, '..', 'bin')
    cmd = "%s%s%s" % (bin_location, os.path.sep, cmd)
    proc = Popen(cmd, **kwargs)
    return proc
