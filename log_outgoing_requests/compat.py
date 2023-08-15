import traceback

import django

# Taken from djangorestframework, see
# https://github.com/encode/django-rest-framework/blob/376a5cbbba3f8df9c9db8c03a7c8fa2a6e6c05f4/rest_framework/compat.py#LL156C1-L177C10
#
# License:
#
# Copyright © 2011-present, [Encode OSS Ltd](https://www.encode.io/).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

if django.VERSION >= (4, 2):
    # Django 4.2+: use the stock parse_header_parameters function
    # Note: Django 4.1 also has an implementation of parse_header_parameters
    #       which is slightly different from the one in 4.2, it needs
    #       the compatibility shim as well.
    from django.utils.http import parse_header_parameters  # type: ignore
else:
    # Django <= 4.1: create a compatibility shim for parse_header_parameters
    from django.http.multipartparser import parse_header

    def parse_header_parameters(line):
        # parse_header works with bytes, but parse_header_parameters
        # works with strings. Call encode to convert the line to bytes.
        main_value_pair, params = parse_header(line.encode())
        return main_value_pair, {
            # parse_header will convert *some* values to string.
            # parse_header_parameters converts *all* values to string.
            # Make sure all values are converted by calling decode on
            # any remaining non-string values.
            k: v if isinstance(v, str) else v.decode()
            for k, v in params.items()
        }


__all__ = ["parse_header_parameters"]


def format_exception(exception: BaseException):
    t, e, tb = type(exception), exception, exception.__traceback__
    return traceback.format_exception(t, e, tb)


# Celery compat, in case celery is not installed
try:
    from celery import shared_task
except ImportError:

    def shared_task(func):
        class NoOpTask:
            def apply_async(self, *args, **kwargs):
                pass

        return NoOpTask()
