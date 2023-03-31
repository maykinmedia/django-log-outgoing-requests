==========
Quickstart
==========

Requirements
------------

* Python 3.7 or above
* Django 3.2 or newer
* requests

Installation
============

#.  Install from PyPI using ``pip``:

    .. code-block:: bash

        pip install django-log-outgoing-requests

#.  Add ``log_outgoing_requests`` to ``INSTALLED_APPS`` in your Django 
    project's ``settings.py``.

#.  Update your ``settings.py`` file with the following (if you haven't defined 
    logging yet, you can see the Django's `documentation`_):

    .. code-block:: python

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
                    "class": "logging.StreamHandler",
                },
                "save_outgoing_requests": {
                    "level": "DEBUG",
                    "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
                },
            },
            "loggers": {
                #...,
                "requests": {
                    "handlers": ["log_outgoing_requests", "save_outgoing_requests"],
                    "level": "DEBUG",
                    "propagate": True,
                },
            },
        }

        LOG_OUTGOING_REQUESTS_DB_SAVE = True # save logs enabled/disabled based on the boolean value

#.  Run ``python manage.py migrate`` to create the necessary database tables.

Usage
-----
**Logs**

Once the django logging has been updated from the ``settings.LOGGING`` you can see the logs each time 
you make a request with requests library.

**Django admin**

In the Django admin, you can see an overview of all the saved logs when save is enabled.

.. _`documentation`: https://docs.djangoproject.com/en/4.1/topics/logging/
