#!/usr/bin/env python

from setuptools import setup

setup(name='bloom',
      version='0.0.17',
      packages=['bloom'],
      package_dir={'': 'src'},
      scripts=['bin/bloom-generate-debian',
               'bin/bloom_util.sh',
               'bin/git-bloom-generate-debian',
               'bin/git-bloom-import-upstream',
               'bin/git-bloom-set-upstream'],
      package_data={'bloom': ['resources/em/*.em', 'util.py', '__init__.py']},
      install_requires=['empy', 'pyyaml', 'argparse',
                        'rosdep', 'rospkg', 'vcstools'],
      author='Tully Foote, William Woodall',
      author_email='tfoote@willowgarage.com, wwoodall@willowgarage.com',
      url='http://www.ros.org/wiki/bloom',
      download_url='http://pr.willowgarage.com/downloads/bloom/',
      keywords=['ROS'],
      classifiers=['Programming Language :: Python',
                   'License :: OSI Approved :: BSD License'],
      description='A tool for facilitating git-buildpackage releases',
      long_description='''\
A package to facilitate releasing into gitbuildpackage repositories.
''',
      license='BSD'
      )
