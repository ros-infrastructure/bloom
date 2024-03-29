0.12.0 (2024-03-29 17:20:00 -0500)
----------------------------------
- Fix regression in RHEL 8 / Python3.6 support. `#700 <https://github.com/ros-infrastructure/bloom/issues/700>`_
- Drop support for Python <2.7, simplify setup.py. `#733 <https://github.com/ros-infrastructure/bloom/issues/733>`_
- Add dh_shlibdeps entry for libraries installed by ament_vendor `#732 <https://github.com/ros-infrastructure/bloom/issues/732>`_
- Fix template file inclusion in Python package. `#731 <https://github.com/ros-infrastructure/bloom/issues/731>`_
- Use raw strings for regular expressions. `#730 <https://github.com/ros-infrastructure/bloom/issues/730>`_
- Update deb platforms and drop python2 packaging. `#724 <https://github.com/ros-infrastructure/bloom/issues/724>`_
- Switch from SafeConfigParser to ConfigParser. `#728 <https://github.com/ros-infrastructure/bloom/issues/728>`_
- Restore weekly CI job. `#729 <https://github.com/ros-infrastructure/bloom/issues/729>`_
- Create a fake rosdistro index for better test isolation. `#727 <https://github.com/ros-infrastructure/bloom/issues/727>`_
- Switch to unified ros-infrastructure CI. `#726 <https://github.com/ros-infrastructure/bloom/issues/726>`_
- Pin to empy < 4. `#726 <https://github.com/ros-infrastructure/bloom/issues/726>`_
- Use extras_require.test and pytest for test dependencies. `#726 <https://github.com/ros-infrastructure/bloom/issues/726>`_
- Add weekly scheduled run to make sure that CI stays green. `#695 <https://github.com/ros-infrastructure/bloom/issues/695>`_
- Add debian package dependency for new packaging dependency. `#698 <https://github.com/ros-infrastructure/bloom/issues/698>`_
- Replace pkg_resources.parse_version with packaging.version.parse. `#693 <https://github.com/ros-infrastructure/bloom/issues/693>`_
- Fix typo 'tempate' -> 'template'. `#694 <https://github.com/ros-infrastructure/bloom/issues/694>`_
- Dry-run with specific remote target, in case remote repo isn't initialized yet. `#684 <https://github.com/ros-infrastructure/bloom/pull/684>`_
- Add Defaults for src/doc information. `#686 <https://github.com/ros-infrastructure/bloom/issues/686>`_
- Ensure subparser is required. `#683 <https://github.com/ros-infrastructure/bloom/issues/683>`_

0.11.2 (2022-07-18 14:18:10 -0700)
----------------------------------
- Use inspect.getfullargspec where available. `#682 <https://github.com/ros-infrastructure/bloom/issues/682>`_
- Update index.rst to reflect python3 on Ubuntu. `#673 <https://github.com/ros-infrastructure/bloom/issues/673>`_
- Get non eol distros from rosdistro index. `#670 <https://github.com/ros-infrastructure/bloom/issues/670>`_

0.11.1 (2022-04-21 12:20:00 -0700)
----------------------------------
- Update release suites. `#672 <https://github.com/ros-infrastructure/bloom/issues/672>`_

0.11.0 (2022-04-19 14:30:00 -0700)
----------------------------------
- Exit early on patch failure if bloom is being run non-interactively. `#668 <https://github.com/ros-infrastructure/bloom/issues/668>`_
- Add build dependency dh-python for --with-python3. `#661 <https://github.com/ros-infrastructure/bloom/issues/661>`_
- Refactor CI platforms. `#659 <https://github.com/ros-infrastructure/bloom/issues/659>`_
- Un-normalize catkin_pkg dependency name. `#656 <https://github.com/ros-infrastructure/bloom/issues/656>`_
- Remove references to Travis CI. `#655 <https://github.com/ros-infrastructure/bloom/issues/655>`_
- Conditionally exclude tests and dependencies. `#649 <https://github.com/ros-infrastructure/bloom/issues/649>`_
- Begin build directories with '.'. `#647 <https://github.com/ros-infrastructure/bloom/issues/647>`_
- Drop support for EOL Ubuntu distros. `#653 <https://github.com/ros-infrastructure/bloom/issues/653>`_
- Include more license information in RPM spec files. `#650 <https://github.com/ros-infrastructure/bloom/issues/650>`_
- Generate machine-readable debian/copyright file. `#651 <https://github.com/ros-infrastructure/bloom/issues/651>`_
- Fall back to 3-way merge when applying patches. `#634 <https://github.com/ros-infrastructure/bloom/issues/634>`_
- Update documentation link in README. `#644 <https://github.com/ros-infrastructure/bloom/issues/644>`_

0.10.7 (2021-04-16 11:30:00 -0700)
----------------------------------
- Fix basic authentication issue affecting new GitHub tokens. `#633 <https://github.com/ros-infrastructure/bloom/issues/633>`_

