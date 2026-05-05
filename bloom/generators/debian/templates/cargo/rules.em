#!/usr/bin/make -f
# -*- makefile -*-
# Sample debian/rules that uses debhelper.
# This file was originally written by Joey Hess and Craig Small.
# As a special exception, when this file is copied by dh-make into a
# dh-make output file, you may use that output file without restriction.
# This special exception was added by Craig Small in version 0.37 of dh-make.

# Uncomment this to turn on verbose mode.
export DH_VERBOSE=1
# TODO: remove the LDFLAGS override.  It's here to avoid esoteric problems
# of this sort:
#  https://code.ros.org/trac/ros/ticket/2977
#  https://code.ros.org/trac/ros/ticket/3842
export LDFLAGS=
export PKG_CONFIG_PATH=@(InstallationPrefix)/lib/pkgconfig
# Explicitly enable -DNDEBUG, see:
# 	https://github.com/ros-infrastructure/bloom/issues/327
export DEB_CXXFLAGS_MAINT_APPEND=-DNDEBUG

DEB_HOST_GNU_TYPE ?= $(shell dpkg-architecture -qDEB_HOST_GNU_TYPE)

%:
	dh $@@ -v --buildsystem=cargo --builddirectory=.obj-$(DEB_HOST_GNU_TYPE)

override_dh_auto_configure:
	# dh-cargo's configure step expects these two files to exist, even when
	# we aren't vendoring dependencies. Touching an empty cargo-checksum.json
	# and Cargo.lock is the canonical workaround (see Debian wiki: Rust Packaging).
	# TODO: once bloom grows a proper vendoring story, the checksum file
	# should be generated from the vendored crates instead of stubbed out.
	touch debian/cargo-checksum.json Cargo.lock
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi && \
	dh_auto_configure
	# Generate a pallet-patcher config so that, once we have a viable
	# vendoring solution, we can point cargo at a ROS-local registry.
	pallet-patcher --output-format=toml Cargo.toml > pallet-patcher.toml

override_dh_auto_clean:
	dh_auto_clean
	rm -f debian/cargo-checksum.json pallet-patcher.toml

override_dh_auto_build:
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi
	# Call cargo directly to avoid the dh-cargo Python wrapper interfering
	# with registry resolution when dependencies are pre-fetched offline.
	# `cargo auditable` is a drop-in wrapper that embeds a compressed JSON
	# dependency list into a `.dep-v0` linker section of every produced
	# binary. Tools like `cargo audit bin`, trivy, grype, syft, and
	# `rust-audit-info` can read it back. URLs and local paths are redacted
	# by design, so no `/work/...` style paths leak into shipped artifacts.
	cargo auditable build --release

override_dh_auto_test:
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	echo -- Running tests. Even if one of them fails the build is not canceled.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi
	cargo test || true

override_dh_auto_install:
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi
	# Call cargo install directly rather than through dh_auto_install so that
	# the dh-cargo Python wrapper does not interfere with registry resolution.
	# --no-track suppresses .crates.toml/.crates2.json metadata in the package.
	# `cargo auditable` wraps cargo and embeds a compressed JSON dependency
	# tree into the resulting binary's `.dep-v0` ELF section. This replaces
	# the previous hand-rolled `cargo tree` manifest: the embedded data is
	# the canonical SBOM, can't drift from the binary, and is consumed by
	# `cargo audit bin`, trivy, grype, syft, osv-scanner, and `rust-audit-info`.
	cargo auditable install --path . \
		--root "$(CURDIR)/debian/@(Package)@(InstallationPrefix)" \
		--no-track
