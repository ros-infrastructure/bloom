.PHONY: all setup clean_dist distro clean install

VERSION=`./setup.py --version`

USERNAME ?= $(shell whoami)

UNAME := $(shell uname)

.PHONY: doc
doc:
	python setup.py build_sphinx
ifeq ($(UNAME),Darwin)
	@open doc/build/html/index.html
else
	@echo "Not opening index.html on $(UNAME)"
endif

publish_docs:
	PYTHONPATH=`pwd`/bloom:$PYTHONPATH python doc/publish_docs.py

all:
	echo "noop for debbuild"

setup:
	echo "building version ${VERSION}"

clean_dist:
	-rm -f MANIFEST
	-rm -rf dist
	-rm -rf deb_dist

distro: setup clean_dist
	python setup.py sdist

clean: clean_dist
	echo "clean"

install: distro
	sudo checkinstall python setup.py install

testsetup:
	echo "running bloom tests"

test: testsetup
	python setup.py nosetests

test--pdb-failures: testsetup
	python setup.py nosetests --pdb-failures

NEW_VERSION := $(shell python doc/bump_version.py setup.py --version_only)

pre-release:
	git push --all && git push --tags
	# Bump the version
	python doc/bump_version.py setup.py > setup.py_tmp
	mv setup.py_tmp setup.py
	# Set the permissions
	chmod 775 setup.py
	# Commit bump
	git commit -m "$(NEW_VERSION)" setup.py
	# Tag it
	git tag -f $(NEW_VERSION)

release: pre-release publish_docs
	@echo "Now push the result with git push --all"
