=========
Changelog
=========

0.6.0 (2023-12-11)
==================

Small quality of life release

* Added Celery task and management command to prune log records.
* [#29] Changed request URL-field to textfield to handle arbitrary URL lengths.

0.5.2 (2023-09-22)
==================

Improved robustness after observing (likely) an APM bug.

Crashes when trying to save the log records to the database are now suppressed. This
means you lose the log record, but the application itself should continue to function
properly.

0.5.1 (2023-08-17)
==================

Fixed a bug causing request logging to happen multiple times.

0.5.0 (2023-08-15)
==================

**💥 Breaking changes**

* This library now logs to the "log_outgoing_requests" logger instead of "requests".
  Update your ``settings.LOGGING["loggers"]`` accordingly.

Other changes

* [#15] Ensure that requests are logged when request errors occur
* [#11] Add changelog file

0.4.0 (2023-06-09)
==================

Improved admin UX when viewing log records.

0.3.0 (2023-06-08)
==================

* Added Dutch translations
* Implemented default settings
* Namespace our requests monkeypatch
* Confirmed Python 3.11 and Django 4.2 support
* Fixed missing version bumps in a number of files

0.2.0 (2023-06-08)
==================

* Implemented options to log request/response bodies
