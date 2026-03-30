from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from loguru import logger

from config.settings import settings

_BROWSER_CONTEXT: dict[str, Any] = {}


async def _ensure_browser() -> Any:
    """Lazily start a Playwright browser and return (browser, page)."""
    if "browser" not in _BROWSER_CONTEXT:
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        _BROWSER_CONTEXT["pw"] = pw
        _BROWSER_CONTEXT["browser"] = browser
        _BROWSER_CONTEXT["page"] = page
    return _BROWSER_CONTEXT["browser"], _BROWSER_CONTEXT["page"]


async def _close_browser() -> None:
    """Tear down the browser context."""
    if "browser" in _BROWSER_CONTEXT:
        await _BROWSER_CONTEXT["browser"].close()
        await _BROWSER_CONTEXT["pw"].stop()
        _BROWSER_CONTEXT.clear()


def _run_async(coro):
    """Run an async coroutine from a sync tool context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


@tool
def navigate_to(url: str) -> str:
    """Navigate the browser to a URL. Returns the page title."""
    logger.info("Navigating to: {}", url)

    async def _nav():
        _, page = await _ensure_browser()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Loaded: {await page.title()} — {page.url}"

    try:
        return _run_async(_nav())
    except Exception as exc:
        logger.error("Navigation failed: {}", exc)
        return f"Navigation error: {exc}"


@tool
def click_element(selector: str) -> str:
    """Click an element matching the CSS selector."""
    logger.info("Clicking: {}", selector)

    async def _click():
        _, page = await _ensure_browser()
        await page.click(selector, timeout=5000)
        return f"Clicked: {selector}"

    try:
        return _run_async(_click())
    except Exception as exc:
        return f"Click error: {exc}"


@tool
def fill_input(selector: str, text: str) -> str:
    """Type text into a form field matching the CSS selector."""
    logger.info("Filling {} with text", selector)

    async def _fill():
        _, page = await _ensure_browser()
        await page.fill(selector, text, timeout=5000)
        return f"Filled: {selector}"

    try:
        return _run_async(_fill())
    except Exception as exc:
        return f"Fill error: {exc}"


@tool
def extract_text(selector: str = "body", limit: int = 3000) -> str:
    """Extract text content from elements matching a CSS selector."""
    logger.info("Extracting text from: {}", selector)

    async def _extract():
        _, page = await _ensure_browser()
        elements = await page.query_selector_all(selector)
        texts: list[str] = []
        for el in elements:
            t = await el.inner_text()
            if t.strip():
                texts.append(t.strip())
        combined = "\n".join(texts)
        return combined[:limit] if combined else "No text found."

    try:
        return _run_async(_extract())
    except Exception as exc:
        return f"Extract error: {exc}"


@tool
def take_screenshot(filename: str = "screenshot.png") -> str:
    """Capture a screenshot of the current page."""
    logger.info("Taking screenshot: {}", filename)

    async def _screenshot():
        _, page = await _ensure_browser()
        path = settings.agent_workspace / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path), full_page=True)
        return f"Screenshot saved: {path}"

    try:
        return _run_async(_screenshot())
    except Exception as exc:
        return f"Screenshot error: {exc}"


@tool
def wait_for_element(selector: str, timeout_ms: int = 5000) -> str:
    """Wait for an element to appear on the page."""

    async def _wait():
        _, page = await _ensure_browser()
        await page.wait_for_selector(selector, timeout=timeout_ms)
        return f"Element found: {selector}"

    try:
        return _run_async(_wait())
    except Exception as exc:
        return f"Wait error: {exc}"


@tool
def get_page_links(limit: int = 50) -> str:
    """Extract all href links from the current page."""

    async def _links():
        _, page = await _ensure_browser()
        links = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
        )
        lines = [f"{l['text']} → {l['href']}" for l in links[:limit] if l["text"]]
        return "\n".join(lines) if lines else "No links found."

    try:
        return _run_async(_links())
    except Exception as exc:
        return f"Links error: {exc}"


@tool
def close_browser() -> str:
    """Close the browser and release resources."""
    try:
        _run_async(_close_browser())
        return "Browser closed."
    except Exception as exc:
        return f"Close error: {exc}"


BROWSER_TOOLS = [
    navigate_to,
    click_element,
    fill_input,
    extract_text,
    take_screenshot,
    wait_for_element,
    get_page_links,
    close_browser,
]
