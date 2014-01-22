.PHONY: all clean_dist clean doc

VERSION=`./setup.py --version`

USERNAME ?= $(shell whoami)

UNAME := $(shell uname)

doc:
	python setup.py build_sphinx
ifeq ($(UNAME),Darwin)
	@open doc/build/html/index.html
else
	@echo "Not opening index.html on $(UNAME)"
endif

all:
	echo "noop for debbuild"

clean_dist:
	-rm -f MANIFEST
	-rm -rf dist
	-rm -rf deb_dist

clean: clean_dist
	echo "clean"

NEW_VERSION := $(shell python docs/bump_version.py setup.py --version_only)

pre-release:
	# Bump the version
	python docs/bump_version.py setup.py > setup.py_tmp
	mv setup.py_tmp setup.py
	# Set the permissions
	chmod 775 setup.py
	# Commit bump
	git commit -m "$(NEW_VERSION)" setup.py
	# Tag it
	git tag -f $(NEW_VERSION)

release: pre-release
	@echo "Now push the result with git push --all"
