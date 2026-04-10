"""Tests for WikiLLMClient implementations."""

from unittest.mock import MagicMock, patch

import pytest

from core.config import Settings
from pipelines.wiki.wiki_llm_client import (
    MockWikiLLMClient,
    OpenAICompatibleWikiLLMClient,
    build_wiki_llm_client,
)
from pipelines.wiki.wiki_schema import WikiPageDefinition


@pytest.fixture
def page_def():
    """Fixture for WikiPageDefinition."""
    return WikiPageDefinition(
        name="career",
        title="Карьера и навыки",
        description="Информация о карьере и профессиональных навыках",
        domains=["self"],
        kinds=["fact", "reflection"],
    )


@pytest.fixture
def facts():
    """Fixture for list of facts."""
    return [
        "User prefers building automated systems.",
        "User enjoys infrastructure automation.",
        "User has experience with Python and Go.",
    ]


@pytest.fixture
def reflections():
    """Fixture for list of reflections."""
    return [
        "User shows a stable career pattern centered on automation and systems design.",
        "User values efficiency and observable systems.",
    ]


class TestMockWikiLLMClient:
    """Tests for MockWikiLLMClient."""

    def test_synthesize_page_basic(self, page_def, facts, reflections):
        """Test basic page synthesis with facts and reflections."""
        client = MockWikiLLMClient()
        result = client.synthesize_page(page_def, facts, reflections)

        assert isinstance(result, str)
        assert "# " in result  # Contains heading
        assert page_def.title in result
        # Facts should be present
        for fact in facts:
            assert fact in result
        # Reflections should be present
        for reflection in reflections:
            assert reflection in result

    def test_synthesize_page_without_reflections(self, page_def, facts):
        """Test page synthesis without reflections."""
        client = MockWikiLLMClient()
        result = client.synthesize_page(page_def, facts, [])

        assert isinstance(result, str)
        assert page_def.title in result
        for fact in facts:
            assert fact in result

    def test_synthesize_page_with_existing_content(self, page_def, facts, reflections):
        """Test page synthesis with existing content appends new content."""
        existing_content = "## Previous Section\n\nSome existing information.\n\n"
        client = MockWikiLLMClient()
        result = client.synthesize_page(
            page_def, facts, reflections, existing_content=existing_content
        )

        assert isinstance(result, str)
        # New content should be added at the end
        assert page_def.title in result
        for fact in facts:
            assert fact in result

    def test_synthesize_page_empty_facts(self, page_def):
        """Test page synthesis with empty facts list."""
        client = MockWikiLLMClient()
        result = client.synthesize_page(page_def, [], [])

        assert isinstance(result, str)
        assert page_def.title in result

    def test_mock_client_returns_markdown_string(self, page_def, facts):
        """Test that MockWikiLLMClient returns plain markdown string."""
        client = MockWikiLLMClient()
        result = client.synthesize_page(page_def, facts, [])

        # Should be markdown, not JSON
        assert not result.strip().startswith("{")
        assert not result.strip().startswith("[")


