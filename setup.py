#!/usr/bin/env python

from setuptools import setup

setup(name='bloom',
      version='0.0.17',
      packages=['bloom'],
      package_dir = {'': 'src'},
      scripts = ['bin/bloom-generate-debian',
                 'bin/bloom_util.sh',
                 'bin/git-bloom-generate-debian',
                 'bin/git-bloom-import-upstream',
                 'bin/git-bloom-set-upstream'],
      package_data = {'bloom': ['resources/em/*.em']},
      install_requires = ['empy', 'pyyaml', 'argparse', 'rosdep', 'rospkg'],
      author = 'Tully Foote', 
      author_email = 'tfoote@willowgarage.com',
      url = 'http://www.ros.org/wiki/bloom',
      download_url = 'http://pr.willowgarage.com/downloads/bloom/',
      keywords = ['ROS'],
      classifiers = ['Programming Language :: Python',
                     'Programming Language :: Unix Shell',
                     'License :: OSI Approved :: BSD License'],
      description = 'A tool for facilitating gitbuildpackage releases',
      long_description = '''\
A package to facilitate releasing into gitbuildpackage repositories.
''',
      license = 'BSD'
      )
