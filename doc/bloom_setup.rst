Setting up a new bloom repository
=================================

Before you can release anything, you need to setup a bloom release repository.

Start by creating a git repository::

    $ mkdir ~/foo-release

    $ cd ~/foo-release

    $ git init .
    Initialized empty Git repository in /tmp/docs/foo-release/.git/

Now inform bloom of your upstream repository settings and initialize the repository::

    $ git bloom-config https://github.com/bar/foo.git git groovy-devel
    Upstream https://github.com/bar/foo.git type: git
    Freshly initialized git repository detected.
    An initial empty commit is going to be made.
    Continue [Y/n]?

Bloom has noticed that this is an uninitialized git repository, press enter::

    Upstream successively set.

Running the above command took the command line arguments of git-bloom-config and stored them in the bloom branch of this new git repository. The usage of git-bloom-config look like this::

    usage: git-bloom-config [-h] [-d] [--pdb] [-v]
                            upstream_repository upstream_vcs_type
                            [upstream_branch]

The `upstream_repository` is the uri of your upstream source code repository and the `upstream_vcs_type` is the type of your upstream repostiory. Acceptable vcs types are 'git', 'hg', 'svn', and 'bzr'. The optional `upstream_branch` argument specifies the branch on which you normally develop, this might be something like 'groovy-devel', but if left blank it will default to 'master', or 'default', or 'trunk', etc... depending on your vcs type.

You can examine your handy work by running `git-bloom-config` with no arguments::

    $ git-bloom-config
    Current bloom configuration:

    [bloom]
            upstream = https://github.com/bar/foo.git
            upstreamtype = git
            upstreambranch = groovy-devel

    See: 'git-bloom-config -h' on how to change the configs

.. Once you have set the configurations for you particular upstream setup, you are now ready to continue with releasing:

.. - :doc:`catkin_release`
.. - :doc:`non_catkin`


