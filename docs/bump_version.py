#!/usr/bin/env python

import argparse
import re
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Bumps the version of a given setup.py file"
    )
    parser.add_argument('file', help="setup.py file to be bumped")
    parser.add_argument('--version_only', default=False, action='store_true')
    args = parser.parse_args()
    with open(args.file, 'r') as f:
        lines = f.read()
    version_line_regex = re.compile(r".*version='\d*[.]\d*[.]\d*'.*")
    version_line = version_line_regex.findall(lines)
    version_line = version_line[0]
    version_regex = re.compile(r'\d*[.]\d*[.]\d*')
    version_str = version_regex.findall(version_line)[0]
    version_str = version_str.split('.')
    version_str[-1] = str(int(version_str[-1]) + 1)
    version_str = '.'.join(version_str)
    if args.version_only:
        print(version_str)
        sys.exit(0)
    new_version_line = version_regex.sub(version_str, version_line)
    for line in lines.splitlines():
        if line.count("version='") > 0:
            print(new_version_line)
        else:
            print(line)
