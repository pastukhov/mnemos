import pytest
from pydantic import ValidationError

from core.config import Settings
from pipelines.wiki.wiki_schema import WikiPageDefinition, WikiSchema


class TestWikiPageDefinition:
    """Test WikiPageDefinition model"""

    def test_valid_wiki_page(self):
        """Test creating a valid WikiPageDefinition"""
        page = WikiPageDefinition(
            name="career",
            title="Карьера и навыки",
            description="Профессиональный опыт",
            domains=["self"],
            kinds=["fact", "reflection"],
            themes=[],
        )
        assert page.name == "career"
        assert page.title == "Карьера и навыки"
        assert page.domains == ["self"]
        assert page.kinds == ["fact", "reflection"]
        assert page.themes == []

    def test_wiki_page_with_themes(self):
        """Test WikiPageDefinition with themes"""
        page = WikiPageDefinition(
            name="values",
            title="Ценности",
            description="Что важно",
            domains=["self"],
            kinds=["reflection"],
            themes=["motivation", "values"],
        )
        assert page.themes == ["motivation", "values"]

    def test_wiki_page_multiple_domains(self):
        """Test WikiPageDefinition with multiple domains"""
        page = WikiPageDefinition(
            name="decisions",
            title="Решения",
            description="Ключевые решения",
            domains=["self", "project"],
            kinds=["decision"],
            themes=[],
        )
        assert page.domains == ["self", "project"]

    def test_wiki_page_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError):
            WikiPageDefinition(
                name="incomplete",
                # missing title
                description="desc",
                domains=["self"],
                kinds=["fact"],
            )

    def test_wiki_page_themes_default_empty(self):
        """Test that themes defaults to empty list"""
        page = WikiPageDefinition(
            name="test",
            title="Test",
            description="Test page",
            domains=["self"],
            kinds=["fact"],
        )
        assert page.themes == []

    def test_wiki_page_rejects_reserved_navigation_names(self):
        with pytest.raises(ValidationError):
            WikiPageDefinition(
                name="index",
                title="Index",
                description="Reserved page",
                domains=["self"],
                kinds=["fact"],
            )


class TestWikiSchema:
    """Test WikiSchema model"""

    def test_valid_wiki_schema(self):
        """Test creating a valid WikiSchema"""
        schema = WikiSchema(
            pages=[
                WikiPageDefinition(
                    name="career",
                    title="Карьера",
                    description="Опыт",
                    domains=["self"],
                    kinds=["fact"],
                    themes=[],
                )
            ],
            output_dir="data/wiki",
            default_domain="self",
        )
        assert len(schema.pages) == 1
        assert schema.output_dir == "data/wiki"
        assert schema.default_domain == "self"

    def test_wiki_schema_default_output_dir(self):
        """Test default output_dir"""
        schema = WikiSchema(
            pages=[],
            default_domain="self",
        )
        assert schema.output_dir == "data/wiki"

    def test_wiki_schema_default_domain(self):
        """Test default default_domain"""
        schema = WikiSchema(pages=[])
        assert schema.default_domain == "self"

    def test_wiki_schema_empty_pages(self):
        """Test WikiSchema with empty pages list"""
        schema = WikiSchema(pages=[])
        assert schema.pages == []

    def test_wiki_schema_rejects_duplicate_page_names(self):
        with pytest.raises(ValidationError):
            WikiSchema(
                pages=[
                    WikiPageDefinition(
                        name="career",
                        title="Career",
                        description="One",
                        domains=["self"],
                        kinds=["fact"],
                    ),
                    WikiPageDefinition(
                        name="career",
                        title="Career 2",
                        description="Two",
                        domains=["self"],
                        kinds=["reflection"],
                    ),
                ]
            )

    def test_get_page_found(self):
        """Test get_page returns page when found"""
        career_page = WikiPageDefinition(
            name="career",
            title="Карьера",
            description="Опыт",
            domains=["self"],
            kinds=["fact"],
            themes=[],
        )
        schema = WikiSchema(pages=[career_page])
        found = schema.get_page("career")
        assert found is not None
        assert found.name == "career"

    def test_get_page_not_found(self):
        """Test get_page returns None when not found"""
        schema = WikiSchema(pages=[])
        found = schema.get_page("nonexistent")
        assert found is None

    def test_get_page_multiple_pages(self):
        """Test get_page with multiple pages"""
        pages = [
            WikiPageDefinition(
                name="career",
                title="Карьера",
                description="Опыт",
                domains=["self"],
                kinds=["fact"],
                themes=[],
            ),
            WikiPageDefinition(
                name="values",
                title="Ценности",
                description="Что важно",
                domains=["self"],
                kinds=["reflection"],
                themes=["motivation"],
            ),
        ]
        schema = WikiSchema(pages=pages)

        assert schema.get_page("career") is not None
        assert schema.get_page("values") is not None
        assert schema.get_page("unknown") is None


