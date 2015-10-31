#!/bin/sh

if ! type python3.5 > /dev/null; then
    sudo add-apt-repository ppa:fkrull/deadsnakes > /dev/null 2>&1
    sudo apt-get -qq update > /dev/null 2>&1
    sudo apt-get -qq install python3.5-dev > /dev/null 2>&1
fi

# drone.io run script
pip install tox
tox -e py27,py35,docs,py27examples,py35examples,qa
