from __future__ import unicode_literals, absolute_import
import datetime
import re
import os
from contextlib import contextmanager
import logging

from .browser import Browser, SimpleBrowser, ParseError, Soup
from .browser import NoSuchElementException, \
    WebDriverException, \
    NoSuchWindowException
from .compat import *


logger = logging.getLogger(__name__)


class RobotError(ParseError):
    """Raised when programatic access is detected"""
    pass


class BaseWishlist(Soup):
    @property
    def host(self):
        return os.environ.get("WISHLIST_HOST", "https://www.amazon.com")


class WishlistElement(BaseWishlist):
    """Wishlist.get() returns an instance of this object"""
    @property
    def uuid(self):
        uuid = self.a_uuid
        if not uuid:
            uuid = self.external_uuid
        return uuid

    @property
    def url(self):
        url = self.a_url
        if not url:
            url = self.external_url
        return url

    @property
    def a_uuid(self):
        """return the amazon uuid of the item"""
        uuid = ""
        a_url = self.url
        if a_url:
            m = re.search("/dp/([^/]+)", self.url)
            if m:
                uuid = m.group(1)
        else:
            # go through all the a tags in ItemInfo looking for asin=
            el = self.soup.find("div", id=re.compile("^itemInfo_"))
            if el:
                regex = re.compile("asin\=([^\&]+)")
                els = el.findAll("a", {"href": regex})
                for el in els:
                    m = regex.search(el.attrs["href"])
                    if m:
                        uuid = m.group(1).strip()
                        if uuid: break
        return uuid

    @property
    def a_url(self):
        """return the amazon url of the item"""
        href = ""
        # http://stackoverflow.com/questions/5041008/how-to-find-elements-by-class
        # http://stackoverflow.com/a/5099355/5006
        # http://stackoverflow.com/a/2832635/5006
        el = self.soup.find("a", id=re.compile("^itemName_"))
        if el and ("href" in el.attrs):
            m = re.search("/dp/([^/]+)", el.attrs["href"])
            if m:
                href = "{}/dp/{}/".format(self.host, m.group(1))

        return href

    @property
    def external_uuid(self):
        """Return the external uuid of the item"""
        ext_url = self.external_url
        return md5(ext_url) if ext_url else ""

    @property
    def external_url(self):
        """was this added from an external website? Then this returns that url"""
        href = ""
        el = self.soup.find("span", {"class": "clip-text"})
        if el:
            el = el.find("a")
            if el:
                href = el.attrs.get("href", "")
        return href


    @property
    def image(self):
        src = ""
        imgs = self.soup.find_all("img")
        for img in imgs:
            if "src" in img.attrs:
                if img.parent and img.parent.name == "a":
                    a = img.parent
                    if a.attrs["href"].startswith("/dp/"):
                        src = img.attrs["src"]
                        break

        if not src:
            for img in imgs:
                maybe_src = img.attrs.get("src", "")
                if "/images/I/" in maybe_src:
                    src = maybe_src
                    break

        return src

    @property
    def price(self):
        el = self.soup.find("span", id=re.compile("^itemPrice_"))
        if not el or len(el.contents) < 1:
            return 0.0
        try:
            # the new HTML actually has separate spans for whole currency
            # units and fractional currency units
            whole = float(
                el.find(
                    'span', class_='a-price-whole'
                ).contents[0].strip().replace(',', '')
            )
            fract = float(
                el.find('span', class_='a-price-fraction').contents[0].strip()
            )
            return float(whole) + (float(fract) / 100.0)
        except (ValueError, IndexError):
            logger.error('Unable to parse price span: %s', el)
            return 0.0

    @property
    def marketplace_price(self):
        price = 0.0
        el = self.soup.find("span", {"class": "itemUsedAndNewPrice"})
        if el and len(el.contents) > 0:
            price = float(el.contents[0].replace("$", "").replace(",", ""))
        return price

    @property
    def title(self):
        title = ""
        el = self.soup.find("a", id=re.compile("^itemName_"))
        if el and len(el.contents) > 0:
            title = el.contents[0].strip()

        else:
            el = self.soup.find("span", id=re.compile("^itemName_"))
            if el and len(el.contents) > 0:
                title = el.contents[0].strip()

        return title

    @property
    def comment(self):
        ret = ""
        el = self.soup.find("span", id=re.compile("^itemComment_"))
        if el and len(el.contents) > 0:
            ret = el.contents[0].strip()
        return ret

    @property
    def rating(self):
        stars = 0.0
        el = self.soup.find("a", {"class": "reviewStarsPopoverLink"})
        if el:
            el = el.find("span", {"class": "a-icon-alt"})
            if len(el.contents) > 0:
                stars = float(el.contents[0].strip().split()[0])
        return stars

    @property
    def author(self):
        el = self.soup.find("a", id=re.compile("^itemName_"))
        if not el:
            return ''
        author = el.parent.next_sibling
        if author is None or len(author.contents) < 1:
            return ''
        return author.contents[0].strip().replace("by ", "")

    @property
    def added(self):
        el = self.soup.find('span', id=re.compile('^itemAddedDate_'))
        if el is None or len(el.contents) < 3:
            logger.error('Unable to find added date for item.')
            return None
        return datetime.datetime.strptime(el.contents[2].strip(), '%B %d, %Y')

    @property
    def wanted_count(self):
        """returns the wanted portion of .quantity"""
        return self.quantity[0]

    @property
    def has_count(self):
        """Returns the has portion of .quantity"""
        return self.quantity[1]

    @property
    def quantity(self):
        """Return the quantity wanted and owned of the element

        :returns: tuple of ints (wanted, has)
        """
        el = self.soup.find(id=re.compile("^itemQuantityRow_"))
        bits = [s for s in el.stripped_strings]
        return (int(bits[1]), int(bits[3]))

    @property
    def source(self):
        """Return "amazon" if product is offered by amazon, otherwise return "marketplace" """
        ret = "marketplace"
        if not self.is_digital():
            el = self.soup.find(class_=re.compile("^itemAvailOfferedBy"))
            if el:
                s = el.string
                # In Stock. Offered by Amazon.com.
                if s and re.search(r"amazon\.com", s, re.I):
                    ret = "amazon"
        return ret

    @property
    def body(self):
        return self.soup.prettify()

    def __init__(self, element):
        self.soup = self.soupify(element)

    def is_digital(self):
        """Return true if this is a digital good like a Kindle book or mp3"""
        ret = False
        el = self.soup.find(class_=re.compile("^itemAvailOfferedBy"))
        if el:
            s = el.string
            if s:
                ret = True
                if not re.search(r"auto-delivered\s+wirelessly", s, re.I):
                    if not re.search(r"amazon\s+digital\s+services", s, re.I):
                        ret = False
        return ret

    def is_amazon(self):
        """returns True if product is offered by amazon, otherwise False"""
        return "amazon" in self.source

    def jsonable(self):
        json_item = {}
        json_item["title"] = self.title
        json_item["image"] = self.image
        json_item["uuid"] = self.uuid
        json_item["url"] = self.url
        json_item["price"] = self.price
        json_item["marketplace_price"] = self.marketplace_price
        json_item["comment"] = self.comment
        json_item["author"] = self.author
        json_item["added"] = self.added.strftime('%B %d, %Y')
        json_item["rating"] = self.rating
        json_item["quantity"] = {
            "wanted": self.wanted_count,
            "has": self.has_count
        }
        json_item["digital"] = self.is_digital()
        json_item["source"] = self.source
        return json_item