0.10.6 (2021-04-07 11:30:00 -0700)
---------------------------------
- Fix a packaging bug affecting only Debian packages.

0.10.5 (2021-04-07 10:30:00 -0700)
---------------------------------
- Fix a packaging bug affecting only Debian packages.

0.10.4 (2021-04-07 10:00:00 -0700)
----------------------------------
- Use basic authentication with the new personal access tokens. `#627 <https://github.com/ros-infrastructure/bloom/issues/627>`_
- Add a fast check for the likely fork name. `#629 <https://github.com/ros-infrastructure/bloom/issues/629>`_
- Specify patch level in RPM templates. `#626 <https://github.com/ros-infrastructure/bloom/issues/626>`_
- Collect manually created token rather than attempting to create one. `#628 <https://github.com/ros-infrastructure/bloom/issues/628>`_

0.10.3 (2021-03-25 11:08:00 -0700)
----------------------------------
- Rewire the typesupport dependencies for post-Foxy. `#625 <https://github.com/ros-infrastructure/bloom/issues/625>`_

0.10.2 (2021-03-11 17:05:00 -0800)
----------------------------------
- Drop Connext from typesupport dependencies for RPMs `#623 <https://github.com/ros-infrastructure/bloom/issues/623>`_
- Enable output from CTest failures in RPMs `#620 <https://github.com/ros-infrastructure/bloom/issues/620>`_
- Only suggest resetting action list if it's old `#622 <https://github.com/ros-infrastructure/bloom/issues/622>`_

0.10.1 (2021-02-04 15:00:00 -0800)
----------------------------------
- Do not verify package version on ignored packages `#610 <https://github.com/ros-infrastructure/bloom/pull/610>`_
- Update email addresses and remove 404 download url `#607 <https://github.com/ros-infrastructure/bloom/pull/607>`_
- Align CMake args in RPMs with debs `#617 <https://github.com/ros-infrastructure/bloom/pull/617>`_
- Add a template substitution for the ROS distro `#612 <https://github.com/ros-infrastructure/bloom/pull/612>`_
- Create and use a 'fake' rosdep cache for tests `#614 <https://github.com/ros-infrastructure/bloom/pull/614>`_
- Add --debian-inc option to bloom-generate `#428 <https://github.com/ros-infrastructure/bloom/pull/428>`_
- Solve shlibdeps errors in REP136 packages that use GNUInstallDirs. `#600 <https://github.com/ros-infrastructure/bloom/pull/600>`_
- Don't prompt if --override-release-repository-url `#594 <https://github.com/ros-infrastructure/bloom/pull/594>`_

0.10.0 (2020-09-28 16:30:00 -0700)
----------------------------------
- Add CMAKE_PREFIX_PATH to ament_cmake and cmake templates `#606 <https://github.com/ros-infrastructure/bloom/pull/606>`_
- Add RHEL to the default action list `#604 <https://github.com/ros-infrastructure/bloom/pull/604>`_
- Handle skipping keys multiple times `#603 <https://github.com/ros-infrastructure/bloom/pull/603>`_

0.9.8 (2020-08-21 15:36:00 -0700)
---------------------------------
- Run tests in RPM builds for ament and cmake packages. `#585 <https://github.com/ros-infrastructure/bloom/pull/585>`_
- Add --skip-keys argument to the RPM generator. `#602 <https://github.com/ros-infrastructure/bloom/pull/602>`_
- Fix conditional evaluation of Conflicts/Replaces. `#601 <https://github.com/ros-infrastructure/bloom/pull/601>`_
- Set Python2-Depends-Name to allow releasing from Focal. `#595 <https://github.com/ros-infrastructure/bloom/pull/595>`_
- Drop CATKIN_BUILD_BINARY_PACKAGE from cmake RPMs. `#589 <https://github.com/ros-infrastructure/bloom/pull/589>`_
- Remove catkin reference from comment in non-catkin pkgs. `#588 <https://github.com/ros-infrastructure/bloom/pull/588>`_

0.9.7 (2020-05-04 12:45:00 -0800)
---------------------------------
- Removed rmw implementations from typesupport dependencies for Foxy. `#587 <https://github.com/ros-infrastructure/bloom/issues/587>`_

0.9.6 (2020-05-04 05:15:00 -0800)
---------------------------------
- Fix a packaging bug affecting only Debian packages

0.9.5 (2020-05-01 15:00:00 -0800)
---------------------------------
- Fixed interactive prompt when not running interactively. `#584 <https://github.com/ros-infrastructure/bloom/issues/584>`_
- Updated vendor typesupport dependencies for Foxy. `#586 <https://github.com/ros-infrastructure/bloom/issues/586>`_
- Happy International Workers' Day.


0.9.4 (2020-04-30 06:30:00 -0800)
---------------------------------
- Restored return code of rosdep failure when non-interactive. `#577 <https://github.com/ros-infrastructure/bloom/issues/577>`_
- Added the development branch to info log when using version auto-detection. `#579 <https://github.com/ros-infrastructure/bloom/issues/579>`_
- Added non-interactive option to git-bloom-release command. `#581 <https://github.com/ros-infrastructure/bloom/issues/581>`_


