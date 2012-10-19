Releasing a catkin project
==========================

Assuming you have either setup a new bloom release repository (:doc:`bloom_setup`) or you have cloned an existing release repository, you are now ready to begin releasing your catkin project.

Once in your release repository, ensure that you are on the 'master' branch::

    $ git checkout master

It is always best to run from the master branch when possible.

Preparing your upstream repository
----------------------------------

Before importing your upstream repository into the release repository using 
bloom, the upstream repository needs to be prepared. For catkin projects, this 
means updating the version number in the ``package.xml``\ (s) of your project. 
Additionally, there needs to be a tag matching the version number exactly. For 
example, if you just released version 1.1.1 from 1.1.0 and you use a git 
repository as your upstream vcs type, then you would need to run::

    $ git tag 1.1.1 -m "Releasing version 1.1.1 of foo"

If you use a different tagging scheme, git bloom-import-upstream can handle that, see `git bloom-import-upstream -h`.

Running git bloom-release
-------------------------

Now that you have either setup a new release repository, or cloned an existing one, and prepared your upstream repository for release, it is time to run the bloom release command::

    $ git bloom-release rosdebian groovy

In this example rosdebian will create ROS tailored debians for the groovy release of ROS.

That's it, if successful you should receive a message something like::

    .
    .
    .
    ### Running 'git bloom-generate -y release --src upstream'... returned (0)


    Tip: Check to ensure that the debian tags created have the same version as the upstream version you are releasing.
    Everything went as expected, you should check that the new tags match your expectations, and then push to the release repo with:
      git push --all && git push --tags

You can follow the message's advice::

    $ git push --all && git push --tags

Now, if you want your packages built and released by the build farm see: :doc:`notify_build_farm`

What is git bloom-release doing?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The bloom release command is a convenience command which combines three bloom commands into one.

The normal work-flow for releasing a project with bloom is:

#. Import the latest version from upstream
#. Run the release generator
#. Run the platform specific generator off the release stage

The release generator creates a new stage in the release pipeline for each package present in the upstream source tree.  For example, if you have an upstream repository with catkin packages 'foo' in the '<git root>/foo' directory and 'bar' in the '<git root>/bar' directory, then the release generator will create the branches 'release/foo' and 'release/bar'. The release branches will not contain the entire upstream source tree, but just the source tree for each package.

The platform specific generator, like 'rosdebian' or 'debian', will produce additional release pipeline stages for each 'release/' prefixed branch and each distribution of the generator's platform. For example, the 'release/foo' branch would result in the 'debian/groovy/oneiric/foo', 'debian/groovy/precise/foo', and 'debian/groovy/quantal/foo' branches. On each of these branches the necessary debian files are generated from the contents of the catkin 'package.xml' file and when complete the branch is tagged for a specific source debian, like ``debian/ros-groovy-foo_1.1.1-0_quantal``.

For more information about ``git bloom-release`` and how it can be used see::

    $ git bloom-release -h