class TestOpenAICompatibleWikiLLMClient:
    """Tests for OpenAICompatibleWikiLLMClient."""

    def test_client_initialization(self):
        """Test client initialization with required parameters."""
        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )
        assert client.model == "gpt-4"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.api_key == "test-key"
        assert client.timeout_seconds == 30.0

    def test_base_url_trailing_slash_stripped(self):
        """Test that base_url trailing slash is removed."""
        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1/",
            api_key=None,
            timeout_seconds=30.0,
        )
        assert client.base_url == "https://api.openai.com/v1"

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_synthesize_page_calls_api(self, mock_post, page_def, facts, reflections):
        """Test that synthesize_page calls the API endpoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "# Карьера и навыки\n\nTest content with facts and reflections."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )
        result = client.synthesize_page(page_def, facts, reflections)

        # Verify API was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check endpoint (first positional argument)
        endpoint = call_args[0][0]
        assert "chat/completions" in endpoint

        # Check headers
        headers = call_args[1]["headers"]
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"

        # Check request body
        json_body = call_args[1]["json"]
        assert json_body["model"] == "gpt-4"
        assert len(json_body["messages"]) == 2
        assert json_body["messages"][0]["role"] == "system"
        assert json_body["messages"][1]["role"] == "user"

        # Check result
        assert isinstance(result, str)
        assert page_def.title in result

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_synthesize_page_with_existing_content(self, mock_post, page_def, facts, reflections):
        """Test synthesize_page with existing content in user message."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "# Title\n\nUpdated content."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )
        existing_content = "## Previous section\n\nOld content."
        client.synthesize_page(
            page_def, facts, reflections, existing_content=existing_content
        )

        # Check that existing_content was included in the request
        call_args = mock_post.call_args
        json_body = call_args[1]["json"]
        user_message = json_body["messages"][1]["content"]
        assert "Previous section" in user_message

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_synthesize_page_without_api_key(self, mock_post, page_def, facts, reflections):
        """Test synthesize_page without API key (public API)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "# Title\n\nContent."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key=None,
            timeout_seconds=30.0,
        )
        result = client.synthesize_page(page_def, facts, reflections)

        # Check headers - no Authorization header
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" not in headers

        assert isinstance(result, str)

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_synthesize_page_api_error(self, mock_post, page_def, facts, reflections):
        """Test that API errors are raised."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )

        with pytest.raises(Exception, match="API Error"):
            client.synthesize_page(page_def, facts, reflections)

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_synthesize_page_invalid_response(self, mock_post, page_def, facts, reflections):
        """Test error handling for invalid API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}  # Missing message

        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )

        with pytest.raises((IndexError, KeyError)):
            client.synthesize_page(page_def, facts, reflections)

    @patch("pipelines.wiki.wiki_llm_client.httpx.post")
    def test_user_message_includes_facts_and_reflections(self, mock_post, page_def, facts, reflections):
        """Test that user message includes facts and reflections as bullet points."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "# Title\n\nContent."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = OpenAICompatibleWikiLLMClient(
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout_seconds=30.0,
        )
        client.synthesize_page(page_def, facts, reflections)

        call_args = mock_post.call_args
        json_body = call_args[1]["json"]
        user_message = json_body["messages"][1]["content"]

        # Verify facts and reflections are in the message
        for fact in facts:
            assert fact in user_message or "fact" in user_message.lower()
        for reflection in reflections:
            assert reflection in user_message or "reflection" in user_message.lower()


class TestBuildWikiLLMClient:
    """Tests for build_wiki_llm_client function."""

    def test_build_raises_error_without_base_url(self):
        """Test that build_wiki_llm_client raises ValueError when base_url is missing."""
        # Create a mock settings object with no base_url
        mock_settings = MagicMock(spec=Settings)
        mock_settings.wiki_llm_base_url = None

        with pytest.raises(ValueError, match="WIKI_LLM_BASE_URL"):
            build_wiki_llm_client(mock_settings)

    def test_build_creates_openai_compatible_client(self):
        """Test that build_wiki_llm_client creates OpenAICompatibleWikiLLMClient."""
        # Use default settings which have valid values
        settings = Settings()

        client = build_wiki_llm_client(settings)

        assert isinstance(client, OpenAICompatibleWikiLLMClient)
        assert client.model == settings.wiki_llm_model
        assert client.base_url == settings.wiki_llm_base_url
        assert client.api_key == settings.wiki_llm_api_key
        assert client.timeout_seconds == settings.wiki_llm_timeout_seconds

    def test_build_uses_settings_values(self):
        """Test that build_wiki_llm_client uses values from settings."""
        # Create settings with defaults
        settings = Settings()

        client = build_wiki_llm_client(settings)

        # Verify all settings values are correctly passed to the client
        assert client.model == settings.wiki_llm_model
        assert client.base_url == settings.wiki_llm_base_url
        assert client.api_key == settings.wiki_llm_api_key
        assert client.timeout_seconds == settings.wiki_llm_timeout_seconds
