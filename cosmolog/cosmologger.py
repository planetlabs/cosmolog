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

from datetime import datetime
from dateutil.parser import parse as dateparse
from pytz import utc


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
            raise CosmologgerException(e.message)
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
            msg = 'Origin length cannot exceed 255 characters'
            raise CosmologgerException('ValidationError', msg)
        pattern = re.compile("(?!-)[A-Z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
        for part in origin.split('.'):
            if not pattern.match(part):
                msg = 'Origin must be a fully qualified domain name'
                raise CosmologgerException('ValidationError', msg)

    @classmethod
    def _validate_stream_name(cls, stream_name):
        matches = re.match(r'[a-z0-9][a-z0-9._-]+', stream_name)
        if matches is None or matches.group(0) != stream_name:
            msg = ('Stream name can contain lowercase alphanumeric characters,'
                   ' and "_", "-", "."')
            raise CosmologgerException('ValidationError', msg)

    @classmethod
    def _validate_payload(cls, payload):
        if not isinstance(payload, collections.Mapping):
            msg = 'Payload must be a dictionary, not {}'.format(payload)
            raise CosmologgerException(msg)
        return {k: v for k, v in payload.iteritems()
                if cls._validate_payload_key(k) and
                cls._validate_payload_value(v)}

    @classmethod
    def _validate_payload_key(cls, key):
        m = re.match(r'[a-zA-Z0-9][a-zA-Z0-9_]+', key)
        if m is None or m.group(0) != key:
            msg = ('Payload keys can contain alphanumeric characters and '
                   'underscores.')
            raise CosmologgerException('ValidationError', msg)
        return True

    _primitive_types = (bool, int, float, long, str, unicode, type(None))

    @classmethod
    def _validate_payload_value(cls, value):
        if type(value) not in cls._primitive_types:
            msg = ('Payload values can be any scalar type. No lists, dicts or '
                   'other complex types. Not {}'.format(type(value)))
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
        if not args:
            return self.logger.log(lvl, None, extra=dict(payload=kwargs))
        return self.logger.log(lvl, *args, extra=dict(payload=kwargs))


class CosmologgerFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        self._origin = kwargs.pop('origin')
        self._version = kwargs.pop('version')
        logging.Formatter.__init__(self, *args, **kwargs)

    def _prepare_exception(self, record):
        if not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        return record.exc_text

    def _prepare_payload(self, record):
        return record.__dict__.get('payload', {})

    def _prepare_timestamp(self, record):
        if hasattr(record, 'created'):
            return record.created
        return datetime.now(utc)

    def _prepare_format(self, record):
        if record.exc_info:
            return self._prepare_exception(record)
        if record.msg is None:
            return None
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

    def format(self, record):
        e = self._prepare_log_event(record)
        return e.json


def _update_config_dict(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = _update_config_dict(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def setup_logging(level='INFO', origin=None, custom_config={}):
    origin = origin or CosmologEvent.get_default_origin()

    # fail fast for bad origin.
    CosmologEvent._validate_origin(origin)

    LOGGING_CONFIG = {
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
    c = _update_config_dict(LOGGING_CONFIG, custom_config)
    logging.config.dictConfig(c)
