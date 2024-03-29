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
import sys

from .cosmologger import CosmologEvent
from .cosmologger import Cosmologger
from .cosmologger import CosmologgerException
from .cosmologger import CosmologgerFormatter
from .cosmologger import CosmologgerHumanFormatter
from .cosmologger import LEVELS
from .cosmologger import setup_logging

__all__ = ['Cosmologger', 'CosmologgerFormatter',
           'CosmologgerHumanFormatter',
           'CosmologgerException', 'CosmologEvent',
           'LEVELS', 'setup_logging']


if sys.version_info >= (3, 8):
    from importlib.metadata import version
else:
    from importlib_metadata import version

__version__ = version
