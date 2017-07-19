#!/usr/bin/env python

# Copyright 2017 Planet Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import os
import versioneer

from setuptools import distutils, find_packages, setup


def get_version():
    if os.path.exists('PKG-INFO'):
        metadata = distutils.dist.DistributionMetadata('PKG-INFO')
        return metadata.version
    else:
        return versioneer.get_version()


setup(name='cosmolog',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='cosmolog: structured python logger',
      url='https://github.com/planetlabs/cosmolog',
      author='Isil Demir',
      author_email='isil@planet.com',
      packages=find_packages(exclude=['tests']),
      install_requires=[
          'click>=6.3',
          'pytz>=2015.7',
          'python-dateutil>=2.4.2',
      ],
      extras_require={
          'test': [
              'pytest>=3.0.2',
              'flake8==3.2.0'
          ]
      },
      entry_points='''
      [console_scripts]
      human=cosmolog.bin.cli:human
      ''')
