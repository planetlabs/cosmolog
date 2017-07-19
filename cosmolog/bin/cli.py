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

import click
import re

from dateutil.parser import parse as dateparse
from pytz import utc

from cosmolog import LEVELS, CosmologEvent, CosmologgerException


@click.group(context_settings={'help_option_names': ['-h', '-?', '--help']})
@click.version_option(version='0.1')
def cli():
    pass


def iso8601_to_datetime(iso8601):
    return dateparse(iso8601, ignoretz=True).replace(tzinfo=utc)


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


def _format_payload(fmt, **kwargs):
    output = ''
    if fmt:
        try:
            output += fmt.format(**kwargs)
        except KeyError:
            output += 'BadLogFormat {}'.format(fmt)
    else:
        for k, v in kwargs.iteritems():
            output += '{}: {}, '.format(k, v)
    return output


_default_datefmt = '{}%b %d {}%H:%M:%S{}'.format(CRED, CGREEN, CRESET)


def _format_timestamp(timestamp, datefmt):
    timestamp = iso8601_to_datetime(timestamp)
    if datefmt:
        return red(timestamp.strftime(datefmt))
    return timestamp.strftime(_default_datefmt)


LEVEL_COLORS = {
    LEVELS['FATAL']: bg_red(LEVELS[LEVELS['FATAL']]),
    LEVELS['ERROR']: bg_red(LEVELS[LEVELS['ERROR']]),
    LEVELS['WARN']: yellow(LEVELS[LEVELS['WARN']]),
    LEVELS['INFO']: green(LEVELS[LEVELS['INFO']]),
    LEVELS['DEBUG']: LEVELS[LEVELS['DEBUG']],
    LEVELS['TRACE']: LEVELS[LEVELS['TRACE']],
}


def _format_level(lvl):
    return LEVEL_COLORS.get(lvl)


def _clear_colors(line):
    for c in COLOR_CODES:
        line = re.sub(re.escape(c), '', line)
    return line


_default_fmt = '{timestamp} {origin} {stream_name}: [{level}] {payload}'


def process(line, verbosity, datefmt, no_color):
    e = CosmologEvent.from_json(line)

    if verbosity < e['level']:
        return

    timestamp = _format_timestamp(e['timestamp'], datefmt)
    origin = blue(e['origin'])
    stream_name = yellow(e['stream_name'])
    level = _format_level(e['level'])
    payload = _format_payload(e['format'], **e['payload'])

    output = _default_fmt.format(
        timestamp=timestamp,
        origin=origin,
        stream_name=stream_name,
        level=level,
        payload=payload)

    if no_color:
        output = _clear_colors(output)

    click.echo(output)


def _format_exception(line, e, no_color):
    msg = 'Failed to interpret \'{}\': {}'
    msg = red(msg.format(line, e.message))
    if no_color:
        msg = _clear_colors(msg)
    return msg


@cli.command()
@click.option('-v', '--verbosity',
              default=600,
              help='Adjust verbosity')
@click.option('-d', '--datefmt',
              default=None,
              help='Format string for dates')
@click.option('--no-color', is_flag=True, default=False,
              help='Do not print with colors')
def human(verbosity, datefmt, no_color):
    '''Use this command to format machine-readable logs for humans.

    `human` reads stdin and writes formatted lines to stdout.

    Verbosity Levels:
    FATAL=100 | ERROR=200 | WARN=300 | INFO=400 | DEBUG=500 |
    TRACE=600 (DEFAULT)

    USAGE:

    tail -f myapp.log | human

    cat myapp.log | human -v 400 --datefmt "%Y-%m-%d %H:%M:%S"

    '''
    with click.get_text_stream('stdin') as stdin:
        for line in stdin:
            line = line.strip()
            try:
                process(line, verbosity, datefmt, no_color)
            except CosmologgerException as e:
                msg = _format_exception(line, e, no_color)
                click.echo(msg, err=True)
