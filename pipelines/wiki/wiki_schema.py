from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class WikiPageDefinition(BaseModel):
    """Definition of a wiki page to be generated"""

    name: str = Field(min_length=1, description="Page identifier (e.g., 'career')")
    title: str = Field(min_length=1, description="Page title (e.g., 'Карьера и навыки')")
    description: str = Field(min_length=1, description="Brief page description")
    domains: list[str] = Field(description="Filter by domains (e.g., ['self'], ['project'])")
    kinds: list[str] = Field(description="Filter by memory item kinds (e.g., ['fact', 'reflection'])")
    themes: list[str] = Field(default_factory=list, description="Optional themes (e.g., ['motivation'])")


class WikiSchema(BaseModel):
    """Schema for wiki generation configuration"""

    pages: list[WikiPageDefinition] = Field(description="List of wiki pages to generate")
    output_dir: str = Field(default="data/wiki", description="Directory for wiki output")
    default_domain: str = Field(default="self", description="Default domain for filtering")

    def get_page(self, name: str) -> WikiPageDefinition | None:
        """Get a page definition by name"""
        for page in self.pages:
            if page.name == name:
                return page
        return None

    @classmethod
    def load_from_yaml(cls, path: str) -> "WikiSchema":
        """Load WikiSchema from YAML file"""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Wiki schema file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        return cls(**data)
