import logging

from .core import Wishlist, WishlistElement, ParseError


__version__ = "0.1.3"


# get rid of "No handler found" warnings (cribbed from requests)
logging.getLogger(__name__).addHandler(logging.NullHandler())

