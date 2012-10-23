#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='bloom',
    version='0.2.2',
    packages=find_packages(exclude=['test']),
    package_data={
        'bloom.generators.debian':
            ['bloom/generators/debian/templates/*.em']
    },
    include_package_data = True,
    install_requires=[
        'empy >= 3.1',
        'PyYAML >= 3.10',
        'argparse >= 1.2.1',
        'rosdep >= 0.10.3',
        'rospkg >= 1.0.6',
        'vcstools >= 0.1.22',
        'catkin-pkg >= 0.1.2',
        'distribute >= 0.6.24'
    ],
    author='Tully Foote, William Woodall',
    author_email='tfoote@willowgarage.com, wwoodall@willowgarage.com',
    maintainer='William Woodall',
    maintainer_email='wwoodall@willowgarage.com',
    url='http://www.ros.org/wiki/bloom',
    download_url='http://pr.willowgarage.com/downloads/bloom/',
    keywords=['ROS'],
    classifiers=['Programming Language :: Python',
                 'License :: OSI Approved :: BSD License'],
    description="A tool for facilitating git-buildpackage based releases",
    long_description="""\
Bloom provides tools for releasing software on top of a git repository \
and leverages tools and patterns from git-buildpackage.  Additionally, \
bloom leverages meta and build information from catkin \
(https://github.com/ros/catkin) to automate release branching and the \
generation of platform specific source packages, like debian's src-debs.""",
    license='BSD',
    test_suite='test',
    entry_points={
        'console_scripts': [
            'git-bloom-config = bloom.commands.config:main',
            'git-bloom-import-upstream = bloom.commands.import_upstream:main',
            'git-bloom-branch = bloom.commands.branch:main',
            'git-bloom-patch = bloom.commands.patch.patch_main:main',
            'git-bloom-generate = bloom.commands.generate:main',
            'git-bloom-release = bloom.commands.release:main'
        ]
    }
)
