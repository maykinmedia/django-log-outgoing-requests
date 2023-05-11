"""
Datastructure(s) for use in settings.py

Note: do not place any Django-specific imports in this file, as
it must be imported in settings.py.
"""

from dataclasses import dataclass


@dataclass
class ContentType:
    """
    Data class for keeping track of content types and associated default encodings
    """

    pattern: str
    default_encoding: str
