#!/bin/sh
# drone.io run script
pip install tox coverage
tox -e py27,py33,docs,py27examples,py33examples,qa
coverage combine

# forked python-coverage with --nogit option
pip install git+https://github.com/estin/python-coveralls.git

# prepare .coveralls.yml config
echo "service_name: drone.io" > .coveralls.yml
echo "repo_token: $COVERALLS_REPO_TOKEN" >> .coveralls.yml

# post coverage report to coveralls.io
coveralls
