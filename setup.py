#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='bloom',
    version='0.4.2',
    packages=find_packages(exclude=['test']),
    package_data={
        'bloom.generators.debian': [
            'bloom/generators/debian/templates/*',
            'bloom/generators/debian/templates/source/*'
        ]
    },
    include_package_data=True,
    install_requires=[
        'argparse',
        'catkin-pkg >= 0.1.14',
        'distribute',
        'empy',
        'python-dateutil',
        'PyYAML',
        'rosdep >= 0.10.3',
        'rosdistro >= 0.2.9',
        'vcstools >= 0.1.22',
    ],
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
            'rosdebian = bloom.generators.rosdebian:RosDebianGenerator'
        ],
        'bloom.generate_cmds': [
            'debian = bloom.generators.debian.generate_cmd:description',
            'rosdebian = bloom.generators.rosdebian:description'
        ]
    }
)