0.9.3 (2020-03-02 17:30:00 -0800)
---------------------------------
- Fix a packaging bug affecting only Debian packages

0.9.2 (2020-03-02 13:00:00 -0800)
---------------------------------
- Add option to disable weak RPM dependencies. `#574 <https://github.com/ros-infrastructure/bloom/issues/574>`_
- If not interactive, don't prompt to fix broken rosdep keys. `#573 <https://github.com/ros-infrastructure/bloom/issues/573>`_
- Make the RPM spec templates look more like the results. `#568 <https://github.com/ros-infrastructure/bloom/issues/568>`_
- Suppress automatic rosdep with BLOOM_SKIP_ROSDEP_UPDATE. `#565 <https://github.com/ros-infrastructure/bloom/issues/565>`_
- Provide group membership information in RPM packages. `#564 <https://github.com/ros-infrastructure/bloom/issues/564>`_
- Add an optional release version suffix to RPM templates. `#569 <https://github.com/ros-infrastructure/bloom/issues/569>`_
- Drop Connext from RPM RMW list. `#566 <https://github.com/ros-infrastructure/bloom/issues/566>`_
- Provide -devel, -doc and -runtime virtual packages in RPM. `#563 <https://github.com/ros-infrastructure/bloom/issues/563>`_
- Print the OS name along with OS version for RPMs. `#562 <https://github.com/ros-infrastructure/bloom/issues/562>`_

0.9.1 (2020-02-03 10:00:00 -0800)
---------------------------------
- Added a debinc of 100 to prevent conflicts with upstream Ubuntu versions.
- Added version dependency on ``rosdistro`` version ``0.8.0`` to prevent use of out-of-date version which caused pull requests to fail.
- Changed to not try and create a pull request if ``--pretend`` is used.

0.9.0 (2019-10-18 14:15:00 -0800)
---------------------------------
- Fixed possibly unescaped logger formatting in version. `#553 <https://github.com/ros-infrastructure/bloom/pull/553>`_
- Added ament package support to RPM generation. `#534 <https://github.com/ros-infrastructure/bloom/pull/534>`_
- Added ROS_PYTHON_VERSION to dependency condtionals. `#551 <https://github.com/ros-infrastructure/bloom/pull/551>`_
  With this change rosdistro v4 indexes must define the ``python_version`` field introduced in `ros-infrastructure/rep#207 <https://github.com/ros-infrastructure/rep/pull/207`_.
- Fixed deprecation warnings by using yaml.safe_load. `#530 <https://github.com/ros-infrastructure/bloom/pull/530>`_
- Changed release suites, dropping all older than Ubuntu Xenial and adding Ubuntu Cosmic, Disco, and Eoan. `#543 <https://github.com/ros-infrastructure/bloom/pull/543>`_
- Improved error handling for package conditions and index files. `#537 <https://github.com/ros-infrastructure/bloom/pull/537>`_
- Added feature to disable pull request generation via argument or ``BLOOM_NO_ROSDISTRO_PULL_REQUEST`` environment variable. `#548 <https://github.com/ros-infrastructure/bloom/pull/548>`_
- Updated RPM generator to always create a source archive. `#540 <https://github.com/ros-infrastructure/bloom/pull/540>`_
- Updated RPM spec templates. `#533 <https://github.com/ros-infrastructure/bloom/pull/533>`_

0.8.0 (2019-04-12 13:45:00 -0800)
---------------------------------
- Start release increment at 1. `#528 <https://github.com/ros-infrastructure/bloom/pull/528>`_
- Evaluate conditions in package.xml before resolving dependencies. `#519 <https://github.com/ros-infrastructure/bloom/pull/519>`_
- Update to prevent overwriting template files that exist in source. `#516 <https://github.com/ros-infrastructure/bloom/pull/516>`_
- Update debian templates to add trailing newline. `#523 <https://github.com/ros-infrastructure/bloom/pull/523>`_
- Fix str/bytes issue in Python 3 auth. `#522 <https://github.com/ros-infrastructure/bloom/pull/522>`_
- Use distribution type from index v4 to set ROS 2-specific behavior. `#502 <https://github.com/ros-infrastructure/bloom/pull/502>`_
- Fix tests to allow them to run outside of a git context. `#515 <https://github.com/ros-infrastructure/bloom/pull/515>`_
- Fix tests to allow empty git environment. `#514 <https://github.com/ros-infrastructure/bloom/pull/514>`_
- Invoke scripts using the current python executable. `#513 <https://github.com/ros-infrastructure/bloom/pull/513>`_
- Drop support for older distributions. (Retroactive to 0.6.8) `#512 <https://github.com/ros-infrastructure/bloom/pull/512>`_

