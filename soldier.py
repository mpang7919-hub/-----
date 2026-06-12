import os
import time

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


LOGIN_URL = (
    "https://customer.xiaohongshu.com/login"
    "?service=https://ark.xiaohongshu.com/app-system/home?from=ark-login"
)


def _visible(locator):
    return locator.filter(visible=True)


def _first_visible(locator, timeout=30_000):
    item = _visible(locator).first
    item.wait_for(state="visible", timeout=timeout)
    return item


def _click_visible_text(page, text: str, timeout=10_000) -> None:
    _first_visible(page.get_by_text(text, exact=True), timeout=timeout).click()


def xhs_login(account: str, password: str) -> requests.Session:
    """
    Login through the real browser flow, then export cookies into requests.Session.

    If Xiaohongshu triggers captcha/risk verification, finish it manually in the
    browser window. The function will keep waiting for the Ark redirect.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        # Account login tab. Unicode escapes avoid Windows console encoding issues.
        _click_visible_text(page, "\u8d26\u53f7\u767b\u5f55")

        account_input = _first_visible(
            page.locator(
                "input[placeholder*='\u8d26\u53f7'], "
                "input[placeholder*='\u624b\u673a\u53f7'], "
                "input[placeholder*='\u90ae\u7bb1']"
            )
        )
        account_input.fill(account)

        password_input = _first_visible(
            page.locator(
                "input[type='password'], "
                "input[placeholder*='\u5bc6\u7801']"
            )
        )
        password_input.fill(password)

        checkbox = page.locator("input[type='checkbox']:visible").first
        if checkbox.count():
            checkbox.check(force=True)

        _click_visible_text(page, "\u767b \u5f55")

        try:
            page.wait_for_url("**://ark.xiaohongshu.com/**", timeout=120_000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Login did not finish. Captcha, SMS verification, or risk "
                "confirmation may be required in the browser window."
            ) from exc

        # Let redirect-side cookies settle before copying them.
        time.sleep(1)

        sess = requests.Session()
        for c in context.cookies():
            sess.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain"),
                path=c.get("path", "/"),
            )

        sess.headers.update(
            {
                "user-agent": page.evaluate("navigator.userAgent"),
                "accept": "application/json, text/plain, */*",
                "referer": "https://ark.xiaohongshu.com/app-system/home?from=ark-login",
                "origin": "https://ark.xiaohongshu.com",
            }
        )

        browser.close()
        return sess


if __name__ == "__main__":
    account = "fanjiaman@hotata.com"
    password = "Hotata2025"

    session = xhs_login(account, password)
    response = session.get("https://ark.xiaohongshu.com/api/edith/seller/info/v2")
    print(response.status_code)
    print(response.text)
