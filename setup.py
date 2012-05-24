#!/usr/bin/env python

from distutils.core import setup
#from setuptools import setup


setup(name='bloom',
      version='0.0.1',
      packages=['bloom'],
      package_dir = {'bloom':'src'},
      scripts = ['bin/git-bloom-generate-debian', 'bin/bloom-generate-debian',
                 'bin/git-bloom-import-upstream', 'bin/git-bloom-set-upstream', 
                 'bin/bloom_util.sh'],
      #include_package_data = True,
      package_data = {'bloom': ['bin/em/*']},
      install_requires = ['empy', 'pyyaml', 'argparse'],
      author = "Tully Foote", 
      author_email = "tfoote@willowgarage.com",
      url = "http://www.ros.org/wiki/bloom",
      download_url = "http://pr.willowgarage.com/downloads/bloom/", 
      keywords = ["ROS"],
      classifiers = [
        "Programming Language :: Python", 
        "Programming Language :: Bash", 
        "License :: OSI Approved :: BSD License" ],
      description = "A tool for facilitating gitbuildpackage releases", 
      long_description = """\
A package to facilitate releasing into gitbuildpackage repositories.  
""",
      license = "BSD"
      )
