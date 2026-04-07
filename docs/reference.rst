=========
Reference
=========

Public API documentation.

.. _reference_settings:

Settings
========

.. autoclass:: log_outgoing_requests.conf.LogOutgoingRequestsConf
    :members:

Formatters
==========

.. automodule:: log_outgoing_requests.formatters
    :members:

Handlers
========

.. automodule:: log_outgoing_requests.handlers
    :members:

uWSGI/Celery integration
========================

When integrating the queue-based logging handler (via
:func:`log_outgoing_requests.handlers.outgoing_requests_handler_factory`) in uWSGI
and/or Celery environments, some additional care is required.

**Celery workers**

Celery workers that use the prefork (the default) concurrency model must take care to
defer the background thread initialization by setting an environment variable to
``true``:

.. code-block:: sh

    export _LOG_OUTGOING_REQUESTS_LOGGER_DEFER_LISTENER=true

Failing to do so will lead to deadlocks.

**Celery beat**

Celery beat shouldn't need the functionality of this library, but to be safe, the
deferred initialization is automatically taken care of.

**uWSGI**

uWSGI also uses a forking process model with the same deadlock risks like the Celery
workers. However, it's automatically taken care of when a uWSGI environment is detected
and the background thread initialization is deferred until after the worker processes
have forked.
