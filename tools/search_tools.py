from __future__ import annotations

import wikipedia
from duckduckgo_search import DDGS
from langchain_core.tools import tool
from loguru import logger

from config.settings import settings


@tool
def duckduckgo_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets."""
    logger.info("DuckDuckGo search: {}", query)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines: list[str] = []
        for r in results:
            lines.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("DuckDuckGo search failed: {}", exc)
        return f"Search error: {exc}"


@tool
def wikipedia_search(query: str, sentences: int = 5) -> str:
    """Look up a topic on Wikipedia. Returns a concise summary."""
    logger.info("Wikipedia search: {}", query)
    try:
        return wikipedia.summary(query, sentences=sentences)
    except wikipedia.DisambiguationError as exc:
        options = ", ".join(exc.options[:5])
        return f"Disambiguation — try one of: {options}"
    except wikipedia.PageError:
        return f"No Wikipedia page found for '{query}'."
    except Exception as exc:
        logger.error("Wikipedia search failed: {}", exc)
        return f"Wikipedia error: {exc}"


@tool
def scrape_url(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return its text content (truncated)."""
    logger.info("Scraping URL: {}", url)
    try:
        import httpx
        from bs4 import BeautifulSoup

        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:max_chars]
    except Exception as exc:
        logger.error("Scrape failed for {}: {}", url, exc)
        return f"Scrape error: {exc}"


@tool
def summarize_text(text: str, max_length: int = 500) -> str:
    """Condense a long text to its key points using the LLM."""
    from llm.ollama_client import get_llm

    llm = get_llm()
    prompt = (
        f"Summarize the following text in under {max_length} characters. "
        f"Focus on key facts and data points.\n\n{text[:6000]}"
    )
    response = llm.invoke(prompt)
    return response.content


RESEARCH_TOOLS = [duckduckgo_search, wikipedia_search, scrape_url, summarize_text]
