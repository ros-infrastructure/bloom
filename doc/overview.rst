Overview of the bloom release pipeline
--------------------------------------

Context
=======

For this article the diagrams will using shapes with meaning, which is
illustrated with this legend:

.. image:: overview/legend.png

The components of the legend are referring to concepts in the ``git`` scm. 
Each git ``repository`` can have one or more ``branches``, and ``branches`` 
consist of a history of ``commits``. ``commits`` in normal git work flows 
will be related to the previous, or parent, ``commit`` and there fore is just 
an incremental change. However, ``commits`` can also be completely different 
from the parent ``commit`` and are only related by their placement in the ``
branch`` history. Normal ``commits`` are represented in these diagrams as a 
solid line, whereas unrelated ``commits`` are connected by dashed lines. 
Additionally, ``tags`` can be created which simply reference a specific
``commit``. ``tags`` indicate which ``commit`` they are referring to by using 
a connecting solid line with an arrow at the ``commit`` side of the line.

Setup an Upstream Repository
============================

In this overview we will start from the very beginning with a brand new ROS 
package. Initially we create a git ``repository`` called ``foo`` with:

    $ cd ~
    $ mkdir bloom_overview
    $ cd bloom_overview
    $ mkdir foo
    $ cd foo
    $ git init .
    $ touch README.rst
    $ git commit -a -m "Initial commit."

.. image:: overview/foo1.png

The result is an empty ``repository`` called foo, which has one ``branch`` 
'master'. This repository will be refered to as the ``upstream repository``
because changes to the foo package will originate in this repository, 'flow' 
down to the ``release repository`` and finally end up in the distributed 
source and binary packages. Following the branching guidelines we should make 
a 'groovy-devel' branch and not use master for development:

    $ git branch groovy-devel
    $ git checkout groovy-devel
    $ git branch -d master

.. image:: overview/foo2.png

Now our ``repository`` foo has one branch called 'groovy-devel'. To make 
foo a proper ROS package it needs a package.xml file. A simple 
example might be:

    <package>
      <name>foo</name>
      <version abi="0.1.0">0.1.0</version>
      <description brief="Provides an interface to foo.">
        Foo ROS pacakge which provides an interface to foo.
      </description>
      <maintainer email="someone@example.com">Someone</maintainer>

      <url type="website">http://wiki.ros.org/foo</url>
      <url type="bugtracker">http://www.github.com/foo_owner/foo/issues</url>

      <author email="jane.doe@example.com">Jane Doe</author>
      <license>BSD</license>
      <copyright>Foo Owner</copyright>

      <depends scope="build">catkin</depends>
      <depends scope="build;run">libboost-thread-dev</depends>
      <depends scope="build;run">libboost-date-time-dev</depends>

    </package>

It should be noted a valid version is specified (required) along with an abi 
(optional) and that there is a maintainer (required). The items listed in the 
<depends> tags are used later in the bloom release pipeline to define 
dependencies for the target platform using rosdep.

Once you have put your package.xml in the foo directory add it to your git 
repository and commit the change:

    $ git add package.xml
    $ git commit -m "Release 0.1.0"

.. image:: overview/foo3.png

Now we are ready to tag our first release from 'groovy-devel':

    $ git tag 0.1.0 -m "0.1.0: First release"

This completes the setup of your ``upstream repository`` and now we are 
ready to create the initial ``release repository`` and make a release 
using bloom.

Setup a Release Repository
==========================

First we need to create a new git repository for the ``release repository``:

    $ cd ~/bloom_overview
    $ mkdir foo-release
    $ cd foo-release
    $ git init .

A this point we will start to use the bloom tools to help facilitate the 
release pipeline process, therefore you need to ensure that bloom is installed.
You can test to see if bloom exists by ensuring ``git bloom-set-upstream`` is 
a command.

  Note: Sometimes the term ``bloom repository`` will be used interchangeably 
  with ``release repository``.

