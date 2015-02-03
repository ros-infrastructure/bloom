# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import pkg_resources
import sys
import traceback

from bloom.logging import debug
from bloom.logging import error
from bloom.logging import info

from bloom.util import code
from bloom.util import maybe_continue
from bloom.util import print_exc

try:
    from rosdep2 import create_default_installer_context
    from rosdep2.catkin_support import get_catkin_view
    from rosdep2.lookup import ResolutionError
    import rosdep2.catkin_support
except ImportError as err:
    debug(traceback.format_exc())
    error("rosdep was not detected, please install it.", exit=True)

BLOOM_GROUP = 'bloom.generators'
DEFAULT_ROS_DISTRO = 'indigo'


def list_generators():
    generators = []
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        generators.append(entry_point.name)
    return generators


def load_generator(generator_name):
    for entry_point in pkg_resources.iter_entry_points(group=BLOOM_GROUP):
        if entry_point.name == generator_name:
            return entry_point.load()

view_cache = {}


def get_view(os_name, os_version, ros_distro):
    global view_cache
    key = os_name + os_version + ros_distro
    if key not in view_cache:
        value = get_catkin_view(ros_distro, os_name, os_version, False)
        view_cache[key] = value
    return view_cache[key]


def invalidate_view_cache():
    global view_cache
    view_cache = {}


def update_rosdep():
    info("Running 'rosdep update'...")
    try:
        rosdep2.catkin_support.update_rosdep()
    except:
        print_exc(traceback.format_exc())
        error("Failed to update rosdep, did you run 'rosdep init' first?",
              exit=True)


def resolve_more_for_os(rosdep_key, view, installer, os_name, os_version):
    """
    Resolve rosdep key to dependencies and installer key.
    (This was copied from rosdep2.catkin_support)

    :param os_name: OS name, e.g. 'ubuntu'
    :returns: resolved key, resolved installer key, and default installer key

    :raises: :exc:`rosdep2.ResolutionError`
    """
    d = view.lookup(rosdep_key)
    ctx = create_default_installer_context()
    os_installers = ctx.get_os_installer_keys(os_name)
    default_os_installer = ctx.get_default_os_installer_key(os_name)
    inst_key, rule = d.get_rule_for_platform(os_name, os_version,
                                             os_installers,
                                             default_os_installer)
    assert inst_key in os_installers
    return installer.resolve(rule), inst_key, default_os_installer


def resolve_rosdep_key(
    key,
    os_name,
    os_version,
    ros_distro=None,
    ignored=None,
    retry=True
):
    ignored = ignored or []
    ctx = create_default_installer_context()
    try:
        installer_key = ctx.get_default_os_installer_key(os_name)
    except KeyError:
        BloomGenerator.exit("Could not determine the installer for '{0}'"
                            .format(os_name))
    installer = ctx.get_installer(installer_key)
    ros_distro = ros_distro or DEFAULT_ROS_DISTRO
    view = get_view(os_name, os_version, ros_distro)
    try:
        return resolve_more_for_os(key, view, installer, os_name, os_version)
    except (KeyError, ResolutionError) as exc:
        debug(traceback.format_exc())
        if key in ignored:
            return None, None, None
        if isinstance(exc, KeyError):
            error("Could not resolve rosdep key '{0}'".format(key))
            returncode = code.GENERATOR_NO_SUCH_ROSDEP_KEY
        else:
            error("Could not resolve rosdep key '{0}' for distro '{1}':"
                  .format(key, os_version))
            info(str(exc), use_prefix=False)
            returncode = code.GENERATOR_NO_ROSDEP_KEY_FOR_DISTRO
        if retry:
            error("Try to resolve the problem with rosdep and then continue.")
            if maybe_continue():
                update_rosdep()
                invalidate_view_cache()
                return resolve_rosdep_key(key, os_name, os_version, ros_distro,
                                          ignored, retry=True)
        BloomGenerator.exit("Failed to resolve rosdep key '{0}', aborting."
                            .format(key), returncode=returncode)


