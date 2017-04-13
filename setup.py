# -*- coding: utf-8 -*-
import os
import sys
from setuptools import setup


here = os.path.dirname(os.path.abspath(__file__))

about = {}
with open(os.path.join(here, "pomp", "__init__.py")) as f:
    exec(f.read(), about)

install_requires = []
if sys.version_info < (3, 2):
    install_requires.append('futures')

packages = [
    'pomp', 'pomp.core', 'pomp.contrib',
]
if sys.version_info > (3, 3):
    packages.append('pomp.contrib.asynciotools')


setup(
    name='pomp',
    version=about['__version__'],
    url='http://bitbucket.org/estin/pomp',
    license='BSD',
    author='Evgeniy Tatarkin',
    author_email='tatarkin.evg@gmail.com',
    description='Screen scraping and web crawling framework',
    long_description=open(os.path.join(here, 'README.rst')).read(),
    packages=packages,
    zip_safe=False,
    platforms='any',
    tests_require=['nose >= 1.0', ],
    test_suite='nose.collector',
    install_requires=install_requires,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
