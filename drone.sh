#!/bin/sh

if ! type python3.5 > /dev/null; then
    echo "python3.5 install..."
    sudo add-apt-repository ppa:fkrull/deadsnakes -y > /dev/null 2>&1
    sudo apt-get -qq update > /dev/null 2>&1
    sudo apt-get -qq install python3.5-dev -y > /dev/null 2>&1
    echo "done"
fi

# install phantomjs
if ! type phantomjs > /dev/null; then
    echo "phantomjs install..."
    curl -sL https://deb.nodesource.com/setup | sudo bash - > /dev/null 2>&1
    sudo apt-get -qq install -y nodejs npm -y > /dev/null 2>&1
    sudo npm -g install phantomjs > /dev/null 2>&1
    echo "done"
fi
echo nodejs `node -v`
echo npm `npm -v`
echo phantomjs `phantomjs -v`

pip install coverage tox
tox -e py27,py35,docs,py27examples,py35examples,qa
coverage combine

if [ ! -z "$CODECOV_REPO_TOKEN" ]; then
    pip install codecov
    codecov --token=$CODECOV_REPO_TOKEN > /dev/null 2>&1
fi
