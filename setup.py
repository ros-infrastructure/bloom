#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='bloom',
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    package_data={'bloom': ['resources/em/*.em']},
    install_requires=['empy', 'pyyaml', 'argparse', 'rosdep', 'rospkg',
                      'vcstools', 'catkin_pkg'],
    author='Tully Foote, William Woodall',
    author_email='tfoote@willowgarage.com, wwoodall@willowgarage.com',
    maintainer='William Woodall',
    maintainer_email='wwoodall@gmail.com',
    url='http://www.ros.org/wiki/bloom',
    download_url='http://pr.willowgarage.com/downloads/bloom/',
    keywords=['ROS'],
    classifiers=['Programming Language :: Python',
                 'License :: OSI Approved :: BSD License'],
    description='A tool for facilitating git-buildpackage releases',
    long_description="A package to facilitate releasing into "
                     "gitbuildpackage repositories.",
    license='BSD',
    test_suite='test'
)
