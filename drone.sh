#!/bin/sh
# drone.io run script
pip install tox
tox -e py27,py33,docs,py27examples,py33examples,qa
