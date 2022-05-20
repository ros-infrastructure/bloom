Bloom
=====

.. Links

.. _catkin: https://github.com/ros/catkin
.. _bloom: http://ros.org/wiki/bloom

What is bloom?
--------------

Bloom is a release automation tool, designed to make generating platform specific release artifacts from source projects easier. Bloom is designed to work best with catkin_ projects, but can also accommodate other types of projects.

How does it work?
-----------------

Bloom works by importing your upstream source tree into a git repository, where it is manipulated and used to generate build artifacts for different platforms like Debian or Fedora.

First bloom gathers information about your source repository and creates an archive for the version you want to release. Then the archive is imported into the release repository, and the source tree is run through a release track where it is tagged, can be patched, and has platform specific artifacts generated for it.

The individual stages of these release tracks are tagged with git and those tags are used by build infrastructure and deployment systems.

What can I release with bloom?
------------------------------

Bloom supports releasing arbitrary software packages, but is optimized for use with catkin_ projects.

.. note:: For :term:`dry` ROS stacks, you should use the legacy `ros-release <http://www.ros.org/wiki/release>`_ system.

How do I install bloom?
-----------------------

On Ubuntu the recommended method is to use apt::

    $ sudo apt-get install python3-bloom

On other systems you can install bloom via pypi::

    $ sudo pip install -U bloom

Note: pip will not notify you of updates, but bloom will notify you when you are using a version of bloom that is not the latest released.

Develop and build from source::

    $ python setup.py build
    $ sudo python setup.py develop

How do I release something with bloom?
---------------------------------------

Please refer to the documentation and tutorials on the bloom_ ROS wiki page.
