#!/usr/bin/env python

import sys
from setuptools import find_packages, setup

install_requires = [
    'catkin-pkg >= 0.4.3',
    'setuptools',
    'empy',
    'python-dateutil',
    'PyYAML',
    'rosdep >= 0.10.25',
    'rosdistro >= 0.4.0',
    'vcstools >= 0.1.22',
]

# argparse got moved into the stdlib in py2.7, so we only
# need to install the pypi version if we're on an older
# python.
if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
    install_requires.append('argparse')

setup(
    name='bloom',
    version='0.6.7',
    packages=find_packages(exclude=['test', 'test.*']),
    package_data={
        'bloom.generators.debian': [
            'bloom/generators/debian/templates/*',
            'bloom/generators/debian/templates/source/*'
        ],
        'bloom.generators.rpm': [
            'bloom/generators/rpm/templates/*'
        ]
    },
    include_package_data=True,
    install_requires=install_requires,
    author='Tully Foote, William Woodall',
    author_email='tfoote@willowgarage.com, william@osrfoundation.org',
    maintainer='William Woodall',
    maintainer_email='william@osrfoundation.org',
    url='http://www.ros.org/wiki/bloom',
    download_url='http://pr.willowgarage.com/downloads/bloom/',
    keywords=['ROS'],
    classifiers=['Programming Language :: Python',
                 'License :: OSI Approved :: BSD License'],
    description="Bloom is a release automation tool.",
    long_description="""\
Bloom provides tools for releasing software on top of a git repository \
and leverages tools and patterns from git-buildpackage. Additionally, \
bloom leverages meta and build information from catkin \
(https://github.com/ros/catkin) to automate release branching and the \
generation of platform specific source packages, like debian's src-debs.""",
    license='BSD',
    test_suite='test',
    entry_points={
        'console_scripts': [
            'git-bloom-config = bloom.commands.git.config:main',
            'git-bloom-import-upstream = bloom.commands.git.import_upstream:main',
            'git-bloom-branch = bloom.commands.git.branch:main',
            'git-bloom-patch = bloom.commands.git.patch.patch_main:main',
            'git-bloom-generate = bloom.commands.git.generate:main',
            'git-bloom-release = bloom.commands.git.release:main',
            'bloom-export-upstream = bloom.commands.export_upstream:main',
            'bloom-update = bloom.commands.update:main',
            'bloom-release = bloom.commands.release:main',
            'bloom-generate = bloom.commands.generate:main'
        ],
        'bloom.generators': [
            'release = bloom.generators.release:ReleaseGenerator',
            'rosrelease = bloom.generators.rosrelease:RosReleaseGenerator',
            'debian = bloom.generators.debian:DebianGenerator',
            'rosdebian = bloom.generators.rosdebian:RosDebianGenerator',
            'rpm = bloom.generators.rpm:RpmGenerator',
            'rosrpm = bloom.generators.rosrpm:RosRpmGenerator'
        ],
        'bloom.generate_cmds': [
            'debian = bloom.generators.debian.generate_cmd:description',
            'rosdebian = bloom.generators.rosdebian:description',
            'rpm = bloom.generators.rpm.generate_cmd:description',
            'rosrpm = bloom.generators.rosrpm:description'
        ]
    }
)