class Wishlist(BaseWishlist):
    """Wrapper that is specifically designed for getting amazon wishlists"""

    element_class = WishlistElement

    @contextmanager
    def open_simple(self):
        with SimpleBrowser.open() as b:
            yield b

    @contextmanager
    def open_full(self):
        with Browser.open() as b:
            yield b

    def get_items_from_body(self, body):
        """this will return the wishlist elements on the current page"""
        soup = self.soupify(body)
        html_items = soup.findAll("div", {"id": re.compile("^item_")})
        for i, html_item in enumerate(html_items):
            item = self.element_class(html_item)
            yield item

    def get_total_pages_from_body(self, body):
        """return the total number of pages of the wishlist

        body -- string -- the complete html page
        """
        page = 0
        soup = self.soupify(body)

        try:
            el = soup.find("ul", {"class": "a-pagination"})
            els = el.findAll("li", {"class": re.compile("^a-")})
            el = els[-2]
            if len(el.contents) and len(el.contents[0].contents):
                page = int(el.contents[0].contents[0].strip())
        except AttributeError:
            logger.info(
                'Could not find total number of pages for wishlist %s; '
                'assuming new-style lazy load with one page', self.wishlist_name
            )
            return 1

        return page

    def robot_check(self, body):
        soup = self.soupify(body)

        el = soup.find("form", action=re.compile(r"validateCaptcha", re.I))
        if el:
            raise RobotError("Amazon robot check")

    def get_wishlist_url(self, name, page):
        base_url = "{}/gp/registry/wishlist/{}".format(self.host, name)
        if page > 0:
            base_url += "?page={}".format(page)
        return base_url

    def set_current(self, url, body):
        self.current_url = url
        self.current_body = body
        soup = self.soupify(body)
        self.robot_check(soup)
        return soup

    def get(self, name, start_page=0, stop_page=0):
        """return the items of the given wishlist name

        :param name: the amazon wishlist NAME, (eg, the NAME in amazon.com/gp/registry/wishlist/NAME url)
        :param start_page: the page of the wishlist to start parsing
        :param stop_page: the page of the wishlist to stop parsing
        """
        crash_count = 0
        page = start_page if start_page > 1 else 1
        self.wishlist_name = name
        self.current_page = page
        self.current_body = None

        soup = None
        page_count = None

        with self.open_simple() as b:
        #with self.open_full() as b:
            while True:
                try:
                    # https://www.amazon.com/gp/registry/wishlist/NAME
                    b.location(self.get_wishlist_url(name, page))
                    soup = self.set_current(b.current_url, b.body)
                    if page_count is None:
                        page_count = stop_page if stop_page else self.get_total_pages_from_body(soup)

                    for i, item in enumerate(self.get_items_from_body(soup)):
                        yield item

                except Exception as e:
                    logger.exception(e)
                    raise

                finally:
                    page += 1
                    if page_count is None or page > page_count:
                        break

                    self.current_page = page
                    soup = None