0.7.2 (2019-01-26 07:45:00 -0800)
---------------------------------
- Updated a test to support mixed rosdistro index. `#510 <https://github.com/ros-infrastructure/bloom/pull/510>`_
- Updated to use yaml.safe_load for untrusted yaml input. `#508 <https://github.com/ros-infrastructure/bloom/pull/508>`_
- Required rosdistro 0.15.0 for package format 3 conditional dependency support. `#511 <https://github.com/ros-infrastructure/bloom/pull/511>`_

0.7.1 (2019-01-11 16:05:00 -0800)
---------------------------------
- Fix some bugs from python3 compatibility. `#505 <https://github.com/ros-infrastructure/bloom/pull/505>`_

0.7.0 (2019-01-10 09:45:00 -0800)
---------------------------------
- Quote files removed with `git rm -rf`. `#491 <https://github.com/ros-infrastructure/bloom/pull/491>`_
- Only consider rosdistros of the same type when looking for a repo name in recent distros. `#501 <https://github.com/ros-infrastructure/bloom/pull/501>`_
- Fix python 3 support for pull request generation. `#489 <https://github.com/ros-infrastructure/bloom/pull/489>`_

0.6.9 (2018-11-15 08:45:00 -0800)
---------------------------------
- Added Crystal Clemmys (crystal) to the list of ROS 2 rosdistros. `#495 <https://github.com/ros-infrastructure/bloom/pull/495>`_

0.6.8 (2018-11-07 06:45:00 -0800)
---------------------------------
- Added support for rosdistro index v4. Bloom now requires rosdistro 0.7.0. `#493 <https://github.com/ros-infrastructure/bloom/pull/493>`_
- Refactored for future GitLab pull request support. `#486 <https://github.com/ros-infrastructure/bloom/pull/486>`_
- Added basic command execution test. `#487 <https://github.com/ros-infrastructure/bloom/pull/487>`_

0.6.7 (2018-09-24 06:30:00 -0800)
---------------------------------
- Added debian/copyright file to debian package when license file is specified in package.xml. `#470 <https://github.com/ros-infrastructure/bloom/pull/470>`_
- Refactored release command to prepare for GitLab pull request support. `#483 <https://github.com/ros-infrastructure/bloom/pull/483>`_
- Fixed outdated GitHub URL in help text. `#484 <https://github.com/ros-infrastructure/bloom/pull/484>`_
- Added entry to tracks.yaml to store the upstream tag of the last release. `#472 <https://github.com/ros-infrastructure/bloom/pull/472>`_

0.6.6 (2018-06-28 19:44:00 -0800)
---------------------------------
- Updated vendor typesupport injection for ROS 2. `#477 <https://github.com/ros-infrastructure/bloom/pull/477>`_

0.6.5 (2018-06-25 07:00:00 -0800)
---------------------------------
- Added injection of vendor typesupport packages into build deps for ROS 2. `#475 <https://github.com/ros-infrastructure/bloom/pull/475>`_
- Updated message wording. `#471 <https://github.com/ros-infrastructure/bloom/pull/471>`_
- Updated tested python versions. `#466 <https://github.com/ros-infrastructure/bloom/pull/466>`_

0.6.4 (2018-03-20 13:15:00 -0800)
---------------------------------
- Fixed use of non-dependency library. `#468 <https://github.com/ros-infrastructure/bloom/pull/468>`_

0.6.3 (2018-03-09 11:05:00 -0800)
---------------------------------
- Released for Debian buster. `#457 <https://github.com/ros-infrastructure/bloom/pull/457>`_
- Updated bloom-release: The --track/-t argument is now optional and defaults to the rosdistro. `#459 <https://github.com/ros-infrastructure/bloom/pull/459>`_
- Added bouncy to the list of ROS 2 rosdistros. `#462 <https://github.com/ros-infrastructure/bloom/pull/462>`_
- Added melodic to the list of rosdistros. `#463 <https://github.com/ros-infrastructure/bloom/pull/463>`_
- Added support for releasing repositories with submodules. `#461 <https://github.com/ros-infrastructure/bloom/pull/461>`_
- Improved release repository discovery with optional environment variable. `#460 <https://github.com/ros-infrastructure/bloom/pull/460>`_
- Fixed python3 encoding issue when processing rpm templates. `#464 <https://github.com/ros-infrastructure/bloom/pull/464>`_

0.6.2 (2018-01-08 13:45:00 -0800)
---------------------------------
- Removed test.* subpackages from installation. `#444 <https://github.com/ros-infrastructure/bloom/pull/444>`_
- Prepared for release supporting Ubuntu Bionic Beaver. `#452 <https://github.com/ros-infrastructure/bloom/pull/452>`_
- Fixed error message when GitHub Multi-Factor auth is enabled. `#451 <https://github.com/ros-infrastructure/bloom/pull/451>`_
- Added support for ROS 2 Ardent Apalone. `#453 <https://github.com/ros-infrastructure/bloom/pull/453>`_
- Fixed an HTTP/JSON encoding issue in bloom-release for Python 3. `#445 <https://github.com/ros-infrastructure/bloom/pull/445>`_

