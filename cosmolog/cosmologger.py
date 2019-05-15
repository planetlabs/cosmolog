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

import collections
import json
import logging
import logging.config
import re
import socket
import string

from datetime import datetime
from dateutil.parser import parse as dateparse
from pytz import utc
from past.builtins import long, unicode, basestring


FATAL = 100
ERROR = 200
WARN = 300
INFO = 400
DEBUG = 500
TRACE = 600

LEVELS = {
    FATAL: 'FATAL',
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
    TRACE: 'TRACE',
    'FATAL': FATAL,
    'ERROR': ERROR,
    'WARN': WARN,
    'INFO': INFO,
    'DEBUG': DEBUG,
    'TRACE': TRACE,
}

CRESET = '\033[0m'
CRED = '\033[31m'
CGREEN = '\033[32m'
CYELLOW = '\033[33m'
CBLUE = '\033[34m'
BRED = '\033[41m'
COLOR_CODES = [CRESET, CRED, CGREEN, CYELLOW, CBLUE, BRED]


def _set_color(color):
    def c(text):
        return '{}{}{}'.format(color, text, CRESET)
    return c


red = _set_color(CRED)
bg_red = _set_color(BRED)
green = _set_color(CGREEN)
yellow = _set_color(CYELLOW)
blue = _set_color(CBLUE)


LEVEL_COLORS = {
    FATAL: bg_red('FATAL'),
    ERROR: bg_red('ERROR'),
    WARN: yellow('WARN'),
    INFO: green('INFO'),
    DEBUG: 'DEBUG',
    TRACE: 'TRACE',
}

DEFAULT_SCHEMA_VERSION = 0


class CosmologgerException(Exception):
    pass


class CosmologEvent(dict):

    def __init__(self, version=DEFAULT_SCHEMA_VERSION, stream_name=None,
                 origin=None, timestamp=None, format=None, level=None,
                 payload={}):
        origin = origin or self.get_default_origin()
        self._validate_origin(origin)
        self._validate_stream_name(stream_name)
        self._validate_payload(payload)
        timestamp = self._coerce_timestamp(timestamp)
        super(CosmologEvent, self).__init__(version=version,
                                            stream_name=stream_name,
                                            origin=origin,
                                            timestamp=timestamp,
                                            format=format,
                                            level=level,
                                            payload=payload)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    @classmethod
    def from_json(cls, j):
        try:
            d = json.loads(j)
        except ValueError as e:
            raise CosmologgerException(unicode(e))
        return cls.from_dict(d)

    @property
    def json(self):
        return json.dumps(self)

    @classmethod
    def get_default_origin(self):
        return socket.getfqdn()

    _default_datefmt = '%Y-%m-%dT%H:%M:%S.%fZ'

    def _coerce_timestamp(self, t):
        if isinstance(t, datetime):
            pass
        elif t == 'now':
            t = datetime.now(utc)
        elif isinstance(t, basestring):
            try:
                t = datetime.utcfromtimestamp(float(t))
            except ValueError:
                t = dateparse(t)
        elif isinstance(t, (int, float, long)):
            t = datetime.utcfromtimestamp(t)
        else:
            msg = 'Unable to parse {} ({}) to UTC time'.format(t, type(t))
            raise CosmologgerException(msg)

        t = t.replace(tzinfo=utc)
        return t.strftime(self._default_datefmt)

    @classmethod
    def _validate_origin(cls, origin):
        if len(origin) > 255:
            msg = ('Invalid origin: "{}". '
                   'Origin length cannot exceed 255 characters'
                   ).format(origin)
            raise CosmologgerException('ValidationError', msg)
        pattern = re.compile("(?!-)[A-Z0-9_-]{1,63}(?<!-)$", re.IGNORECASE)
        for part in origin.split('.'):
            if not pattern.match(part):
                msg = 'Origin must be a fully qualified domain name'
                raise CosmologgerException('ValidationError', msg)

    @classmethod
    def _validate_stream_name(cls, stream_name):
        matches = re.match(r'[a-zA-Z0-9][a-zA-Z0-9._-]+', stream_name)
        if matches is None or matches.group(0) != stream_name:
            msg = ('Invalid stream_name: "{}". '
                   'Stream name can contain alphanumeric characters '
                   'and "_", "-", "."').format(stream_name)
            raise CosmologgerException('ValidationError', msg)

    @classmethod
    def _validate_payload(cls, payload):
        if not isinstance(payload, collections.Mapping):
            msg = ('Invalid payload: "{}". '
                   'Payload must be a dictionary, not type {}'
                   ).format(payload, type(payload))
            raise CosmologgerException(msg)
        return {k: v for k, v in payload.items()
                if cls._validate_payload_key(k) and
                cls._validate_payload_value(v)}

    @classmethod
    def _validate_payload_key(cls, key):
        m = re.match(r'[a-zA-Z0-9][a-zA-Z0-9_\-\.]+', key)
        if m is None or m.group(0) != key:
            msg = ('Invalid payload key: "{}". '
                   'Payload keys can contain alphanumeric characters, '
                   'underscores, dashes, and dots.'.format(key))
            raise CosmologgerException('ValidationError', msg)
        return True

    _primitive_types = (bool, int, float, long, str, unicode, type(None))

    @classmethod
    def _validate_payload_value(cls, value):
        if type(value) not in cls._primitive_types:
            msg = ('Invalid payload value: "{}". '
                   'Payload values can be any scalar type. No lists, dicts or '
                   'other complex types. Not type {}'
                   ).format(value, type(value))
            raise CosmologgerException('ValidationError', msg)
        return True


