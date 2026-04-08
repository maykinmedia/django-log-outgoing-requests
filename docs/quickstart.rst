==========
Quickstart
==========

Requirements
============

* Optional: celery

Additional requirements are installed along with the package.

Installation
============

#.  Install from PyPI using ``pip``:

    .. code-block:: bash

        pip install django-log-outgoing-requests[xml]

#.  Add ``log_outgoing_requests`` to ``INSTALLED_APPS`` in your Django
    project's ``settings.py``.

#. Run ``python manage.py migrate`` to create the necessary database tables

If celery is installed in your environment, then the task to reset the admin
configuration is automatically enabled.

The ``xml`` extra is optional - it installs LXML for pretty-printing of XML bodies. If
you don't expect to ever work with XML, you can omit it.

Configuration
=============

You must configure the ``LOGGING`` Django setting to integrate the formatter(s) and/or
handler(s). Review the Django `documentation`_ about this setting if there is no
configuration in place yet.

The snippet below provides an example of configuring the custom formatter and enabling
the custom handler to save records to the database.

.. code-block:: python
    :linenos:
    :emphasize-lines: 1, 8, 14, 20, 25, 26

    from log_outgoing_requests.formatters import HttpFormatter


    LOGGING = {
        #...,
        "formatters": {
            #...,
            "outgoing_requests": {"()": HttpFormatter},
            # optionally provide the 'format' kwarg, like with the default formatter.
        },
        "handlers": {
            #...,
            "log_outgoing_requests": {
                "level": "DEBUG",
                "formatter": "outgoing_requests",
                "class": "logging.StreamHandler",  # to write to stdout
            },
            "save_outgoing_requests": {
                "level": "DEBUG",
                "()": "log_outgoing_requests.handlers.outgoing_requests_handler_factory",
                "buffer_size": 3,  # batch size of log records to write in one go
                "flush_interval": 15.0,  # in seconds
            },
        },
        "loggers": {
            #...,
            "log_outgoing_requests": {  # the logger name must be 'log_outgoing_requests'
                "handlers": ["log_outgoing_requests", "save_outgoing_requests"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    }


.. versionadded:: 0.8.0

    Added the handler factory that automatically sets up a queue-based handler.

The library ships with safe defaults for settings - essentially only emitting
meta-information about requests and responses. To view request and response bodies,
you likely want to apply the following non-default settings:

.. code-block:: python

    LOG_OUTGOING_REQUESTS_DB_SAVE = True # save logs enabled/disabled based on the boolean value
    LOG_OUTGOING_REQUESTS_DB_SAVE_BODY = True # save request/response body
    LOG_OUTGOING_REQUESTS_EMIT_BODY = True # log request/response body
    LOG_OUTGOING_REQUESTS_MAX_AGE = 1 # delete requests older than 1 day

.. note::

    A number of settings can be configured at runtime in the admin interface:

        * Saving to database (both the entire record and the request/response bodies)
        * Maximum body size

    From a security and privacy perspective, we advise not enabling saving to the
    database by default via Django settings and instead rely on runtime configuration.

    If Celery is installed but not configured in your environment, ``LOG_OUTGOING_REQUESTS_RESET_DB_SAVE_AFTER``
    (which defines if/when database logging is reset after changes to the library config) should
    be set to ``None``. The duration for **Reset saving logs in database after** can also be
    configured from the admin and will override the value of the environment variable if defined.

    The library provides a Django management command as well as a Celery task to delete
    logs which are older than a specified time (by default, 1 day).

See :ref:`reference_settings` for all available settings and their meaning.

Usage
=====

You don't have to do anything in particular to get the functionality. Any request made
via the requests library (even in third party packages) will pass through the logging
machinery.

**Logs**

With correct configuration (see above), your logs should now be visible in the
configured handler (stdout, file, log aggregation service...).

Additionally, if you have enabled logging to the database, the log records should
be visible via *Admin* > *Outgoing request logs* > *Outgoing request logs*.

**Runtime configuration**

Via *Admin* > *Outgoing request logs* > *Outgoing request log configuration* you can
specify/override some settings that influence the logging behaviour.

Testing
=======

Set:

.. code-block:: python

    LOG_OUTGOING_REQUESTS__HANDLER_USE_QUEUE = False

when running your Django test suite. It will skip the thread and queue for log messages,
and synchronously insert the log events in the database. This will all happen in the
same database transaction that your test is currently running in, so at the end of the
test when the transaction is rolled back, your log events are rolled back too. This
prevents broken isolation between tests.

If, for some reason, you need to enable the thread-based logging, you should use a
``TransactionTestCase``, but be warned - these are much slower.

.. note:: This setting is global and cannot be changed on an individual test-basis,
   because Django only configures logging once when it initializes.

.. _`documentation`: https://docs.djangoproject.com/en/5.2/topics/logging/
