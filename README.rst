django-log-outgoing-requests
=================================================

:Version: 0.8.0
:Source: https://github.com/maykinmedia/django-log-outgoing-requests
:Keywords: logging, django, requests

|build-status| |code-quality| |ruff| |coverage| |docs|

|python-versions| |django-versions| |pypi-version|

A logging solution for outgoing requests made via the requests_ library.

django-log-outgoing-requests provides a custom formatter and handler for the Python
``logging`` standard library. It integrates with existing logging configuration and
provides (configuration) options to save the log records to the database.

You would typically use this as a tool to debug integration with external HTTP services,
via log shipping solutions and/or the Django admin.


.. contents::

.. section-numbering::

Features
========

* log formatter for a readable representation of a request and response
* log handler to persist relevant log records to the database
* configurable via Django settings
* runtime configuration in the admin, overriding defaults from Django settings.

Usage
=====

Please see the hosted documentation_ for installation, configuration and usage
instructions.

Local development
=================

To install and develop the library locally, use:

.. code-block:: bash

    uv pip install -e .[tests,docs,release,celery]

Before releasing, make sure the styles are up to date:

.. code-block:: bash

    python -m log_outgoing_requests.syntax_highlighting


.. _`requests`: https://pypi.org/project/requests/

.. _`documentation`: https://django-log-outgoing-requests.readthedocs.io/en/latest/

.. |build-status| image:: https://github.com/maykinmedia/django-log-outgoing-requests/workflows/Run%20CI/badge.svg
    :alt: Build status
    :target: https://github.com/maykinmedia/django-log-outgoing-requests/actions?query=workflow%3A%22Run+CI%22

.. |code-quality| image:: https://github.com/maykinmedia/django-log-outgoing-requests/workflows/Code%20quality%20checks/badge.svg
     :alt: Code quality checks
     :target: https://github.com/maykinmedia/django-log-outgoing-requests/actions?query=workflow%3A%22Code+quality+checks%22

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

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