class Cosmologger(object):

    def __init__(self, stream_name):
        # fail fast for invalid stream name
        CosmologEvent._validate_stream_name(stream_name)
        self.logger = logging.Logger.manager.getLogger(stream_name)

    _level_mappings = {
        logging.FATAL: FATAL,
        logging.CRITICAL: FATAL,
        logging.ERROR: ERROR,
        logging.WARN: WARN,
        logging.WARNING: WARN,
        logging.INFO: INFO,
        logging.DEBUG: DEBUG
    }

    @classmethod
    def to_cosmolog_level(cls, lvl):
        return cls._level_mappings.get(lvl)

    def fatal(self, *args, **kwargs):
        return self.log(logging.FATAL, *args, **kwargs)

    def critical(self, *args, **kwargs):
        return self.fatal(*args, **kwargs)

    def exception(self, *args, **kwargs):
        if 'exc_info' not in kwargs:
            kwargs['exc_info'] = 1
        return self.error(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self.log(logging.ERROR, *args, **kwargs)

    def warn(self, *args, **kwargs):
        return self.log(logging.WARN, *args, **kwargs)

    def warning(self, *args, **kwargs):
        return self.warn(*args, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(logging.INFO, *args, **kwargs)

    def debug(self, *args, **kwargs):
        return self.log(logging.DEBUG, *args, **kwargs)

    def log(self, lvl, *args, **kwargs):
        payload = kwargs.copy()
        payload.pop('extra', None)
        payload.pop('exc_info', None)
        extras = kwargs.get('extra', {})
        extras.update(dict(payload=payload))
        exc_info = kwargs.pop('exc_info', 0)

        if not args:
            return self.logger.log(
                lvl, None, exc_info=exc_info, extra=extras)
        return self.logger.log(
            lvl, *args, exc_info=exc_info, extra=extras)


class CosmologgerFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        self._origin = kwargs.pop('origin')
        self._version = kwargs.pop('version')
        logging.Formatter.__init__(self, *args, **kwargs)

    def _prepare_payload(self, record):
        pld = record.__dict__.get('payload', {})
        if record.exc_info:
            pld['exc_text'] = record.exc_text
        return pld

    def _prepare_timestamp(self, record):
        if hasattr(record, 'created'):
            return record.created
        return datetime.now(utc)

    def _prepare_format(self, record):
        if record.msg is None:
            return None
        if record.exc_info and '{exc_text}' not in str(record.msg):
            return record.getMessage() + '\n{exc_text}'
        return record.getMessage()

    def _prepare_log_event(self, record):
        return CosmologEvent.from_dict({
            'stream_name': record.name,
            'origin': self._origin or CosmologEvent.get_default_origin(),
            'version': self._version,
            'timestamp': self._prepare_timestamp(record),
            'format': self._prepare_format(record),
            'level': Cosmologger.to_cosmolog_level(record.levelno),
            'payload': self._prepare_payload(record)
        })

    def event_format(self, event):
        return event.json

    def format(self, record):
        super(CosmologgerFormatter, self).format(record)
        e = self._prepare_log_event(record)
        return self.event_format(e)


_default_fmt = '{timestamp} {origin} {stream_name}: [{level}] {payload}'
_default_datefmt = {
    True: '{}%b %d {}%H:%M:%S{}'.format(CRED, CGREEN, CRESET),
    False: '%b %d %H:%M:%S'
}


class _PayloadFormatter(string.Formatter):
    # https://stackoverflow.com/questions/7934620/python-dots-in-the-name-of-variable-in-a-format-string  # noqa
    def get_field(self, field_name, args, kwargs):
        return (self.get_value(field_name, args, kwargs), field_name)


class CosmologgerHumanFormatter(CosmologgerFormatter):

    def __init__(self, *args, **kwargs):
        self._color = kwargs.pop('color', False)
        self._format = kwargs.pop('format', _default_fmt)
        self._datefmt = kwargs.pop('datefmt', None)
        if self._datefmt is None:
            self._datefmt = _default_datefmt[self._color]
        CosmologgerFormatter.__init__(self, *args, **kwargs)

    def _format_timestamp(self, timestamp):
        timestamp = dateparse(timestamp, ignoretz=True).replace(tzinfo=utc)
        return timestamp.strftime(self._datefmt)

    def event_format(self, e):
        timestamp = self._format_timestamp(e['timestamp'])
        if self._color:
            origin = blue(e['origin'])
            stream_name = yellow(e['stream_name'])
            level = LEVEL_COLORS.get(e['level'])
        else:
            origin = e['origin']
            stream_name = e['stream_name']
            level = LEVELS[e['level']]

        fmt, payload = e['format'], e['payload']
        if fmt:
            try:
                payload = _PayloadFormatter().vformat(fmt, [], payload)
            except KeyError:
                payload = 'BadLogFormat("{format}") {payload}'.format(**e)
        else:
            payload = ', '.join('{}: {}'.format(k, v)
                                for k, v in payload.items())

        output = self._format.format(
            timestamp=timestamp,
            origin=origin,
            stream_name=stream_name,
            level=level,
            payload=payload)

        return output


def setup_logging(level='INFO', origin=None, custom_config=None):
    origin = origin or CosmologEvent.get_default_origin()

    # fail fast for bad origin.
    CosmologEvent._validate_origin(origin)

    DEFAULT_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'cosmolog': {
                '()': CosmologgerFormatter,
                'origin': origin,
                'version': DEFAULT_SCHEMA_VERSION,
            },
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'cosmolog'
            },
        },
        'root': {
            'handlers': ['default'],
            'level': level,
        }
    }
    c = custom_config or DEFAULT_CONFIG
    logging.config.dictConfig(c)