Now we are going to use the ``git bloom-set-upstream`` command to configure 
our ``release repository``. The ``git bloom-set-upstream`` command has two 
required arguments and one optional one. The first argument is a URL to the ``
upstream repository``, in this case we are using a file:// type URL because 
the ``upstream repository`` is on the local disk, but this could be a ssh:// 
or https:// URL pointing to a remotely hosted ``upstream repository``. The 
second argument is one of git, svn, hg, or bzr. This tells bloom what kind of 
repository the ``upstream repository`` is, in this case we are using git. The 
third, optional, argument is a ``branch`` or ``tag`` to use when fetching code 
from the ``upstream repository``. If not specified the default ``branch`` is 
used, but in our case we will specify the 'groovy-devel' ``branch``. You 
should always specify the third argument if you can. We will execute our 
command as follows:

    $ git bloom-set-upstream file://$HOME/bloom_overview/foo git groovy-devel

The command will detect that you have made no commits yet and offer to 
initialize the ``repository`` for you, accept by typing 'y' and pressing enter.

.. image:: overview/foo-release1.png

The above figure now shows what your ``release repository`` looks like.

.. image:: overview/git-bloom-set-upstream.png

The ``git bloom-set-upstream`` command has created a 'bloom' ``branch`` and 
stored the configurations you gave it in a file called 'bloom.conf'. Bloom 
stores all its configurations and state in the 'bloom' ``branch`` and will 
sometimes switch to this ``branch`` and modify files, but will always return 
you to the branch you started in, i.e. it won't move you from 'master' to 
'bloom'. You should only need to run ``git bloom-set-upstream`` command again 
when you change the upstream URL, type, or branch.

Your ``release repository`` is now setup and ready for releasing.

Releasing Your Package
======================

There are a few instances when you want to push a release down the pipeline, 
but the most common scenario is that that is a new upstream version, which 
hasn't previously been released, ready for release. When setting up our ``
upstream repository`` we set the <version> tag in the package.xml to '0.1.0' 
as well as the abi attribute, and created a ``tag`` called '0.1.0'. This is 
all that is needed to prepare an ``upstream repository`` for release. Now we 
need to pull in the newly released version 0.1.0 of the upstream into our ``
release repository``. This is done using the ``git bloom-import-upstream`` 
command:

    $ git bloom-import-upstream

.. image:: overview/git-bloom-import-upstream1.png

The ``git bloom-import-upstream`` command first clones at your ``upstream 
repository`` and switches to the upstream ``branch`` if one was specified. In 
that ``branch`` it expects to find a package.xml file which it parses for 
information like the version and package name. Using the version string found 
in the package.xml file it "exports" a snapshot of the ``upstream repository`` 
at the ``tag`` with the same name as the version string. This snapshot of the 
``upstream repository`` is stripped of any previous vcs content and put into a 
tar.gz archive.

  Note: Even if an upstream ``branch`` has been specified in 'bloom.conf', you 
  can override that configuration when running the 
  ``git bloom-import-upstream`` command using the '--upstream-branch BRANCH' 
  command line option.

.. image:: overview/git-bloom-import-upstream2.png

This archive is then passed to the ``gbp-import-orig`` command, which takes 
the tar.gz archive and puts it at the head of the 'upstream' ``branch``. 
Additionally, ``git bloom-import-upstream`` creates a ``tag`` that points to 
this newly imported snapshot of the upstream. The ``tag`` name is 
'release/<prefix><package.xml:name>_<package.xml:version><postfix>', where 
prefix and postfix are strings which are set using the ``git bloom-set-prefix``
and ``git bloom-set-postfix`` commands and the 'package.xml:*' elements are 
strings from tags in the 'package.xml' file.

  Note: The ``commits`` in the 'upstream' ``branch`` are a series of 
  snapshots, not the incremental changes which are common in the normal git 
  work flow. For this reason they connected by dotted lines in the diagrams.

.. image:: overview/foo-release2.png

Your ``release repository`` now has a new ``branch`` called 'upstream' with 
one ``commit`` under it which is the imported snapshot of your ``upstream 
branch`` at tag '0.1.0'.
