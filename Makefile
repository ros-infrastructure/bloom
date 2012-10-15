.PHONY: all setup clean_dist distro clean install upload push

NAME=bloom

OUTPUT_DIR=deb_dist

USERNAME := $(shell whoami)
# If william, use my WG login wwoodall
ifeq ($(USERNAME),william)
	USERNAME := wwoodall
endif


all:
	echo "noop for debbuild"

setup:
	echo "building version ${`./setup.py --version`}"

clean_dist:
	-rm -f MANIFEST
	-rm -rf dist
	-rm -rf deb_dist

distro: setup clean_dist
	python setup.py sdist

push: distro
	python setup.py sdist register upload
	scp dist/${NAME}-${`./setup.py --version`}.tar.gz ${USERNAME}@ipr:/var/www/pr.willowgarage.com/html/downloads/${NAME}

clean: clean_dist
	echo "clean"

install: distro
	sudo checkinstall python setup.py install

deb_dist:
	# need to convert unstable to each distro and repeat
	python setup.py --command-packages=stdeb.command sdist_dsc --workaround-548392=False bdist_deb

upload-packages: deb_dist
	dput -u -c dput.cf all-shadow ${OUTPUT_DIR}/${NAME}_${`./setup.py --version`}-1_amd64.changes 
	dput -u -c dput.cf all-shadow-fixed ${OUTPUT_DIR}/${NAME}_${`./setup.py --version`}-1_amd64.changes 
	dput -u -c dput.cf all-ros ${OUTPUT_DIR}/${NAME}_${`./setup.py --version`}-1_amd64.changes 

upload-building: deb_dist
	dput -u -c dput.cf all-building ${OUTPUT_DIR}/${NAME}_${`./setup.py --version`}-1_amd64.changes 

upload: upload-building upload-packages

testsetup:
	echo "running bloom tests"

test: testsetup
	python setup.py nosetests

test--pdb-failures: testsetup
	python setup.py nosetests --pdb-failures
