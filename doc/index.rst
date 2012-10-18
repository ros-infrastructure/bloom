Bloom v0.1.x
============

Better documentation is in progress, for now there is Installation and Quickstarts.

Installing
----------

On ubuntu the recommend method is to use apt::

    sudo apt-get install python-bloom

On other systems you can install bloom via pypi::

    sudo pip install -U bloom


Quickstarts
-----------

Setup a new bloom repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See: :doc:`bloom_setup`


Releasing for Groovy
^^^^^^^^^^^^^^^^^^^^

Import upstream::

    $ git bloom-import-upstream

Note: see `git bloom-import-upstream -h` for more import options.

Release::

    $ git bloom-release groovy

Two steps happen here, branching (this is when individual packages get split up) and debian generation. This command will likely have different arguments in the future (when there is more than just debian).

That's it, unless there was an error.

Things to check:

- Is there a release/<package>/<version> tag
- Did your generate-debian step produce tags for your new version

When you are done, follow the instructions at the end of the command::

    $ git push --all && git push --tags

Releasing for Fuerte
^^^^^^^^^^^^^^^^^^^^

The only difference from groovy is that you probably need to import from upstream differently. If you have a separate fuerte development branch, like 'fuerte-devel', then you can use::

    $ git bloom-import-upstream --upstream-devel fuerte-devel

If you don't have a branch, but you have a specific tag in mind::

    $ git bloom-import-upstream --upstream-tag fuerte-foo-1.1.1

Once you have imported from upstream, just run the release script like normal::

    $ git bloom-release fuerte

Check everything out and push::

    $ git push --all && git push --tags

Releasing non Catkin Projects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When import a non catkin project from upstream, you must specify the upstream version manually using the '--upstream-version' argument and the upstream tag to export from using the '--upstream-tag' argument. For example::

    $ git bloom-import-upstream --upstream-version 1.1.1 --upstream-tag foo-1.1.1

If you are using svn in a non standard layout, you can specify the exact url to use like this:

    $ git bloom-import-upstream --upstream-version 1.1.1 --explicit-svn-url https://svn.foo.com/svn/foo/some/weird/path/foo-1.1.1

Once you have imported the upstream, you will need to manually branch to the release stage::

    $ git bloom-branch --src upstream --package-name foo release

Note: this workflow will probably change in the next version of bloom to make it more streamlined and compatable with catkin projects.

The above command created a new branch called 'release/foo'. You should change to the branch::

    $ git checkout release/foo

And add a minimal catkin package.xml file. The generate debian phase requires a catkin package.xml file or legacy stack.xml file to produce debians. There is a convenience command::

    $ git bloom-packageme foo 1.1.1

Which will create a template package.xml in the current directory for a package foo at version 1.1.1. Once you have completed your package.xml file, commit it to this branch::

    $ git add package.xml
    $ git commit -m "Added a package.xml file"

Now you need to 'export' this patch so that it will persist through new upstream versions (though you likely have to edit it for each version)::

    $ git bloom-patch export

You should run that command any time you make a commit on one of the patch branches (release/foo is a patch branch).

Next, you need to tag this release for the build farm (this is automatic when you have an upstream catkin project)::

    $ git tag release/foo/1.1.1

Now you are ready to generate the debians::

    $ git bloom-generate-debian-all groovy release

If this is successful you won't get a nice little message like git bloom-release gives you, but as long as the return code was 0 you can push just like you would with catkin branches::

    $ git push --all && git push --tags

Notifying the buildfarm
-----------------------

Test first by checking out to a tag and then running this command::

    $ git checkout debian/groovy/ros-groovy-<package>_<version>-<debinc>_<distro>
    $ git-buildpackage -uc -us --git-ignore-branch

Once you have pushed your changes to the release repository, you still need to update the file that the build farm uses to generate jobs which is currently located at https://github.com/ros/rosdistro/blob/master/releases/groovy.yaml


.. Introducing Bloom v0.1.9
.. ========================

.. What is bloom?
.. --------------

..   Bloom is a release automation tool, designed to make generating platform specific release artifacts from source projects easier.

.. How does it work?
.. -----------------

..   Bloom works by importing your upstream source code repository into a git repository, where it gives opporitunity for you to patch the upstream for specific platforms, and finally produces platform specific release tags using generators.

.. What can I release with bloom?
.. ------------------------------

.. .. _catkin: https://github.com/ros/catkin

..   Bloom supports releasing arbitrary software packages, but is optimized for use with catkin_ projects.

.. How do I install bloom?
.. -----------------------

.. On ubuntu the recommend method is to use apt::

..     sudo apt-get install python-bloom

.. On other systems you can install bloom via pypi::

..     sudo pip install -U bloom

.. Note: pip will not notify you of updates, so check often if you use pip

.. How do I release something with bloom?
.. ---------------------------------------

.. It depends on your usecase:

.. #. :doc:`bloom_setup`
.. #. :doc:`catkin_release`
.. #. :doc:`catkin_backport`
.. #. :doc:`non_catkin`
