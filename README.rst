django-log-outgoing-requests
=================================================

:Version: 0.1.0
:Source: https://github.com/maykinmedia/django-log-outgoing-requests
:Keywords: logging
:PythonVersion: 3.9

|build-status| |code-quality| |black| |coverage| |docs|

|python-versions| |django-versions| |pypi-version|

Log and save outgoing requests

The current library logs only the requests made by the `requests`_ library

.. contents::

.. section-numbering::

Features
========

* Log outgoing requests made by requests library
* Save logs in database
* Overview of the saved logs in the admin page

Installation
============

Requirements
------------

* Python 3.7 or above
* setuptools 30.3.0 or above
* Django 3.2 or newer
* requests


Install
-------

.. code-block:: bash

    pip install django-log-outgoing-requests


Usage
=====

To use this with your project you need to follow these steps:

#.  Add **Django Log Outgoing Requests** to ``INSTALLED_APPS`` in your Django 
    project's ``settings.py``:

    .. code-block:: python

        INSTALLED_APPS = (
          # ...,
          "log_outgoing_requests"
        )

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

#.  Run the migrations

    .. code-block:: bash

        python manage.py migrate

#.  Make some requests using requests library within the Django context, for example using ``python manage.py shell``

    .. code-block:: console

        import requests
        res = requests.get("https://httpbin.org/json")
        print(res.json())

#.  Check stdout for the printable output, and navigate to ``/admin/log_outgoing_requests/outgoingrequestslog/`` to see 
    the saved log records


Local development
=================

To install and develop the library locally, use:

.. code-block:: bash

    pip install -e --no-build-isolation .[tests,coverage,docs,pep8,release]


.. _`requests`: https://pypi.org/project/requests/

.. _`documentation`: https://docs.djangoproject.com/en/4.1/topics/logging/

.. |build-status| image:: https://github.com/maykinmedia/django-log-outgoing-requests/workflows/Run%20CI/badge.svg
    :alt: Build status
    :target: https://github.com/maykinmedia/django-log-outgoing-requests/actions?query=workflow%3A%22Run+CI%22

.. |code-quality| image:: https://github.com/maykinmedia/django-log-outgoing-requests/workflows/Code%20quality%20checks/badge.svg
     :alt: Code quality checks
     :target: https://github.com/maykinmedia/django-log-outgoing-requests/actions?query=workflow%3A%22Code+quality+checks%22

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |coverage| image:: https://codecov.io/gh/maykinmedia/django-log-outgoing-requests/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/maykinmedia/django-log-outgoing-requests
    :alt: Coverage status

.. |docs| image:: https://readthedocs.org/projects/django-log-outgoing-requests/badge/?version=latest
    :target: https://django-log-outgoing-requests.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/django-log-outgoing-requests.svg

.. |django-versions| image:: https://img.shields.io/pypi/djversions/django-log-outgoing-requests.svg

.. |pypi-version| image:: https://img.shields.io/pypi/v/django-log-outgoing-requests.svg
    :target: https://pypi.org/project/django-log-outgoing-requests/
