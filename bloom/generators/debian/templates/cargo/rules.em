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
	# dh-cargo's configure step copies this file into place, so it has to
	# exist even when we aren't vendoring dependencies (see Debian wiki: Rust
	# Packaging). It does not need a Cargo.lock: that same step removes one.
	touch debian/cargo-checksum.json
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi && \
	dh_auto_configure
	# Generate a pallet-patcher config pointing cargo at the crates that are
	# already on disk. The search paths are consulted in the order given, so
	# crates from other ROS packages win over the ones the platform ships.
	pallet-patcher --output-format=toml Cargo.toml \
		@(InstallationPrefix)/share/cargo/registry \
		/usr/share/cargo/registry > pallet-patcher.toml
	# The sourcedeb job vendors the crates.io dependencies into debian/vendor
	# and rejects crates from any other source, so the replacement cargo needs
	# to build against them is always this one stanza. It covers every crate
	# left unpatched above, which is deliberately the only way the vendored
	# copies are reached: patching them in would turn them into path
	# dependencies, and cargo-auditable redacts local paths from the .dep-v0
	# section, losing them from the SBOM. Note the directory has to be
	# absolute: cargo resolves relative paths in a file passed to '--config'
	# against that file's grandparent directory, not the working directory.
	if [ -d debian/vendor ]; then \
		printf '\n[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "$(CURDIR)/debian/vendor"\n' >> pallet-patcher.toml ; \
	fi
	# Every crate has to be on disk by now, so refuse to reach the network.
	# Set as config rather than passing --offline so that it also covers the
	# cargo invocations we do not spell out ourselves. This stops cargo
	# fetching, it does NOT stop build scripts or proc macros from opening
	# their own connections; that needs an isolated build container.
	printf '\n[net]\noffline = true\n' >> pallet-patcher.toml

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
	cargo auditable build --release --config pallet-patcher.toml

override_dh_auto_test:
	# In case we're installing to a non-standard location, look for a setup.sh
	# in the install tree and source it.  It will set things like
	# CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, and PYTHONPATH.
	echo -- Running tests. Even if one of them fails the build is not canceled.
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi
	cargo test --config pallet-patcher.toml || true

override_dh_auto_install:
	# Classify the crate's targets ourselves rather than rely on dh-cargo's
	# libpkg/binpkg dispatch, which keys on Debian package-name heuristics
	# (librust-*-dev vs. others) that bloom-generated ROS package names don't
	# satisfy. We then run whichever of the two install branches apply:
	#   - HAS_LIB: lay down the unpacked crate source under
	#     <prefix>/share/cargo/registry/<name>-<version>/ so downstream ROS
	#     Rust packages can resolve this crate via pallet-patcher. Mirrors
	#     dh-cargo cargo.pm:install() libpkg branch.
	#   - HAS_BIN: run `cargo auditable install`, which wraps cargo and
	#     embeds a compressed JSON SBOM into each binary's .dep-v0 ELF
	#     section. Tools that read it: cargo audit bin, trivy, grype, syft,
	#     osv-scanner, rust-audit-info. --no-track suppresses .crates.toml.
	set -e ; \
	if [ -f "@(InstallationPrefix)/setup.sh" ]; then . "@(InstallationPrefix)/setup.sh"; fi ; \
	META=$$(cargo metadata --no-deps --format-version 1) ; \
	CRATE_NAME=$$(printf '%s' "$$META" | python3 -c "import sys,json;print(json.load(sys.stdin)['packages'][0]['name'])") ; \
	CRATE_VER=$$(printf '%s' "$$META" | python3 -c "import sys,json;print(json.load(sys.stdin)['packages'][0]['version'])") ; \
	HAS_LIB=$$(printf '%s' "$$META" | python3 -c "import sys,json;p=json.load(sys.stdin)['packages'][0];L={'lib','rlib','dylib','cdylib','staticlib','proc-macro'};print(int(any(k in L for t in p['targets'] for k in t['kind'])))") ; \
	HAS_BIN=$$(printf '%s' "$$META" | python3 -c "import sys,json;p=json.load(sys.stdin)['packages'][0];print(int(any('bin' in t['kind'] for t in p['targets'])))") ; \
	if [ "$$HAS_LIB" = "1" ]; then \
		TARGET="$(CURDIR)/debian/@(Package)@(InstallationPrefix)/share/cargo/registry/$$CRATE_NAME-$$CRATE_VER" ; \
		install -d "$$TARGET" ; \
		find . -mindepth 1 -maxdepth 1 \
			\! -name target \! -name debian \! -name .git \
			\! -name '.obj-*' \! -name 'pallet-patcher.toml' \
			-exec cp -a -t "$$TARGET" {} + ; \
		rm -rf "$$TARGET/target" ; \
		cp debian/cargo-checksum.json "$$TARGET/.cargo-checksum.json" ; \
		[ -z "$$SOURCE_DATE_EPOCH" ] || touch -d@@$$SOURCE_DATE_EPOCH "$$TARGET/Cargo.toml" ; \
	fi ; \
	if [ "$$HAS_BIN" = "1" ]; then \
		cargo auditable install --path . --config pallet-patcher.toml \
			--root "$(CURDIR)/debian/@(Package)@(InstallationPrefix)" \
			--no-track ; \
	fi
