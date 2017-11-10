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

import json
import logging
import logging.config
import pytest
import traceback

from cosmolog import (setup_logging,
                      Cosmologger,
                      CosmologgerException,
                      CosmologgerFormatter)


@pytest.fixture
def log_file(tmpdir, random_name):
    def make_log_file():
        return tmpdir.mkdir('tmp').join(random_name)
    return make_log_file


@pytest.fixture
def cosmolog_setup(log_file):
    def prepare_cosmolog_setup(level='INFO', origin=None, custom_config={}):
        f = log_file()
        origin = origin or 'jupiter.planets.com'
        if custom_config == {}:
            custom_config = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'cosmolog': {
                        '()': CosmologgerFormatter,
                        'origin': origin,
                        'version': 0,
                    },
                },
                'handlers': {
                    'f': {
                        'class': 'logging.FileHandler',
                        'formatter': 'cosmolog',
                        'filename': f.strpath,
                    },
                },
                'root': {
                    'handlers': ['f'],
                    'level': level,
                }
            }
        setup_logging(level, origin, custom_config=custom_config)
        return f.strpath
    return prepare_cosmolog_setup


@pytest.fixture
def cosmolog():
    def make_cosmolog(stream_name='star_stuff'):
        return Cosmologger(stream_name)
    return make_cosmolog


def _log_output(filepath):
    with open(filepath) as f:
        data = f.readline().strip()
    return json.loads(data)


def test_stream_is_validated(cosmolog):
    with pytest.raises(CosmologgerException) as e:
        cosmolog(stream_name='Bad:Stream#Name+1.0')
    assert e.value[0] == 'ValidationError'


def test_origin_is_validated(cosmolog, cosmolog_setup):
    with pytest.raises(CosmologgerException) as e:
        cosmolog_setup(origin='not a fully qualified domain name')
    assert e.value[0] == 'ValidationError'


def test_required_fields(cosmolog, cosmolog_setup):
    logfile = cosmolog_setup()
    logger = cosmolog()
    logger.info('the pale blue dot')
    out = _log_output(logfile)
    assert sorted(out.keys()) == sorted(['stream_name', 'origin', 'level',
                                         'timestamp', 'version', 'payload',
                                         'format'])


def test_log_message(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()
    logger.info('the pale blue dot')
    out = _log_output(logpath)
    assert out['format'] == 'the pale blue dot'


def test_payload(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()
    logger.info(ganymede_g=1.428, europa_g=1.315)
    out = _log_output(logpath)
    assert out['format'] is None
    assert out['payload']['ganymede_g'] == 1.428
    assert out['payload']['europa_g'] == 1.315


def test_format_and_payload(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()
    msg = 'the observable universe consists of {n_galaxy} galaxies'
    logger.info(msg, n_galaxy='2 trillion')
    out = _log_output(logpath)
    assert out['format'] == msg
    assert out['payload']['n_galaxy'] == '2 trillion'


def test_payload_is_validated(cosmolog, cosmolog_setup, capsys):
    cosmolog_setup()
    logger = cosmolog()
    logger.info('black hole properties: {properties}',
                properties={'supermassive': True, 'location': 'milky way'})
    out, err = capsys.readouterr()
    assert 'CosmologgerException' in err
    assert 'ValidationError' in err


def test_can_log_all_levels(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup('DEBUG')
    logger = cosmolog()
    levels = [(getattr(logger, 'debug'), 500),
              (getattr(logger, 'info'), 400),
              (getattr(logger, 'warn'), 300),
              (getattr(logger, 'warning'), 300),
              (getattr(logger, 'error'), 200),
              (getattr(logger, 'exception'), 200),
              (getattr(logger, 'fatal'), 100)]
    for l in levels:
        l[0]('earth')
        out = _log_output(logpath)
        out['level'] == l[1]


def test_python_logging(cosmolog, cosmolog_setup):
    cosmolog_setup()
    universal_logger = cosmolog(stream_name='space_time')
    logging_logger = logging.getLogger('space_time')
    assert universal_logger.logger == logging_logger


def test_python_logging_is_formatted_with_cosmolog(cosmolog_setup):
    logpath = cosmolog_setup()
    logger = logging.getLogger('cosmos')
    logger.setLevel(logging.DEBUG)
    logger.debug('the cosmos is vast')
    out = _log_output(logpath)
    assert out['format'] == 'the cosmos is vast'
    assert out['stream_name'] == 'cosmos'
    assert out['payload'] == {}


def test_extra_reserved(cosmolog, cosmolog_setup):
    '''ensure `extra` is reserved and not part of cosmolog payload'''
    logpath = cosmolog_setup()
    logger = logging.getLogger('cosmos')
    logger.info('captains log', extra={'gravitational_wave': True})
    out = _log_output(logpath)
    assert out['payload'] == {}


def test_exc_info(cosmolog, cosmolog_setup):
    '''ensure `exc_info` can be used to pass along the stack trace'''
    logpath = cosmolog_setup()
    logger = logging.getLogger('cosmos')

    try:
        1 / 0
    except Exception as e:
        tb = traceback.format_exc()

    logger.info(e, exc_info=1)
    out = _log_output(logpath)
    assert out['format'] == tb.strip()