0.6.1 (2017-10-20 13:45:00 -0800)
---------------------------------
- Switched to PyPI JSON API for online updates check. `#438 <https://github.com/ros-infrastructure/bloom/pull/438>`_
- Fixed regression in bloom-generate. `#440 <https://github.com/ros-infrastructure/bloom/pull/440>`_
- Fixed bloom-release in python3. `#441 <https://github.com/ros-infrastructure/bloom/pull/441>`_

0.6.0 (2017-10-19 10:30:00 -0800)
---------------------------------
- Added artful support to release configuration.
- Added support for 'unmaintained' package status. `#427 <https://github.com/ros-infrastructure/bloom/pull/427>`_
- Fixed prompt for opening a pull request from a fork. `#431 <https://github.com/ros-infrastructure/bloom/pull/431>`_
- Fixed UTF-8 encoded text across Python 2 and 3. `#432 <https://github.com/ros-infrastructure/bloom/pull/432>`_
- Added support for ament packages on Debian. `#435 <https://github.com/ros-infrastructure/bloom/pull/435>`_

0.5.26 (2017-03-28 6:15:00 -0800)
---------------------------------
- Fix default answer to prompt in pull request field.

0.5.25 (2017-02-23 11:45:00 -0800)
----------------------------------
- Added the ``auto-commit`` option to quilt so that ``orig.tar.gz`` are reused release to release.
  See: `#419 <https://github.com/ros-infrastructure/bloom/pull/419>`_

0.5.24 (2017-02-23 11:45:00 -0800)
----------------------------------
- Fixed the way ros/rosdistro is forked.
- Added a ``--native`` option as an alternative to the default ``quilt`` for the Debian format.
- Added a prompt to ask users if they want to enable pull request building with the build farm.

0.5.23 (2016-10-25 11:45:00 -0800)
----------------------------------
- Fix to support change in output with git 2.9.3.
- Added more detailed message about skipping non-required distributions, e.g. Fedora.

0.5.22 (2016-08-24 13:30:00 -0800)
----------------------------------
- Repository names are now checked for bogus contents, to help detect accidental input.
- Fixed to allow use of unicode in the long description.
- Fixed a pagination related bug that occurred when trying to find a users rosdistro fork on GitHub.
- Updated GitHub interactions to allow for use from behind proxy servers.
- Added a new message to help people who have two-factor authentication.

0.5.21 (2016-03-04 18:30:00 -0800)
----------------------------------
- Debian pkg descriptions are now split into a synopsis and long description.
- The Conflicts and Replaces fields were moved to the general section in the Debian control file.
- Generated RPM's now explicitly set the library directory.
- Added option to allow quiet exit when a given OS has no platforms in the rosdistro.
- Added new default action item to generate for Debian (e.g. Jessie) in addition to Ubuntu and RPM.
- Fixed unnecessary ``!!python/unicode`` tags being put in the tracks.yaml.

0.5.20 (2015-04-23 15:00:00 -0800)
----------------------------------
- Updated conditional for special GitHub commit handling logic to include raw.githubusercontent.com.
- Updated GitHub commit handling logic to replace the branch part of the ROS distro index url with the commit for more stability.
- Set LC_ALL to C when calling out to ``git`` in order to avoid problems from output in different languages.

0.5.19 (2015-02-23 15:00:00 -0800)
----------------------------------
- Fixed tests so they could be run when multiple remotes were in the local bloom git instance.
- Fixed a new PEP8 checker test failure.
- Added a conflicts rule between the python3 and python2 .deb of bloom (python-bloom and python3-bloom) since they collide anyways with the installed scripts.
- Fixed a bug with Conflicts and Replaces in the debian generator.

0.5.18 (2015-02-09 15:53:10 -0800)
----------------------------------
- Fixed a bug which required a git repo as cwd.

0.5.17 (2015-02-03 15:53:10 -0800)
----------------------------------
- Now notifies about existing patches and ignore files when creating a new track.
- Now shows the git remotes before prompting for pushing of the release repository.
- Now uses reverse alphabetical ordering when selecting track configuration defaults, the idea is that ROS distributions with larger starting characters are more likely to be newer.
- Now guesses the release repository, the doc entry, and the source entry based on other distributions.
- Replace ``groovy`` with ``indigo`` in many defaults.
- Fixed a bug where whitespace in filenames and trailing ``~``'s caused a release failure.
- Now does a check of all rosdep keys before starting the Debian and RPM generators.
- Fixed a problem for recovering from platform specific rosdep key errors.
- Added options to ``bloom-release`` to override the release repository URL and release repository push URL.
- Now checks that all rosdep keys resolve to an installed that matches the default installer, i.e. ``apt`` and not ``pip``. This affectes the Debian and RPM generators.

