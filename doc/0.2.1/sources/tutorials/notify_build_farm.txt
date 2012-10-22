Notifying the buildfarm
=======================

Test first by checking out to a tag and then running this command::

    $ git checkout debian/groovy/ros-groovy-<package>_<version>-<debinc>_<distro>
    $ git-buildpackage -uc -us --git-ignore-branch

Once you have pushed your changes to the release repository, you still need to update the file that the build farm uses to generate jobs which is currently located at `https://github.com/ros/rosdistro/blob/master/releases/groovy.yaml <https://github.com/ros/rosdistro/blob/master/releases/groovy.yaml>`_

