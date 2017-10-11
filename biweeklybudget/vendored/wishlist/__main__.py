from __future__ import unicode_literals
import logging
import sys
import argparse

from captain import echo, exit as console, ArgError
from captain.decorators import arg, args

from wishlist import __version__
from wishlist.core import Wishlist, ParseError, RobotError
from wishlist.browser import RecoverableCrash


# https://hg.python.org/cpython/file/2.7/Lib/argparse.py#l863
class LoggingAction(argparse.Action):
    def __init__(self, option_strings, dest, help=None, **kwargs):
        super(LoggingAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=True,
            default=False,
            required=False,
            help=help
        )

    def __call__(self, parser, namespace, values, option_string=None):
        """This is called if the value is actually passed in"""
        #pout.v(namespace, values, option_string)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        log_handler = logging.StreamHandler(stream=sys.stderr)
        log_formatter = logging.Formatter('[%(levelname)s] %(message)s')
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)
        setattr(namespace, self.dest, self.const)


def main_auth():
    """Signin to amazon so you can access private wishlists"""
    w = Wishlist()
    with w.open_full() as b:
        host = w.host
        echo.out("Requesting {}", host)
        b.location(host, ignore_cookies=True)

        # If you access from another country, amazon might prompt to redirect to
        # country specific store, we don't want that
        if b.element_exists("#redir-opt-out"):
            echo.out("Circumventing redirect")
            remember = b.element("#redir-opt-out")
            stay = b.element("#redir-stay-at-www")
            remember.click()
            stay.click()

        button = b.element("#a-autoid-0-announce")
        echo.out("Clicking sign in button")
        button.click()

        # now put in your creds
        email = b.element("#ap_email")
        password = b.element("#ap_password")
        submit = b.element("#signInSubmit")
        if email and password and submit:
            echo.out("Found sign in form")
            email_in = echo.prompt("Amazon email address")
            password_in = echo.prompt("Amazon password")

        email.send_keys(email_in)
        password.send_keys(password_in)
        echo.out("Signing in")
        submit.click()

        # for 2-factor, wait for this element
        code = b.wait_for_element("#auth-mfa-otpcode", 5)
        if code:
            echo.out("2-Factor authentication is on, you should be receiving a text")
            submit = b.element("#auth-signin-button")
            remember = b.element("#auth-mfa-remember-device")
            remember.click()
            authcode = echo.prompt("2-Factor authcode")
            code.send_keys(authcode)
            submit.click()

        #https://www.amazon.com/ref=gw_sgn_ib/853-0204854-22247543
        if "/ref=gw_sgn_ib/" in b.current_url:
            echo.out("Success, you are now signed in")
            b.save()


@arg('name', nargs=1, help="the name of the wishlist, amazon.com/gp/registry/wishlist/NAME")
@arg('--start-page', dest="start_page", type=int, default=1, help="The Wishlist page you want to start on")
@arg('--stop-page', dest="stop_page", type=int, default=0, help="The Wishlist page you want to stop on")
@arg('--debug', dest="debug", action=LoggingAction, help="Turn debugging on")
def main_dump(name, start_page, stop_page, **kwargs):
    """This is really here just to test that I can parse a wishlist completely and
    to demonstrate (by looking at the code) how to iterate through a list"""
    name = name[0]
    #pout.v(name, start_page, stop_page, kwargs)
    #pout.x()

    pages = set()
    current_url = ""
    w = Wishlist()
    for i, item in enumerate(w.get(name, start_page, stop_page), 1):
        new_current_url = w.current_url
        if new_current_url != current_url:
            current_url = new_current_url
            echo.h3(current_url)

        try:
            item_json = item.jsonable()
            echo.out("{}. {} is ${:.2f}", i, item_json["title"], item_json["price"])
            echo.indent(item_json["url"])

        except RobotError:
            raise

        except ParseError as e:
            echo.err("{}. Failed!", i)
            echo.err(e.body)
            echo.exception(e)

        except KeyboardInterrupt:
            break

        except Exception as e:
            echo.err("{}. Failed!", i)
            echo.exception(e)

        finally:
            pages.add(w.current_page)

    echo.out(
        "Done with wishlist, {} total pages parsed (from {} to {})",
        len(pages),
        start_page,
        stop_page
    )


if __name__ == "__main__":
    console()

