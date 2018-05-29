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
import socket

from copy import deepcopy
from dateutil.parser import parse as dateparse

from cosmolog import CosmologEvent, CosmologgerException


@pytest.fixture
def basic_event():
    return {
        'version': 0,
        'stream_name': 'telemetry',
        'origin': 'foobar.example.com',
        'timestamp': '2016-09-02T16:34:12.019105Z',
        'format': 'once upon a time {sensor}',
        'level': 400,
        'payload': {
            'sensor': 36.7
        }
    }


def test_from_dict(basic_event):
    e = CosmologEvent.from_dict(basic_event)
    assert e == basic_event


def test_from_json(basic_event):
    j = '''{
        "version": 0,
        "stream_name": "telemetry",
        "origin": "foobar.example.com",
        "timestamp": "2016-09-02T16:34:12.019105Z",
        "format": "once upon a time {sensor}",
        "level": 400,
        "payload": {
            "sensor": 36.7
        }
    }'''
    e = CosmologEvent.from_json(j)
    assert e == basic_event


def test_invalid_json(basic_event):
    j = '{"not": "quite", "json"'
    with pytest.raises(CosmologgerException):
        CosmologEvent.from_json(j)


def test_default_origin(monkeypatch, basic_event):
    monkeypatch.setattr(socket, 'getfqdn', lambda: 'foobar.example.com')
    kwargs = deepcopy(basic_event)
    kwargs.pop('origin')
    e = CosmologEvent(**kwargs)
    assert e == basic_event


def test_invalid_origin(basic_event):
    basic_event['origin'] = 'spaces are not allowed'
    with pytest.raises(CosmologgerException):
        CosmologEvent.from_dict(basic_event)


def test_invalid_stream_name(basic_event):
    basic_event['stream_name'] = '%&^'
    with pytest.raises(CosmologgerException):
        CosmologEvent.from_dict(basic_event)


def test_case_insensitive_stream_name(basic_event):
    basic_event['stream_name'] = 'raven.FooClient'
    kwargs = deepcopy(basic_event)
    e = CosmologEvent(**kwargs)
    assert e == basic_event


def test_nested_payload_not_allowed(basic_event):
    basic_event['payload'] = {
        'turtle': {
            'turtle': {
                'turtle': {
                    'turtle': 'turtle'
                }
            }
        }
    }
    with pytest.raises(CosmologgerException):
        CosmologEvent.from_dict(basic_event)


def test_datetimes_allowed(basic_event):
    kwargs = deepcopy(basic_event)
    kwargs['timestamp'] = dateparse(basic_event['timestamp'])
    e = CosmologEvent(**kwargs)
    assert e == basic_event


def test_unix_timestamp_allowed(basic_event):
    kwargs = deepcopy(basic_event)
    kwargs['timestamp'] = 1472834052.019105
    e = CosmologEvent(**kwargs)
    assert e == basic_event


def test_unix_timestamp_string_allowed(basic_event):
    kwargs = deepcopy(basic_event)
    kwargs['timestamp'] = '1472834052.019105'
    e = CosmologEvent(**kwargs)
    assert e == basic_event


def test_null_values_in_payload(basic_event):
    kwargs = deepcopy(basic_event)
    kwargs['payload']['sensor'] = None
    e = CosmologEvent(**kwargs)
    assert e == kwargs


def test_payload_keys_with_dots(basic_event):
    basic_event['payload'] = {
        'sun.distance': 146e6,
        'moon.distance': 384400
    }
    e = CosmologEvent(**basic_event)
    assert e == basic_event


def test_payload_keys_with_dashes(basic_event):
    basic_event['payload'] = {
        'sun-distance': 146e6,
    }
    e = CosmologEvent(**basic_event)
    assert e == basic_event


def test_origin_with_underscores(basic_event):
    basic_event['origin'] = 'black_hole'
    e = CosmologEvent(**basic_event)
    assert e == basic_event
