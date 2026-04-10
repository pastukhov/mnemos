"""Wiki LLM Client for synthesizing markdown wiki pages from facts and reflections."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from core.config import Settings
from pipelines.wiki.wiki_schema import WikiPageDefinition

SYSTEM_PROMPT = """You are a wiki page synthesis expert. Your task is to create cohesive, well-structured markdown content for wiki pages.

Given:
1. Page metadata (title, description)
2. A list of facts (atomic statements)
3. A list of reflections (patterns and insights derived from facts)
4. Optionally, existing page content to update

Your responsibilities:
1. Generate clear, structured markdown content
2. Use the page title as the main heading (# title)
3. Start with an introduction (1-2 paragraphs) based on the description
4. Organize content into logical sections using headers, lists, and paragraphs
5. Reference facts and reflections naturally - don't make up information
6. When updating existing content, integrate new information without full regeneration
7. Keep content concise and well-organized

IMPORTANT RULES:
- Do NOT invent information beyond what's in the facts and reflections
- Do NOT use frontmatter or JSON - output is plain markdown only
- Do NOT add metadata blocks or YAML headers
- Facts are the source of truth - use them as evidence for claims
- Reflections provide context and patterns
- If existing_content is provided, treat it as context for updates

Output ONLY markdown content with no JSON wrapping, no code blocks, no meta tags."""


class WikiLLMClient(ABC):
    """Abstract base class for wiki page synthesis clients."""

    @abstractmethod
    def synthesize_page(
        self,
        page_def: WikiPageDefinition,
        facts: list[str],
        reflections: list[str],
        existing_content: str | None = None,
    ) -> str:
        """Synthesize a markdown wiki page from facts and reflections.

        Args:
            page_def: Page definition with title and description
            facts: List of factual statements to synthesize
            reflections: List of reflection/pattern statements
            existing_content: Optional existing page content to update

        Returns:
            Markdown string for the wiki page
        """
        raise NotImplementedError


class MockWikiLLMClient(WikiLLMClient):
    """Mock wiki client for testing - simple concatenation of facts and reflections."""

    def synthesize_page(
        self,
        page_def: WikiPageDefinition,
        facts: list[str],
        reflections: list[str],
        existing_content: str | None = None,
    ) -> str:
        """Synthesize page by concatenating facts and reflections.

        Args:
            page_def: Page definition with title and description
            facts: List of factual statements
            reflections: List of reflection statements
            existing_content: Optional existing content (prepended)

        Returns:
            Simple markdown combining all inputs
        """
        lines = []

        # Add heading
        lines.append(f"# {page_def.title}")
        lines.append("")

        # Add description as introduction
        if page_def.description:
            lines.append(page_def.description)
            lines.append("")

        # Add facts section
        if facts:
            lines.append("## Facts")
            lines.append("")
            for fact in facts:
                lines.append(f"- {fact}")
            lines.append("")

        # Add reflections section
        if reflections:
            lines.append("## Reflections")
            lines.append("")
            for reflection in reflections:
                lines.append(f"- {reflection}")
            lines.append("")

        content = "\n".join(lines).strip()

        # If existing content provided, return it with new content appended
        if existing_content:
            return f"{existing_content}\n\n{content}"

        return content


class OpenAICompatibleWikiLLMClient(WikiLLMClient):
    """OpenAI-compatible API client for wiki page synthesis."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None,
        timeout_seconds: float,
    ) -> None:
        """Initialize OpenAI-compatible wiki client.

        Args:
            model: Model name (e.g., 'gpt-4', 'gpt-4-mini')
            base_url: Base URL for API endpoint (e.g., 'https://api.openai.com/v1')
            api_key: Optional API key for authentication
            timeout_seconds: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def synthesize_page(
        self,
        page_def: WikiPageDefinition,
        facts: list[str],
        reflections: list[str],
        existing_content: str | None = None,
    ) -> str:
        """Synthesize page using LLM API.

        Args:
            page_def: Page definition with title and description
            facts: List of factual statements
            reflections: List of reflection statements
            existing_content: Optional existing content for updates

        Returns:
            Markdown string returned by LLM

        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If API response is malformed
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Format facts and reflections for inclusion in user message
        facts_text = "\n".join(f"- {fact}" for fact in facts) if facts else "No facts provided"
        reflections_text = (
            "\n".join(f"- {reflection}" for reflection in reflections)
            if reflections
            else "No reflections provided"
        )

        # Build user message
        user_message_parts = [
            f"Page Title: {page_def.title}",
            f"Page Description: {page_def.description}",
            "",
            "Facts:",
            facts_text,
            "",
            "Reflections:",
            reflections_text,
        ]

        if existing_content:
            user_message_parts.extend(
                [
                    "",
                    "Existing Content (for context):",
                    existing_content,
                ]
            )

        user_message = "\n".join(user_message_parts)

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            timeout=self.timeout_seconds,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return content.strip()


def build_wiki_llm_client(settings: Settings) -> WikiLLMClient:
    """Build a wiki LLM client from settings.

    Args:
        settings: Application settings

    Returns:
        Configured WikiLLMClient instance

    Raises:
        ValueError: If WIKI_LLM_BASE_URL is not configured
    """
    if not settings.wiki_llm_base_url:
        raise ValueError("WIKI_LLM_BASE_URL is required for wiki LLM client")

    return OpenAICompatibleWikiLLMClient(
        model=settings.wiki_llm_model,
        base_url=settings.wiki_llm_base_url,
        api_key=settings.wiki_llm_api_key,
        timeout_seconds=settings.wiki_llm_timeout_seconds,
    )
