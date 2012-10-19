Bloom -- 0.2.0
==============

.. Links

.. _catkin: https://github.com/ros/catkin

What is bloom?
--------------

Bloom is a release automation tool, designed to make generating platform specific release artifacts from source projects easier. Bloom is designed to work best with catkin_ projects, but can also accommodate other types of projects.

How does it work?
-----------------

Bloom works by importing your upstream source tree into a git repository, where it is manipulated and used to generate build artifacts for different platforms like Debian and Fedora.

After importing your upstream source tree, the source tree is run through a release pipeline of git branches, each of which gives you the opportunity to patch the upstream source tree for specific platforms, and finally produces platform specific release tags using platform specific generators.

What can I release with bloom?
------------------------------

Bloom supports releasing arbitrary software packages, but is optimized for use with catkin_ projects.

.. note:: For :term:`dry` ROS stacks, you should use the legacy `ros-release <http://www.ros.org/wiki/release>`_ system.

How do I install bloom?
-----------------------

On Ubuntu the recommend method is to use apt::

    $ sudo apt-get install python-bloom

On other systems you can install bloom via pypi::

    $ sudo pip install -U bloom

Note: pip will not notify you of updates, so check often if you use pip

How do I release something with bloom?
---------------------------------------

It depends on your use case:

.. toctree::
    :maxdepth: 1

    tutorials/bloom_setup
    tutorials/catkin_release
    tutorials/non_catkin
    tutorials/notify_build_farm

.. toctree::
    :hidden:

    glossary
