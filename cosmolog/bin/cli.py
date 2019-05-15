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

from cosmolog import (
    CosmologEvent, CosmologgerException, CosmologgerHumanFormatter)


@click.group(context_settings={'help_option_names': ['-h', '-?', '--help']})
@click.version_option(version='0.1')
def cli():
    pass


def _format_exception(line, e, no_color):
    msg = 'Failed to interpret \'{}\': {}'.format(line, str(e))
    if not no_color:
        msg = '\033[31m{}\033[0m'.format(msg)
    return msg


def process(line, verbosity, formatter):
    e = CosmologEvent.from_json(line)

    if verbosity < e['level']:
        return

    click.echo(formatter.event_format(e))


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
    f = CosmologgerHumanFormatter(origin='todo',
                                  version=0,
                                  datefmt=datefmt,
                                  color=not no_color)
    with click.get_text_stream('stdin') as stdin:
        for line in stdin:
            line = line.strip()
            try:
                process(line, verbosity, f)
            except CosmologgerException as e:
                msg = _format_exception(line, e, no_color)
                click.echo(msg, err=True)
