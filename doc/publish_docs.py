#!/usr/bin/env python

import os
import re
import shutil
import sys

this_dir = os.path.dirname(os.path.abspath(__file__))
setup_py = os.path.join(this_dir, '..', 'setup.py')
cmd = setup_py + ' build'
print("### Running '" + cmd + "'")
os.system(cmd)

sys.path.append(os.path.abspath(os.path.join(this_dir, '..')))

from bloom import __version__ as ver

from bloom.logging import warning

from bloom.git import GitClone
from bloom.git import inbranch
from bloom.git import has_changes

from bloom.util import execute_command
from bloom.util import maybe_continue

print("Generating github pages documentation for version '{}'...".format(ver))

execute_command('make clean', cwd='doc')
execute_command('python setup.py build_sphinx')
execute_command('sphinxtogithub doc/build/html --verbose')
orig_cwd = os.getcwd()

clone = GitClone()
with clone as clone_dir:
    execute_command('git clean -fdx')
    with inbranch('gh-pages'):
        doc_dir = os.path.join('doc', ver)
        if os.path.exists(doc_dir):
            warning("Documentation for version '" + ver + "' already exists.")
            if not maybe_continue('y'):
                sys.exit(-1)
            execute_command('git rm -rf ' + doc_dir)
        shutil.copytree(os.path.join(orig_cwd, 'doc', 'build', 'html'),
                        doc_dir)
        p = re.compile('\d[.]\d[.]\d')
        with open('doc/index.html', 'r') as f:
            redirect = f.read()
        redirect = p.sub(ver, redirect)
        with open('doc/index.html', 'w+') as f:
            f.write(redirect)
        execute_command('git add ' + os.path.join('doc', ver))
        execute_command('git add doc/index.html')
        if has_changes():
            execute_command('git commit -m "Uploading documentation for '
                            'version {0}"'.format(ver))
clone.commit()
clone.clean_up()
