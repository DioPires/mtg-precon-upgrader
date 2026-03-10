"""Pydantic response models for Scryfall MCP tools."""

from pydantic import BaseModel, Field, model_validator


class CardResult(BaseModel):
    """A single card result from Scryfall."""

    name: str = Field(description="Card name")
    mana_cost: str = Field(default="", description="Mana cost string (e.g., '{2}{U}{U}')")
    cmc: float = Field(default=0, description="Converted mana cost")
    type_line: str = Field(default="", description="Full type line")
    oracle_text: str = Field(default="", description="Oracle text (DFC: front // back merged)")
    colors: list[str] = Field(default_factory=list, description="Card colors")
    color_identity: list[str] = Field(default_factory=list, description="Color identity")
    power: str | None = Field(default=None, description="Power (creatures only)")
    toughness: str | None = Field(default=None, description="Toughness (creatures only)")
    set_code: str = Field(default="", description="Set code")
    image_uris: dict | None = Field(default=None, description="Image URIs by size")
    scryfall_uri: str = Field(default="", description="Scryfall page URL")
    legalities: dict = Field(default_factory=dict, description="Format legality map")
    keywords: list[str] = Field(default_factory=list, description="Keyword abilities")
    card_faces: list[dict] | None = Field(default=None, description="Per-face data for DFC/split/adventure")
    scryfall_id: str = Field(default="", description="Scryfall UUID")

    @model_validator(mode="before")
    @classmethod
    def merge_dfc_oracle_text(cls, data: dict) -> dict:
        """Merge oracle text from card faces for DFC/split cards."""
        if isinstance(data, dict) and data.get("card_faces") and not data.get("oracle_text"):
            faces = data["card_faces"]
            texts = [f.get("oracle_text", "") for f in faces if f.get("oracle_text")]
            if texts:
                data["oracle_text"] = " // ".join(texts)
        return data


class SearchResults(BaseModel):
    """Results from a Scryfall search."""

    total_cards: int = Field(description="Total cards matching query")
    results: list[CardResult] = Field(description="Card results")


class CollectionResult(BaseModel):
    """Results from a bulk collection lookup."""

    found: list[CardResult] = Field(description="Cards found")
    not_found: list[str] = Field(description="Card names not found")


class RulingEntry(BaseModel):
    """A single ruling for a card."""

    source: str = Field(description="Ruling source (wotc or scryfall)")
    published_at: str = Field(description="Date published")
    comment: str = Field(description="Ruling text")


class RulingsResult(BaseModel):
    """Rulings for a card."""

    card_name: str = Field(description="Card name")
    rulings: list[RulingEntry] = Field(description="List of rulings")
