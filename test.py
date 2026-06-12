import os
import json
import time
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


LOGIN_URL = (
    "https://customer.xiaohongshu.com/login"
    "?service=https://ark.xiaohongshu.com/app-system/home?from=ark-login"
)
STATE_FILE = Path(__file__).with_name("xhs_state.json")
SELLER_INFO_URL = "https://ark.xiaohongshu.com/api/edith/seller/info/v2"


def _visible(locator):
    return locator.filter(visible=True)


def _first_visible(locator, timeout=30_000):
    item = _visible(locator).first
    item.wait_for(state="visible", timeout=timeout)
    return item


def _click_visible_text(page, text: str, timeout=10_000) -> None:
    _first_visible(page.get_by_text(text, exact=True), timeout=timeout).click()


def _new_session(cookies=None, user_agent=None) -> requests.Session:
    sess = requests.Session()
    if cookies:
        for c in cookies:
            sess.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain"),
                path=c.get("path", "/"),
            )

    sess.headers.update(
        {
            "user-agent": user_agent
            or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
            "accept": "application/json, text/plain, */*",
            "referer": "https://ark.xiaohongshu.com/app-system/home?from=ark-login",
            "origin": "https://ark.xiaohongshu.com",
        }
    )
    return sess


def _session_is_valid(sess: requests.Session) -> bool:
    try:
        response = sess.get(SELLER_INFO_URL, timeout=15)
        if response.status_code != 200:
            return False
        data = response.json()
        return bool(data.get("success") or data.get("code") == 0)
    except Exception:
        return False


def _load_cached_session() -> requests.Session | None:
    if not STATE_FILE.exists():
        return None

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        sess = _new_session(
            cookies=state.get("cookies") or [],
            user_agent=state.get("user_agent"),
        )
    except Exception:
        return None

    return sess if _session_is_valid(sess) else None


def _save_state(cookies, user_agent: str) -> None:
    STATE_FILE.write_text(
        json.dumps(
            {
                "saved_at": int(time.time()),
                "user_agent": user_agent,
                "cookies": cookies,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _browser_login(account: str, password: str) -> requests.Session:
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

        cookies = context.cookies()
        user_agent = page.evaluate("navigator.userAgent")
        _save_state(cookies, user_agent)

        browser.close()
        return _new_session(cookies=cookies, user_agent=user_agent)


def xhs_login(account: str, password: str) -> requests.Session:
    """
    Return a requests.Session with Xiaohongshu Ark login state.

    It first tries cached cookies with pure requests. If they are expired, it
    opens the browser login flow and refreshes the cache.
    """
    cached = _load_cached_session()
    if cached:
        return cached

    return _browser_login(account, password)


if __name__ == "__main__":
    account = "fanjiaman@hotata.com"
    password = "Hotata2025"

    session = xhs_login(account, password)
    response = session.get(SELLER_INFO_URL)
    print(response.status_code)
    print(response.text)
