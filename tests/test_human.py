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

from click.testing import CliRunner

from cosmolog.bin.cli import human


@pytest.fixture
def cli_tester():
    def tester(args, stdin):
        runner = CliRunner()
        return runner.invoke(human, args, catch_exceptions=False, input=stdin)
    return tester


def test_one_event(cli_tester):
    line = (
        '{"version": 0, "stream_name": "telemetry", '
        '"origin": "foobar.example.com", '
        '"timestamp": "2016-09-02T16:34:12.019105Z", '
        '"format": "s={sensor}", "level": 400,'
        '"payload": {"sensor": 36.7} }')
    expected = 'Sep 02 16:34:12 foobar.example.com telemetry: [INFO] s=36.7\n'
    r = cli_tester([], line)
    assert r.exit_code == 0
    assert r.output == expected


def test_bad_json(cli_tester):
    line = '*$'
    expected = (
        "Failed to interpret '*$': No JSON object could be decoded\n",
        "Failed to interpret '*$': Expecting value: line 1 column 1 (char 0)\n"
    )
    r = cli_tester([], line)
    assert r.exit_code == 0
    assert r.output in expected


def test_payload_keys_with_dots(cli_tester):
    line = (
        '{"version": 0, "stream_name": "distances", '
        '"origin": "earth", '
        '"timestamp": "2016-09-02T16:34:12.019105Z", '
        '"format": "distance to sun is {sun.distance}", "level": 400,'
        '"payload": {"sun.distance": 9} }')
    expected = 'Sep 02 16:34:12 earth distances: [INFO] distance to sun is 9\n'
    r = cli_tester([], line)
    assert r.exit_code == 0
    assert r.output == expected


def test_payload_keys_with_dashes(cli_tester):
    line = (
        '{"version": 0, "stream_name": "distances", '
        '"origin": "earth", '
        '"timestamp": "2016-09-02T16:34:12.019105Z", '
        '"format": "distance to sun is {sun-distance}", "level": 400,'
        '"payload": {"sun-distance": 9} }')
    expected = 'Sep 02 16:34:12 earth distances: [INFO] distance to sun is 9\n'
    r = cli_tester([], line)
    assert r.exit_code == 0
    assert r.output == expected
