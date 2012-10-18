#!/usr/bin/make -f
# -*- makefile -*-

# Uncomment this to turn on verbose mode.
# don't use version.major, version.minor, this is pys >= 2.7
@{
from sys import version_info as v
pyversion="%u.%u" % (v[0], v[1])
import platform
}
export DH_VERBOSE=1
export DH_OPTIONS=-v
# this is the --install-layout=deb variety

# elsewhere there is a PYTHON_PACKAGES_DIR defined.  We shouldn't
# need this here:  this file is only for debian.
export PYTHONPATH=@(InstallationPrefix)/lib/python@(pyversion)/dist-packages
%:
	dh  $@@

override_dh_auto_configure:
	dh_auto_configure -Scmake -- \
		-DCATKIN_BUILD_BINARY_PACKAGE="1" \
		-DCMAKE_INSTALL_PREFIX="@(InstallationPrefix)" \
		-DCMAKE_PREFIX_PATH="@(InstallationPrefix)"
	dh_auto_configure -Spython_distutils

override_dh_auto_install:
	dh_auto_install -Scmake
	dh_auto_install -Spython_distutils -- \
		--prefix="@(InstallationPrefix)" --install-layout=deb

override_dh_auto_build:
	dh_auto_build -Scmake
	dh_auto_build -Spython_distutils