def default_fallback_resolver(key, peer_packages):
    BloomGenerator.exit("Failed to resolve rosdep key '{0}', aborting."
                        .format(key), returncode=code.GENERATOR_NO_SUCH_ROSDEP_KEY)


def resolve_dependencies(
    keys,
    os_name,
    os_version,
    ros_distro=None,
    peer_packages=None,
    fallback_resolver=None
):
    ros_distro = ros_distro or DEFAULT_ROS_DISTRO
    peer_packages = peer_packages or []
    fallback_resolver = fallback_resolver or default_fallback_resolver

    resolved_keys = {}
    keys = [k.name for k in keys]
    for key in keys:
        resolved_key, installer_key, default_installer_key = \
            resolve_rosdep_key(key, os_name, os_version, ros_distro,
                               peer_packages, retry=True)
        # Do not compare the installer key here since this is a general purpose function
        # They installer is verified in the OS specific generator, when the keys are pre-checked.
        if resolved_key is None:
            resolved_key = fallback_resolver(key, peer_packages)
        resolved_keys[key] = resolved_key
    return resolved_keys


class GeneratorError(Exception):
    def __init__(self, msg, returncode=code.UNKNOWN):
        super(GeneratorError, self).__init__("Error running generator: " + msg)
        self.returncode = returncode

    @staticmethod
    def excepthook(etype, value, traceback):
        GeneratorError.sysexcepthook(etype, value, traceback)
        if isinstance(value, GeneratorError):
            sys.exit(value.returncode)

    sys.excepthook, sysexcepthook = excepthook.__func__, staticmethod(sys.excepthook)


class BloomGenerator(object):
    """
    Abstract generator class, from which all bloom generators inherit.
    """
    generator_type = None
    title = 'no title'
    description = None
    help = None

    @classmethod
    def exit(cls, msg, returncode=code.UNKNOWN):
        raise GeneratorError(msg, returncode)

    def prepare_arguments(self, parser):
        """
        Argument preparation hook, should be implemented in child class

        :param parser: argparse.ArgumentParser on which to call add_argument()
        """
        pass

    def handle_arguments(self, args):
        """
        Hook to handle parsed arguments from argparse
        """
        debug("BloomGenerator.handle_arguments: got args -> " + str(args))

    def summarize(self):
        """
        Summarize the command, consider listing configurations here
        """
        info("Running " + self.title + " generator")

    def get_branching_arguments(self):
        """
        Return a list of tuples, each representing parameters for branching.

        Override this to return something other than [] if this generator
        needs to produce branches.

        The tuples can either be singular (destination,), or contain two
        elements (destination, source). Optionally, a third tuple element
        can be a bool indicating if git-bloom-branch should be interactive:
        (destination, source, interactive)

        :returns: list of tuples containing arguments for git-bloom-branch
        """
        return []

    def pre_modify(self):
        """
        Hook for last minute checks

        This is the last call before the generator is expected to start
        performing modifications to the repository.

        :returns: return code, return 0 or None for OK, anything else on error
        """
        return 0

    def pre_branch(self, destination, source):
        """
        Pre-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_branch(self, destination, source):
        """
        Post-branching hook

        :param destination: destination branch name
        :param source: source branch name

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_export_patches(self, branch_name):
        """
        Pre-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_export_patches(self, branch_name):
        """
        Post-patch-export hook

        :param branch_name: name of the branch patches are being exported from

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_rebase(self, branch_name):
        """
        Pre-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_rebase(self, branch_name):
        """
        Post-rebase hook

        :param branch_name: name of the branch rebase is being done on

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def pre_patch(self, branch_name):
        """
        Pre-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0

    def post_patch(self, branch_name):
        """
        Post-patching hook

        :param branch_name: name of the branch being patched

        :returns: return code, return 0 or None for OK, anythign else on error
        """
        return 0