0.5.16 (2014-12-15 14:30:00 -0700)
----------------------------------
- Hotfix to the Replaces/Conflicts template generation to prevent error causes extra whitespace.
  See: `#340 <https://github.com/ros-infrastructure/bloom/issues/340>`_

0.5.15 (2014-12-08 12:10:00 -0700)
----------------------------------
- Added support for REP 143 which allows for multiple distribution files, currently bloom uses the last one.
- Fix to Python3 support.
- ``ROSDISTRO_INDEX_URL``'s which point to githubusercontent.com will also be eligible for pull requests now.
- ``-DNDEBUG`` is now added to debian configurations by default.

0.5.14 (2014-11-26 08:10:00 -0700)
----------------------------------
- Hotfix for issue #329 which makes sure no extra new lines are introduced in the debian control file.
- Changed RPM build directory to have a more unique name.

0.5.13 (2014-11-24 17:10:00 -0700)
----------------------------------
- Fixed exception from importing ``bloom.logging``.
- Debian ``gbp.conf`` now uses ``upstream-tag``.
- Fixed a bug which overwrote the user provided debian folder during templating.
- Added support for utilizing the Conflicts and Replaces in ``package.xml``'s in the Debian control files.

0.5.12 (2014-09-24 15:28:16 -0700)
----------------------------------
- Pull requests are now opened against the commit from which the rosdistro index file is retrieved.
  This should address the remaining race condition in bloom allows pull requests which modify other entries.
  Addresses: `#252 <https://github.com/ros-infrastructure/bloom/issues/252>`_
- Pagination is now used when listing branches from GitHub.
  This addresses an error which occurred when the user had too many branches for page one.
  Addresses: `#273 <https://github.com/ros-infrastructure/bloom/issues/273>`_
- Improved support for unicode in changelogs.
  Addresses: `#260 <https://github.com/ros-infrastructure/bloom/issues/260>`_
- Added checking for .git and https on source and doc urls.
  Addresses: `#271 <https://github.com/ros-infrastructure/bloom/issues/271>`_
- Added check to make sure the release repository and the upstream repository are not the same.
  Addresses: `#267 <https://github.com/ros-infrastructure/bloom/issues/267>`_
- Added a check to make sure the changelog versions are sane with respect to the current version being released.
- Users can now skip rpm generation if rosdep keys are missing for fedora only.
- Improved error handling when GitHub's two factor authentication is encountered.
- Fixed a bug with expanding nested tarball's.
- Fixed order of changelogs in rpm generators.
- Non-interactive mode now applies to the confirmation for opening a pull request.

0.5.11 (2014-07-24 14:28:03 -0700)
----------------------------------
- Added rosrpm generator to the default list of generators.
- Upstream repository url and release repository url are now included in the summaries in pull requests.
- Updated the warning about changing track actions to make the transition of rosrpm in the default actions smoother.

0.5.10 (2014-06-16 11:48:51 -0700)
----------------------------------
- Fix cleaning behavior for trim and rebase, #281
- Fix a bug where stdout was getting truncated before a user prompt

0.5.9 (2014-05-22 14:55:59 -0700)
---------------------------------
- Revert to deb compat version 7 for Oneric

0.5.8 (2014-05-16 16:17:38 -0700)
---------------------------------
- Change deb compat version to 9 in order to get default compiler flags (with optimization) again

0.5.7 (2014-05-08 14:00:00 -0700)
---------------------------------
- Add versioned dependency on catkin_pkg 0.2.2

0.5.6 (2014-05-07 17:16:43 -0700)
---------------------------------
- When generating Debian and Fedora packaging files, explicitly include buildtool_export_depends with run_depends

0.5.5 (2014-05-01 10:24:31 -0700)
---------------------------------
- Add noarch flag to fedora generation for metapackages and packages marked as architecture_independent
- Fix the order of the arguments for git-bloom-config copy

0.5.4 (2014-04-11 16:09:00 -0700)
---------------------------------
- Fixed a problem with the documentation on readthedocs.org

0.5.3 (2014-04-11 15:51:09 -0700)
---------------------------------
- Fixed a bug when handling unicode failed on values which were int's
- Removed mention of username and hostname from bloom summaries in the release repo's README.md
- Fixed unicode handling in Fedora generation
- Modified handling of test dependencies for changes from REP-140 roll out
- Removed references to python-distribute in favor of python-setuptools
- Changed usuage of rosdep api to work with rosdep >= 0.10.27

0.5.2 (2014-03-04 20:52:09 -0600)
---------------------------------
- Pull request titles and body are now santized before printing
- Prevent unicode getting into the yaml files
- Make license tags required (rpm generation)
  Source RPMs will not build if the license tag is empty or missing.
  This will not be a problem for the vast majority of packages in ROS.
- Packages are now ordered in changelog summary
- Improved unicode support in Python2
- setup environment is now sourced before the install step (debian rules file)

0.5.1 (2014-02-24 16:03:29 -0800)
---------------------------------
- fix a bug related to setting the status description

