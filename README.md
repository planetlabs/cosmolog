# Cosmolog

Cosmolog provides structured log formatting for your application. It treats
logs as event streams and will record each log event as a json object with a
schema.

## CosmologEvent Schema

A cosmolog event looks like the following:

    {
        "version": 0,
        "stream_name": "foo_nginx",
        "origin": "foo-api1.com",
        "timestamp": "2016-09-02T16:34:12.019105Z",
        "format": "service {name} started",
        "level": 400,
        "payload": {"name": "foo"}
    }

    version     (int)    The version of the logging schema.
    stream_name (string) The name that identifies the log stream.
    origin      (string) FQDN of the host on which the stream originated.
    timestamp   (string) UTC ISO8601 formatted datetime string.
    format      (string) Optional Python Format String to format the payload to
                         make it human-readable. Please use format strings with
                         replacement fields that are delimited with "{}".
    level       (int)    The log level.
    payload     (dict)   A flat dictionary of key-value pairs where keys are
                         strings and values can be any scalar type.


## Installation

    pip install cosmolog

## Quick Start
    
    from cosmolog import setup_logging
    from cosmolog import Cosmologger

    setup_logging()

    l = Cosmologger('foo')
    l.info('Hello World')
    l.info('Hello {person}', person='Dave')
    l.info(value1=0.98, value2=4.0)

## Human

`human` is a command line tool that formats machine readable logs for humans.
It reads stdin and writes formatted lines to stdout.

    $ echo '{"origin": "enterprise.starfleet.com", "stream_name": "telemetry", "format": "Measurement complete: gravity={gravity}", "timestamp": "2016-10-19T04:13:15.049920Z", "level": 400, "version": 0, "payload": {"gravity": 1.8}}' | human
    Oct 19 04:13:15 enterprise.starfleet.com telemetry: [INFO] Measurement complete: gravity=1.8

## Advanced Usage: setup_logging

`setup_logging` provides basic Python logging configuration with
`CosmologgerFormatter` class as the default logging formatter. The default
logging configuration looks like the following:

    LOGGING_CONFIG = {
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

By default, `origin` is set to `socket.getfqdn()`. To set it yourself:

    setup_logging(origin='my-fully-qualified-domain.com')

You can configure Cosmologger with a custom configuration dictionary, as
you would with regular Python logging. Let's say you want to stream your log 
entries to a file in the CosmologEvent schema, as well as stderr in a human-
readable format:

    my_custom_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'cosmolog': {
                '()': CosmologgerFormatter,
                'origin': origin,
                'version': 0,
            },
            'cosmolog-human': {
                '()': CosmologgerHumanFormatter,
                'origin': origin,
                'version': 0,
            },
        },
        'handlers': {
            'file_handler': {
                'class': 'logging.FileHandler',
                'formatter': 'cosmolog',
                'filename': '/path/to/my/file.log'
            },
            'stderr': {
                'class': 'logging.StreamHandler',
                'formatter': 'cosmolog-human',
		'color': True
            },
        },
        'root': {
            'handlers': ['file_handler', 'stderr'],
            'level': 'DEBUG',
        }
    }

    setup_logging(custom_config=my_custom_config)

By default, your log level will be set to `INFO`. You can set it to a
different [level](https://docs.python.org/2/library/logging.html#levels):

    setup_logging(level='DEBUG')

The table below shows the level names, and the numberic values they will be
mapped to in the log output:

| Level | Numeric value |
| ----- | ------------- |
| FATAL | 100           |
| ERROR | 200           |
| WARN  | 300           |
| INFO  | 400           |
| DEBUG | 500           |
| TRACE | 600           |

## Advanced usage: Exceptions

Normally, all keyword arguments are faithfully passed into the `CosmologEvent`
payload field, except in the case of logging exceptions. Here, the conventions
of the builtin logging library are followed. Calling `Cosmologger.exception` or
any of the other logging methods with the keyword argument `exc_info=1` will
add traceback information to the payload's `exc_text` field. If there is no
`{exc_text}` specified in the format string, then the format field will be
appended with `'\n{exc_text}'`.

## Development

    pip install -e .[test]
    tox
