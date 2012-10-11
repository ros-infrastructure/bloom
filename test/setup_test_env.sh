#! /usr/bin/env bash
# must use bash for BASH_SOURCE, and must not try to get rid of /./
# test in this folder, parent folder, and grandparent folder
BASEDIR=`pwd`/$(dirname $BASH_SOURCE)
echo export PYTHONPATH=$BASEDIR/../src:$PYTHONPATH
export PYTHONPATH=$BASEDIR/../src:$PYTHONPATH
echo export PATH=$BASEDIR/../bin:$PATH
export PATH=$BASEDIR/../bin:$PATH