0.5.0 (2014-02-23 21:55:00 -0800)
---------------------------------
- OAUTH is now used for creating pull requests.
  On the first pull request, bloom will ask for your github username and password.
  Using them it will create an authorization on your behalf and store it in your home folder.
  Specifically `~/.config/bloom`.
  From then on, bloom will no longer require your username and password for pull requests.
  Closed #177 and #170.
- Added checks to ensure that for github.com urls provided by users they end in `.git` and are `https://`
- Added some fixes and monkey patches to empy to better support unicode in changelogs
- Added additionally pull request checks, which should prevent some of the invalid pull requests from being created.
- Fixed a bug where packages which were removed from the repository were still getting generated.
- Merged preliminary Fedora generation support, provided by @cottsay
- Added changelog summaries to pull requests
- Added a prompt for users to enter doc, source, and maintenance status when releasing.

0.4.9 (2014-02-06 14:05:47 -0800)
---------------------------------
- Fixed another bug for first time releases, specifically first time releases which already have doc or source entries

0.4.8 (2014-01-29 14:19:24 -0600)
---------------------------------
- Fixed a bug for first time releases

0.4.7 (2014-01-24 15:50:00 -0800)
---------------------------------
- Fix bug in pull request opening with new rosdistro format

0.4.6 (2014-01-24 15:33:00 -0800)
---------------------------------
- Updates to support REP-0141 with rosdistro >= 0.3.0 and rosdep >= 0.10.25
- @ahendrix contributed an option for doing ssh key based pull request generation

0.4.5 (2014-01-22 10:58:50 -0800)
---------------------------------
- Added Python2/3 bilingual support, bloom should now install and work with Python3
- Added an assertion that the rosdistro version 1 is being used in preperation of REP-0141 roll out
- Fixed crash from unicode characters in the changelog
- Added assertions about the format of version numbers used
- Added check for git submodules, still not supported, but bloom will fail earlier with a better error
- Fixed a bug where empty folders containing a .gitignore in the upstream caused bloom to fail

0.4.4 (2013-07-22 17:50:55 -0700)
---------------------------------
- Properly handle pagination of github pages #174
- Made the pull request branch names more unique to avoid collisions in parallel releasing situations #178
- Disabled automatic opening of the webbrowser on Linux and added an option to disable it otherwise #162
- Fixed a problem where permissions where lost on templates, this applied specifically to loosing the executable flag on the debian rules file #179
- Only put the first maintainer listed in the debian/control file to prevent lintian errors #183

0.4.3 (2013-07-19 16:37:23 -0700)
---------------------------------
- Fixed a bug with creating new tracks
- Fixed a bug where the debian changelog would be wrong if a CHANGELOG.rst existed for the package, but there was no entry for this version being release
- Fixed a bug where the colorization of the diff could cause a crass to occur
- Added a versioned dependency on rosdistro-0.2.12, which addresses a rosdistro file formatting bug
- Fixed some issues with the stand alone rosdebian generator
- Temporary fix for github pagination problems

0.4.2 (2013-06-27 11:20:25 -0700)
---------------------------------
- Improved logging system slightly.
- Fixed the way logs are renamed after closing.
- Fixed a bug where names were not debian'ized for packages which rosdep could not resolve. #163
- Fixed a bug where a diff of the rosdistro file would fail when packages were being removed. #165
- Fixed a bug where upconverting repository configs could fail if a track.yaml and a bloom.conf existed. #166

0.4.1 (2013-06-25 12:17:13 -0700)
---------------------------------
- Fixed a bug which occurred on repositories with no previous releases. #158
- Fixed a bug where safety warnings were being printed when they should not have been. #159
- Fixed a bug where repositories with multiple packages did not consider peer packages when resolving rosdep keys. #160

0.4.0 (2013-06-19 17:13:36 -0700)
---------------------------------
- Automated Pull Requests have been re-enabled, but now the .netrc file is **not** used.
- REP-0132 CHANGELOG.rst files are now parsed and inserted into generated debian changes files.
- bloom now summarizes activity on the master branch, which is useful for figuring out what has been released recently.
- There is a new command bloom-generate, which allows generators to expose a stand alone generation command. For example, you can now run ``bloom-generate debian`` in a single catkin package and it will generate the needed files in the local ``debian`` folder. Addresses #121
- The command line options for ``bloom-release`` have been changed to be more explicit.
- The ``bloom`` branch is now deprecated, the ``master`` branch now holds all configurations and upstream overlay files. The ``bloom`` branch can be deleted after the automatic upgrade where bloom moves the needed files from the ``bloom`` branch to the ``master`` branch.
- Fuerte is no longer supported; this is because supporting fuerte was complicating the code base, use an older version of bloom (0.3.5) for fuerte releases.
- Packages can now be explicitly ignored by bloom by putting their names (separated by whitespace) in the <track>.ignored file in the master branch.
- Deprecated rosdep calls have been replaced with rosdistro.
- bloom now logs all output to log files in the ``~/.bloom_logs`` folder.
- Fixed several bugs:

    - Fixed use of tar as a vcs type #149
    - Fixed a bug where ``--new-track``'s changes would not take affect #147
    - bloom now allows a debian folder to already exist, overlaying other generated files #146
    - bloom now allows for an alternative release repository url which is used for pushing #137

