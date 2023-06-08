==========
Quickstart
==========

Requirements
============

* Python 3.8 or newer
* Django 3.2 or newer

Additional requirements are installed along with the package.

Installation
============

#.  Install from PyPI using ``pip``:

    .. code-block:: bash

        pip install django-log-outgoing-requests

#.  Add ``log_outgoing_requests`` to ``INSTALLED_APPS`` in your Django 
    project's ``settings.py``.

#. Run ``python manage.py migrate`` to create the necessary database tables

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
                # enabling saving to database
                "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
            },
        },
        "loggers": {
            #...,
            "requests": {  # the logger name must be 'requests'
                "handlers": ["log_outgoing_requests", "save_outgoing_requests"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    }


The library ships with safe defaults for settings - essentially only emitting
meta-information about requests and responses. To view request and response bodies,
you likely want to apply the following non-default settings:

.. code-block:: python

    LOG_OUTGOING_REQUESTS_DB_SAVE = True # save logs enabled/disabled based on the boolean value
    LOG_OUTGOING_REQUESTS_DB_SAVE_BODY = True # save request/response body
    LOG_OUTGOING_REQUESTS_EMIT_BODY = True # log request/response body

.. note::

    A number of settings can be configured at runtime in the admin interface:

        * Saving to database (both the entire record and the request/response bodies)
        * Maximum body size

    From a security and privacy perspective, we advise not enabling saving to the
    database by default via Django settings and instead rely on runtime configuration.

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

.. _`documentation`: https://docs.djangoproject.com/en/4.1/topics/logging/
