from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str | None = None
    snippet: str | None = None
    provider: str = "unknown"


@dataclass(frozen=True)
class ResearchContext:
    query: str
    summary: str | None = None
    sources: list[ResearchSource] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.summary and not self.sources and not self.topics

    def to_prompt_text(self) -> str:
        if self.is_empty:
            return "Исследовательский контекст не найден."
        lines = [f"Поисковый запрос: {self.query}"]
        if self.summary:
            lines.append(f"Краткая справка: {self.summary}")
        if self.topics:
            lines.append("Темы/ключевые слова: " + ", ".join(self.topics[:12]))
        if self.sources:
            lines.append("Источники:")
            for source in self.sources[:8]:
                url = f" ({source.url})" if source.url else ""
                snippet = f" — {source.snippet}" if source.snippet else ""
                lines.append(f"- {source.title}{url}{snippet}")
        return "\n".join(lines)


class GoalResearcher:
    """Collects external context before decomposition.

    Tavily gives the best web-search quality when configured. Without a key,
    the public fallback only uses no-auth endpoints such as OpenLibrary and
    Wikipedia, so it is intentionally best-effort and never blocks generation.
    """

    def research(self, title: str, description: str | None, context: str | None) -> ResearchContext:
        settings = get_settings()
        query = self._build_query(title, description, context)
        if not settings.web_research_enabled or settings.research_provider == "none":
            return ResearchContext(query=query)

        sources: list[ResearchSource] = []
        summary_parts: list[str] = []
        topics: list[str] = []

        if settings.research_provider in {"auto", "tavily"} and settings.tavily_api_key:
            tavily_context = self._tavily(query)
            sources.extend(tavily_context.sources)
            if tavily_context.summary:
                summary_parts.append(tavily_context.summary)
            topics.extend(tavily_context.topics)

        if settings.research_provider in {"auto", "public"}:
            public_context = self._public_context(query, title)
            sources.extend(public_context.sources)
            if public_context.summary:
                summary_parts.append(public_context.summary)
            topics.extend(public_context.topics)

        return ResearchContext(
            query=query,
            summary=" ".join(dict.fromkeys(summary_parts)) or None,
            sources=self._dedupe_sources(sources),
            topics=self._dedupe_topics(topics),
        )

    def _tavily(self, query: str) -> ResearchContext:
        settings = get_settings()
        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": settings.research_max_results,
                },
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - research must degrade gracefully.
            logger.warning("research.tavily_failed", error=str(exc))
            return ResearchContext(query=query)

        sources = [
            ResearchSource(
                title=str(item.get("title") or "Источник"),
                url=item.get("url"),
                snippet=item.get("content"),
                provider="tavily",
            )
            for item in payload.get("results", [])
        ]
        return ResearchContext(
            query=query,
            summary=payload.get("answer"),
            sources=sources,
            topics=self._extract_topics(" ".join(item.snippet or "" for item in sources)),
        )

    def _public_context(self, query: str, title: str) -> ResearchContext:
        sources: list[ResearchSource] = []
        summary_parts: list[str] = []
        topics: list[str] = []

        book_title = self.extract_quoted_title(title) or title
        open_library = self._open_library(book_title)
        sources.extend(open_library.sources)
        if open_library.summary:
            summary_parts.append(open_library.summary)
        topics.extend(open_library.topics)

        wikipedia = self._wikipedia(query)
        sources.extend(wikipedia.sources)
        if wikipedia.summary:
            summary_parts.append(wikipedia.summary)
        topics.extend(wikipedia.topics)

        return ResearchContext(
            query=query,
            summary=" ".join(summary_parts) or None,
            sources=sources,
            topics=topics,
        )

    def _open_library(self, title: str) -> ResearchContext:
        try:
            response = httpx.get(
                "https://openlibrary.org/search.json",
                params={"title": title, "limit": 3, "fields": "key,title,author_name,first_publish_year,subject"},
                timeout=8,
            )
            response.raise_for_status()
            docs = response.json().get("docs", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("research.open_library_failed", error=str(exc))
            return ResearchContext(query=title)

        sources: list[ResearchSource] = []
        topics: list[str] = []
        summaries: list[str] = []
        for doc in docs:
            authors = ", ".join(doc.get("author_name") or [])
            year = doc.get("first_publish_year")
            subjects = [str(item) for item in (doc.get("subject") or [])[:8]]
            topics.extend(subjects)
            summary = f"{doc.get('title', title)}"
            if authors:
                summary += f", авторы: {authors}"
            if year:
                summary += f", первое издание: {year}"
            if subjects:
                summary += f", темы: {', '.join(subjects[:5])}"
            summaries.append(summary)
            sources.append(
                ResearchSource(
                    title=summary,
                    url=f"https://openlibrary.org{doc.get('key')}" if doc.get("key") else None,
                    snippet=", ".join(subjects[:8]) if subjects else None,
                    provider="openlibrary",
                )
            )

        return ResearchContext(query=title, summary=" ".join(summaries[:2]) or None, sources=sources, topics=topics)

    def _wikipedia(self, query: str) -> ResearchContext:
        try:
            search = httpx.get(
                "https://ru.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "utf8": 1,
                    "srlimit": 3,
                },
                timeout=8,
            )
            search.raise_for_status()
            hits = search.json().get("query", {}).get("search", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("research.wikipedia_failed", error=str(exc))
            return ResearchContext(query=query)

        sources = [
            ResearchSource(
                title=str(hit.get("title") or "Wikipedia"),
                url=f"https://ru.wikipedia.org/wiki/{str(hit.get('title', '')).replace(' ', '_')}",
                snippet=self._strip_html(str(hit.get("snippet") or "")),
                provider="wikipedia",
            )
            for hit in hits
        ]
        topics = self._extract_topics(" ".join(source.title + " " + (source.snippet or "") for source in sources))
        return ResearchContext(query=query, sources=sources, topics=topics)

    def _build_query(self, title: str, description: str | None, context: str | None) -> str:
        parts = [title, description or "", context or ""]
        query = " ".join(part.strip() for part in parts if part and part.strip())
        return re.sub(r"\s+", " ", query)[:280]

    @staticmethod
    def extract_quoted_title(value: str) -> str | None:
        match = re.search(r"[\"«](.+?)[\"»]", value)
        return match.group(1).strip() if match else None

    @staticmethod
    def _strip_html(value: str) -> str:
        return re.sub(r"<[^>]+>", "", value)

    @staticmethod
    def _extract_topics(value: str) -> list[str]:
        words = re.findall(r"[А-Яа-яA-Za-z][А-Яа-яA-Za-z-]{4,}", value)
        stop = {
            "который",
            "которая",
            "также",
            "может",
            "через",
            "после",
            "before",
            "about",
            "which",
            "their",
        }
        return [word for word in words if word.lower() not in stop][:20]

    @staticmethod
    def _dedupe_sources(sources: list[ResearchSource]) -> list[ResearchSource]:
        seen: set[str] = set()
        unique: list[ResearchSource] = []
        for source in sources:
            key = source.url or source.title
            if key in seen:
                continue
            seen.add(key)
            unique.append(source)
        return unique

    @staticmethod
    def _dedupe_topics(topics: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for topic in topics:
            key = topic.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(topic)
        return unique[:20]