0.3.5 (2013-04-17 11:03:50 -0700)
---------------------------------
- Temporarily disable automated pull requests while the new rosdistro format is being deployed.
- bloom now suggests likely alternatives when a repository is not found in the release file.

0.3.4 (2013-04-09 16:36:55 -0700)
---------------------------------
- Fixed a bug in the update notifier where the first run after updating still reports that bloom is out of date. #129
- bloom-release now respects global arguments like --version and --debug
- Improved messages around the cloning/pushing back of the working copy which takes a long time on large repos.
- Improved pull request failure message, indicating that the release was successful, but the pr was not. #131
- Fixed versioned dependencies in debians and setup.py. #130
- Fixed a bug with empty ~/.netrc files. #131
- General improvements with the automated pull request mechanism. #135
- Checks for valid metapackages using catkin_pkg now, adds version dependency of catkin_pkg at 0.1.11. #134

0.3.3 (2013-04-01 14:04:00 -0700)
---------------------------------
- bloom no longer allows users to release metapackages which do not have a CMakeLists.txt. See: `REP-0127 <http://ros.org/reps/rep-0127.html#metapackage>`_
- Fixed a bug related to gathering of package meta data on hg and svn repositories. #111
- Fixed a bug in git-bloom-patch which prevented users from running it directly. #110
- Fixed a bug where patches would not get applied after exporting them manually. #107
- Worked around a bug in vcstools which would not allow hg repositories to checkout to existing, empty directories. #112
- All git-bloom-* scripts now assert that they are in the root of a git repository. #113
- Added PEP8 check to the automated tests.
- bloom-release will now offer the user a git push --force if non-force fails.
- Added git-bloom-config [copy|rename] commands.
- Fixed a bug in the bloom.git.checkout api where it would return 0 on success, but should return True. #122
- bloom-release will now prompt the user for the release repository url if it is not in the rosdistro file. #125
- bloom-release will now offer to automatically open a pull-request for the user, if the user's .netrc file is setup for github. #126

0.3.2 (2013-03-06 17:49:51 -0800)
---------------------------------
- Fixed a bug in vcs url templating.
- Improved the performance of git-bloom-config.
- Added an --unsafe global option which will disable some of the safety mechanisms in bloom, making releasing about twice as fast but at the expense of errors putting the local release repository in an inconsistent state. Use with caution.
- Added support for templating stack.xml files like package.xml files in the import-upstream step.
- Fixed a bug where bloom failed if you call it and you were not on a branch
- Added global arguments to some commands which were still lacking them
- Fixed a bug where bloom would create None/<version> tags (these should be deleted manually if found)
- Got the automated tests fixed and running in travis again
- Added emoji icons for OS X users with lion or greater

0.3.1 (2013-02-26 18:00:47 -0800)
---------------------------------
- Fixed handling of non-standard archive names in git-bloom-import-upstream.
  This was a bug where if the archive only had the name of the package then it would fail to be processed by import-upstream.
- Fixed an issue when blooming from svn upstream.
  This issue was caused by improperly handling the release_tag configuration when dealing with svn

0.3.0 (2013-02-26 14:04:21 -0800)
---------------------------------
- Generators can now be added using the distribute entry_points machanism
- There is now a debian/<rosdistro>/<package_name> branch before forking into debian/<rosdistro>/<debian_distro>/<package_name>
  The debian/<rosdistro> branch now contains the untemplated debain files, so that they can be patched before being templated.
- Users are now dropped into a shell when patch merging fails, allowing them to resolve the problem and continue.
- New generator rosrelease, makes the release tag release/<rosdistro>/<package_name> instead of release/<package_name>
- Bloom now checks to see if it is the latest version available and warns if it is not
- Configurations are now stored in "tracks" so that there can be multiple release configurations in each release repository
- New command bloom-export-upstream, this command creates an archive (tar.gz) of upstream given a uri, type, and reference to archive
- Refactored git-bloom-import-upstream, this command only takes an archive (tar.gz) now
- Configurations are now stored on the bloom branch in YAML
- git-bloom-release now takes only one argument, the release track to execute
- Files can be automatically overlaid onto upstream using a patches folder in the bloom branch
  This allows you to put a package.xml onto upstream without a patch in the release branch.
- package.xml files overlaid onto upstream branch from the patches folder in the bloom branch are templated on the version
- Release tags now contain release increment numbers, similar to the debian increment numbers, e.g. release/groovy/foo/0.1.0 is now release/groovy/foo/0.1.0-0
- New command bloom-release <repository> [<track>], which will release a repository end-to-end
  It will fetch the release repository using info from the ROS distro file, run bloom, then push the results


