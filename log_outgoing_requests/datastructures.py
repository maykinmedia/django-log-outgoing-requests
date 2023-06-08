"""
Datastructure(s) for use in settings.py

Note: do not place any Django-specific imports in this file, as
it must be imported in settings.py.
"""

from dataclasses import dataclass
from typing import Union


@dataclass
class ContentType:
    """
    Specify a supported content type and matching default encoding.

    The default encoding is used when no explicit encoding could be parsed from the
    Content-Type HTTP header.
    """

    pattern: str
    default_encoding: str


@dataclass
class ProcessedBody:
    allow_saving_to_db: bool
    content: Union[bytes, str]
    content_type: str
    encoding: str
