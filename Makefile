.PHONY: all setup clean_dist distro clean install upload push

NAME=bloom
VERSION=`./setup.py --version`

OUTPUT_DIR=deb_dist

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

push: distro
	python setup.py sdist register upload
	scp dist/${NAME}-${VERSION}.tar.gz ${USERNAME}@ipr:/var/www/pr.willowgarage.com/html/downloads/${NAME}

clean: clean_dist
	echo "clean"

install: distro
	sudo checkinstall python setup.py install

deb_dist:
	# need to convert unstable to each distro and repeat
	python setup.py --command-packages=stdeb.command sdist_dsc --workaround-548392=False bdist_deb

upload-packages: deb_dist
	dput -u -c dput.cf all-shadow ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 
	dput -u -c dput.cf all-shadow-fixed ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 
	dput -u -c dput.cf all-ros ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 

upload-building: deb_dist
	dput -u -c dput.cf all-building ${OUTPUT_DIR}/${NAME}_${VERSION}-1_amd64.changes 

upload: upload-building upload-packages

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

release: pre-release publish_docs push upload
	@echo "Now push the result with git push --all"
butts lol
