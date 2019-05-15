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

import pytest
import random
import string

from click.testing import CliRunner

from cosmolog.bin.cli import cli


@pytest.fixture
def random_name(length=6):
    return ''.join(random.choice(string.lowercase) for i in range(length))


@pytest.fixture
def cli_runner():
    def runner(command):
        runner = CliRunner()
        result = runner.invoke(cli, command.split(' '))
        return result.output
    return runner