class TestWikiSchemaYAMLLoading:
    """Test loading WikiSchema from YAML"""

    def test_load_from_yaml_valid(self, tmp_path):
        """Test loading valid YAML"""
        yaml_file = tmp_path / "wiki_schema.yaml"
        yaml_content = """
output_dir: data/wiki
default_domain: self
pages:
  - name: career
    title: Карьера и навыки
    description: Профессиональный опыт, навыки, компетенции
    domains: [self]
    kinds: [fact, reflection]
    themes: []
  - name: values
    title: Ценности и мотивация
    description: Что движет тобой
    domains: [self]
    kinds: [reflection]
    themes: [motivation, values]
"""
        yaml_file.write_text(yaml_content, encoding="utf-8")

        schema = WikiSchema.load_from_yaml(str(yaml_file))

        assert schema.output_dir == "data/wiki"
        assert schema.default_domain == "self"
        assert len(schema.pages) == 2
        assert schema.pages[0].name == "career"
        assert schema.pages[1].name == "values"

    def test_load_from_yaml_with_custom_defaults(self, tmp_path):
        """Test loading YAML with custom defaults"""
        yaml_file = tmp_path / "wiki_schema.yaml"
        yaml_content = """
output_dir: custom/wiki
default_domain: project
pages:
  - name: test
    title: Test
    description: Test page
    domains: [project]
    kinds: [decision]
    themes: []
"""
        yaml_file.write_text(yaml_content, encoding="utf-8")

        schema = WikiSchema.load_from_yaml(str(yaml_file))

        assert schema.output_dir == "custom/wiki"
        assert schema.default_domain == "project"

    def test_load_from_yaml_nonexistent_file(self):
        """Test loading from nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            WikiSchema.load_from_yaml("/nonexistent/path/wiki_schema.yaml")

    def test_load_from_yaml_empty_pages(self, tmp_path):
        """Test loading YAML with empty pages list"""
        yaml_file = tmp_path / "wiki_schema.yaml"
        yaml_content = """
output_dir: data/wiki
default_domain: self
pages: []
"""
        yaml_file.write_text(yaml_content, encoding="utf-8")

        schema = WikiSchema.load_from_yaml(str(yaml_file))

        assert schema.pages == []

    def test_load_from_yaml_minimal(self, tmp_path):
        """Test loading minimal YAML with only pages"""
        yaml_file = tmp_path / "wiki_schema.yaml"
        yaml_content = """
pages:
  - name: career
    title: Карьера
    description: Опыт
    domains: [self]
    kinds: [fact]
"""
        yaml_file.write_text(yaml_content, encoding="utf-8")

        schema = WikiSchema.load_from_yaml(str(yaml_file))

        assert schema.output_dir == "data/wiki"  # default
        assert schema.default_domain == "self"   # default
        assert len(schema.pages) == 1

    def test_load_from_yaml_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML syntax"""
        yaml_file = tmp_path / "wiki_schema.yaml"
        yaml_file.write_text("invalid: yaml: syntax: [", encoding="utf-8")

        with pytest.raises(Exception):  # Could be YAMLError or similar
            WikiSchema.load_from_yaml(str(yaml_file))


class TestWikiSettings:
    """Test Wiki-related Settings"""

    def test_wiki_settings_defaults(self):
        """Test wiki settings have correct defaults"""
        settings = Settings()

        assert settings.wiki_schema_path == "data/wiki_schema.yaml"
        assert settings.wiki_llm_timeout_seconds == 20.0
        assert settings.wiki_max_page_chars == 5000
        assert settings.wiki_min_facts_per_page == 3
        assert settings.pipeline_worker_enabled is True
        assert settings.pipeline_worker_interval_seconds == 60.0

    def test_wiki_llm_defaults_to_reflection(self):
        """Test that wiki LLM settings default to reflection LLM"""
        settings = Settings()

        # Wiki LLM should match reflection LLM by default
        assert settings.wiki_llm_model == settings.reflection_llm_model
        assert settings.wiki_llm_base_url == settings.reflection_llm_base_url
        assert settings.wiki_llm_api_key == settings.reflection_llm_api_key

    def test_wiki_custom_settings(self):
        """Test wiki settings can be customized via env vars"""
        import os

        os.environ["WIKI_SCHEMA_PATH"] = "custom/schema.yaml"
        os.environ["WIKI_MAX_PAGE_CHARS"] = "10000"
        os.environ["WIKI_MIN_FACTS_PER_PAGE"] = "5"

        try:
            settings = Settings()
            assert settings.wiki_schema_path == "custom/schema.yaml"
            assert settings.wiki_max_page_chars == 10000
            assert settings.wiki_min_facts_per_page == 5
        finally:
            # Clean up
            for key in ["WIKI_SCHEMA_PATH", "WIKI_MAX_PAGE_CHARS", "WIKI_MIN_FACTS_PER_PAGE"]:
                os.environ.pop(key, None)
