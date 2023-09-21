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
import sys

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from freezegun import freeze_time
from builtins import str as newstr

from cosmolog import (setup_logging,
                      Cosmologger,
                      CosmologgerException,
                      CosmologgerFormatter,
                      CosmologgerHumanFormatter)


@pytest.fixture
def cosmolog_setup():
    '''Sets up cosmolog and returns the log file as a StringIO object'''
    def prepare_cosmolog_setup(level='INFO', origin=None, formatter='cosmolog'):  # noqa: E501
        log_stream = StringIO()
        origin = origin or 'jupiter.planets.com'
        custom_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'cosmolog': {
                    '()': CosmologgerFormatter,
                    'origin': origin,
                    'version': 0,
                },
                'human': {
                    '()': CosmologgerHumanFormatter,
                    'origin': origin,
                    'version': 0,
                }
            },
            'handlers': {
                'h': {
                    'class': 'logging.StreamHandler',
                    'formatter': formatter,
                    'stream': log_stream,
                },
            },
            'root': {
                'handlers': ['h'],
                'level': level,
            }
        }
        setup_logging(level, origin, custom_config=custom_config)
        return log_stream
    return prepare_cosmolog_setup


@pytest.fixture
def cosmolog():
    def make_cosmolog(stream_name='star_stuff'):
        return Cosmologger(stream_name)
    return make_cosmolog


def _log_output(stream):
    logline = stream.getvalue().split('\n').pop(0)
    return json.loads(logline)


def test_stream_is_validated(cosmolog):
    with pytest.raises(CosmologgerException) as e:
        cosmolog(stream_name='Bad:Stream#Name+1.0')
    assert e.value.args[0] == 'ValidationError'


def test_origin_is_validated(cosmolog, cosmolog_setup):
    with pytest.raises(CosmologgerException) as e:
        cosmolog_setup(origin='not a fully qualified domain name')
    assert e.value.args[0] == 'ValidationError'


def test_required_fields(cosmolog, cosmolog_setup):
    logfile = cosmolog_setup()
    logger = cosmolog()
    logger.info('the pale blue dot')
    out = _log_output(logfile)
    assert sorted(out.keys()) == sorted(['stream_name', 'origin', 'level',
                                         'timestamp', 'version', 'payload',
                                         'format'])


