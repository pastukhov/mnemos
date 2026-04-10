"""Tests for wiki CLI commands."""

from unittest.mock import MagicMock, patch

from cli import (
    run_wiki_build_command,
    run_wiki_lint_command,
    run_wiki_query_command,
)


class MockWikiReport:
    """Mock wiki build report."""

    def __init__(self, pages_built=1, pages_updated=0, pages_skipped=0, errors=0):
        self.pages_built = pages_built
        self.pages_updated = pages_updated
        self.pages_skipped = pages_skipped
        self.errors = errors

    def render(self) -> str:
        """Render report as string."""
        lines = [
            f"Pages built: {self.pages_built}",
            f"Pages updated: {self.pages_updated}",
            f"Pages skipped: {self.pages_skipped}",
        ]
        if self.errors:
            lines.append(f"Errors: {self.errors}")
        return "\n".join(lines)


def test_wiki_build_command_creates_pages(capsys):
    """Test wiki build command successfully creates pages."""
    # Arrange
    args = MagicMock()
    args.domain = None
    args.page = None

    parser = MagicMock()

    settings = MagicMock()
    settings.postgres_dsn = "postgresql://user:pass@localhost/db"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_vector_size = 1536
    settings.qdrant_timeout_seconds = 5.0
    settings.wiki_schema_path = "data/wiki_schema.yaml"

    # Mock all the dependencies
    with patch("cli.create_engine"):
        with patch("cli.create_session_factory"):
            with patch("cli.MnemosQdrantClient"):
                with patch("cli.build_embedder"):
                    with patch("cli.MemoryService"):
                        with patch("cli.build_wiki_llm_client"):
                            with patch("cli.WikiBuildRunner") as mock_runner_class:
                                # Setup mocks
                                mock_report = MockWikiReport(
                                    pages_built=1,
                                    pages_updated=0,
                                    pages_skipped=0,
                                )
                                mock_runner_instance = MagicMock()
                                mock_runner_instance.run.return_value = mock_report
                                mock_runner_class.return_value = mock_runner_instance

                                # Act
                                result = run_wiki_build_command(args, parser, settings)

                                # Assert
                                assert result == 0
                                mock_runner_instance.run.assert_called_once_with(
                                    domain=None,
                                    page_name=None,
                                )
                                captured = capsys.readouterr()
                                assert "Pages built: 1" in captured.out
                                assert "Pages updated: 0" in captured.out
                                assert "Pages skipped: 0" in captured.out


def test_wiki_build_with_domain_filter(capsys):
    """Test wiki build command with domain filter."""
    # Arrange
    args = MagicMock()
    args.domain = "self"
    args.page = None

    parser = MagicMock()

    settings = MagicMock()
    settings.postgres_dsn = "postgresql://user:pass@localhost/db"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_vector_size = 1536
    settings.qdrant_timeout_seconds = 5.0
    settings.wiki_schema_path = "data/wiki_schema.yaml"

    # Mock all the dependencies
    with patch("cli.create_engine"):
        with patch("cli.create_session_factory"):
            with patch("cli.MnemosQdrantClient"):
                with patch("cli.build_embedder"):
                    with patch("cli.MemoryService"):
                        with patch("cli.build_wiki_llm_client"):
                            with patch("cli.WikiBuildRunner") as mock_runner_class:
                                # Setup mocks
                                mock_report = MockWikiReport(pages_built=2)
                                mock_runner_instance = MagicMock()
                                mock_runner_instance.run.return_value = mock_report
                                mock_runner_class.return_value = mock_runner_instance

                                # Act
                                result = run_wiki_build_command(args, parser, settings)

                                # Assert
                                assert result == 0
                                mock_runner_instance.run.assert_called_once_with(
                                    domain="self",
                                    page_name=None,
                                )


def test_wiki_build_with_page_filter(capsys):
    """Test wiki build command with specific page filter."""
    # Arrange
    args = MagicMock()
    args.domain = None
    args.page = "career"

    parser = MagicMock()

    settings = MagicMock()
    settings.postgres_dsn = "postgresql://user:pass@localhost/db"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_vector_size = 1536
    settings.qdrant_timeout_seconds = 5.0
    settings.wiki_schema_path = "data/wiki_schema.yaml"

    # Mock all the dependencies
    with patch("cli.create_engine"):
        with patch("cli.create_session_factory"):
            with patch("cli.MnemosQdrantClient"):
                with patch("cli.build_embedder"):
                    with patch("cli.MemoryService"):
                        with patch("cli.build_wiki_llm_client"):
                            with patch("cli.WikiBuildRunner") as mock_runner_class:
                                # Setup mocks
                                mock_report = MockWikiReport(pages_built=1)
                                mock_runner_instance = MagicMock()
                                mock_runner_instance.run.return_value = mock_report
                                mock_runner_class.return_value = mock_runner_instance

                                # Act
                                result = run_wiki_build_command(args, parser, settings)

                                # Assert
                                assert result == 0
                                mock_runner_instance.run.assert_called_once_with(
                                    domain=None,
                                    page_name="career",
                                )


def test_wiki_lint_command_not_implemented(capsys):
    """Test wiki lint command outputs not implemented message."""
    # Arrange
    args = MagicMock()
    args.domain = None
    args.fix = False

    parser = MagicMock()
    settings = MagicMock()

    # Act
    result = run_wiki_lint_command(args, parser, settings)

    # Assert
    assert result == 0
    captured = capsys.readouterr()
    assert "Wiki lint not yet implemented" in captured.out
    assert "Phase 7.6" in captured.out


def test_wiki_query_command_not_implemented(capsys):
    """Test wiki query command outputs not implemented message."""
    # Arrange
    args = MagicMock()
    args.question = "What is my career path?"
    args.domain = None

    parser = MagicMock()
    settings = MagicMock()

    # Act
    result = run_wiki_query_command(args, parser, settings)

    # Assert
    assert result == 0
    captured = capsys.readouterr()
    assert "Wiki query not yet implemented" in captured.out
    assert "Phase 7.7" in captured.out