def test_log_message(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup()
    logger = cosmolog()
    logger.info('the pale blue dot')
    out = _log_output(logstream)
    assert out['format'] == 'the pale blue dot'


@freeze_time("1970-04-13T03:07:53Z")
def test_human_log_message(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    logger.error('Something bad happened')
    logline = logstream.getvalue().split('\n').pop(0)
    assert logline == 'Apr 13 03:07:53 jupiter.planets.com star_stuff: [ERROR] Something bad happened'  # noqa: E501


def test_payload(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup()
    logger = cosmolog()
    logger.info(ganymede_g=1.428, europa_g=1.315)
    out = _log_output(logstream)
    assert out['format'] is None
    assert out['payload']['ganymede_g'] == 1.428
    assert out['payload']['europa_g'] == 1.315


@freeze_time("1970-04-13T03:07:53Z")
def test_human_payload(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    logger.error(component='oxygen tank')
    logline = logstream.getvalue().split('\n').pop(0)
    assert logline == 'Apr 13 03:07:53 jupiter.planets.com star_stuff: [ERROR] component: oxygen tank'  # noqa: E501


def test_format_and_payload(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup()
    logger = cosmolog()
    msg = 'the observable universe consists of {n_galaxy} galaxies'
    logger.info(msg, n_galaxy='2 trillion')
    out = _log_output(logstream)
    assert out['format'] == msg
    assert out['payload']['n_galaxy'] == '2 trillion'


@freeze_time("1970-04-13T03:07:53Z")
def test_human_format_and_payload(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    msg = 'the {component} has exploded'
    logger.error(msg, component='oxygen tank')
    logline = logstream.getvalue().split('\n').pop(0)
    assert logline == 'Apr 13 03:07:53 jupiter.planets.com star_stuff: [ERROR] the oxygen tank has exploded'  # noqa: E501


@freeze_time("1970-04-13T03:07:53Z")
def test_human_format_and_payload_with_newstr(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    msg = 'the {component} has exploded'
    logger.error(msg, component=newstr('oxygen tank'))
    logline = logstream.getvalue().split('\n').pop(0)
    assert logline == 'Apr 13 03:07:53 jupiter.planets.com star_stuff: [ERROR] the oxygen tank has exploded'  # noqa: E501


def test_payload_is_validated(cosmolog, cosmolog_setup, capsys):
    cosmolog_setup()
    logger = cosmolog()
    logger.info('black hole properties: {properties}',
                properties={'supermassive': True, 'location': 'milky way'})
    out, err = capsys.readouterr()
    assert 'CosmologgerException' in err
    assert 'ValidationError' in err


def test_newstr_is_accepted(cosmolog, cosmolog_setup, capsys):
    cosmolog_setup()
    logger = cosmolog()
    logger.info('someone is from the future: {futstr}',
                futstr=newstr("hi from the future"))
    out, err = capsys.readouterr()
    assert not err


@freeze_time("1970-04-13T03:07:53Z")
def test_human_format_invalid(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    msg = 'the {blarg} has exploded'
    logger.error(msg, component='oxygen tank')
    logline = logstream.getvalue().split('\n').pop(0)
    assert logline == 'Apr 13 03:07:53 jupiter.planets.com star_stuff: [ERROR] BadLogFormat("the {blarg} has exploded") {\'component\': \'oxygen tank\'}'  # noqa: E501


def test_json_not_bad(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    msg = 'sometimes somebody logs a {"json": "data"} from space. That is okay'
    logger.info(msg)
    logline = logstream.getvalue().split('\n').pop(0)
    assert 'BadLogFormat' not in logline


def test_dicts_not_bad(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup(formatter='human')
    logger = cosmolog()
    d = {
        "orbit": "sso",
        "camera": "nadir",
        "radio": "zenith"
    }
    msg = f'sometimes somebody logs a dict {d}'
    logger.info(msg)
    logline = logstream.getvalue().split('\n').pop(0)
    assert 'BadLogFormat' not in logline


def test_can_log_all_levels(cosmolog, cosmolog_setup):
    logstream = cosmolog_setup('DEBUG')
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
        out = _log_output(logstream)
        out['level'] == l[1]


def test_python_logging(cosmolog, cosmolog_setup):
    cosmolog_setup()
    universal_logger = cosmolog(stream_name='space_time')
    logging_logger = logging.getLogger('space_time')
    assert universal_logger.logger == logging_logger


def test_python_logging_is_formatted_with_cosmolog(cosmolog_setup):
    logstream = cosmolog_setup()
    logger = logging.getLogger('cosmos')
    logger.setLevel(logging.DEBUG)
    logger.debug('the cosmos is vast')
    out = _log_output(logstream)
    assert out['format'] == 'the cosmos is vast'
    assert out['stream_name'] == 'cosmos'
    assert out['payload'] == {}


def test_extra_reserved(cosmolog, cosmolog_setup):
    '''ensure `extra` is reserved and not part of cosmolog payload'''
    logstream = cosmolog_setup()
    logger = logging.getLogger('cosmos')
    logger.info('captains log', extra={'gravitational_wave': True})
    out = _log_output(logstream)
    assert out['payload'] == {}


def test_exc_info(cosmolog, cosmolog_setup):
    '''ensure `exc_info` can be used to pass along the stack trace'''
    logstream = cosmolog_setup()
    logger = logging.getLogger('cosmos')

    def fail(fmt):
        1 / 0
    exc = None

    try:
        fail('Extra braces for extra fail {}')
    except Exception:
        exc = sys.exc_info()

    typ, val, tb = exc
    tb = traceback.format_exc()
    print((typ, val, tb))
    logger.error(val, exc_info=1)
    out = _log_output(logstream)
    assert out['format'] == str(val) + '\n{exc_text}'
    assert out['payload'] == {'exc_text': tb.strip()}


@freeze_time("1970-04-13T03:07:53Z")
def test_exc_info_human(cosmolog, cosmolog_setup):
    '''ensure `exc_info` can be used to pass along the stack trace'''
    logstream = cosmolog_setup(formatter='human')
    logger = logging.getLogger('apollo13')

    def fail(fmt):
        1 / 0

    try:
        fail('Extra braces for extra fail {}')
    except Exception:
        pass

    tb = traceback.format_exc()

    logger.error('Something bad happened', exc_info=1)
    out = logstream.getvalue()
    assert out == 'Apr 13 03:07:53 jupiter.planets.com apollo13: [ERROR] Something bad happened\n{}'.format(tb)  # noqa: E501


@freeze_time("1970-04-13T03:07:53Z")
def test_exception_human(cosmolog, cosmolog_setup):
    '''ensure `exception` can be used to pass along the stack trace'''
    logstream = cosmolog_setup(formatter='human')
    logger = logging.getLogger('apollo13')

    def fail(fmt):
        1 / 0

    try:
        fail('Extra braces for extra fail {}')
    except Exception:
        tb = traceback.format_exc()
        logger.exception('Something bad happened')

    out = logstream.getvalue()
    assert out == 'Apr 13 03:07:53 jupiter.planets.com apollo13: [ERROR] Something bad happened\n{}'.format(tb)  # noqa: E501


def test_payload_with_dots(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()
    logger.info(**{'jupiter.ganymede_g': 1.428, 'jupiter.europa_g': 1.315})
    out = _log_output(logpath)
    assert out['format'] is None
    assert out['payload']['jupiter.ganymede_g'] == 1.428
    assert out['payload']['jupiter.europa_g'] == 1.315


def test_payload_with_dashes(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()
    logger.info(**{'jupiter-ganymede_g': 1.428, 'jupiter-europa_g': 1.315})
    out = _log_output(logpath)
    assert out['format'] is None
    assert out['payload']['jupiter-ganymede_g'] == 1.428
    assert out['payload']['jupiter-europa_g'] == 1.315


def test_user_specified_exc_info(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()

    class DeorbitException(Exception):
        pass

    def fly():
        raise DeorbitException('Panic. Deorbiting.')
    try:
        fly()
    except DeorbitException:
        logger.exception('Problem flying.', exc_info=True)

    out = _log_output(logpath)
    assert 'exc_text' in out['payload']
    assert out['payload']['exc_text'] is not None


def test_user_specified_exc_info_false(cosmolog, cosmolog_setup):
    logpath = cosmolog_setup()
    logger = cosmolog()

    class DeorbitException(Exception):
        pass

    def fly():
        raise DeorbitException('Panic. Deorbiting.')
    try:
        fly()
    except DeorbitException:
        logger.exception('Problem flying.', exc_info=False)

    out = _log_output(logpath)
    assert 'exc_text' not in out['payload']
