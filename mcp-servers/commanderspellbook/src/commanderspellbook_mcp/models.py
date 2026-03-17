"""Pydantic response models for Commander Spellbook MCP tools."""

from pydantic import BaseModel, Field


class CardInCombo(BaseModel):
    """A card used in a combo."""

    name: str = Field(description="Card name")
    quantity: int = Field(default=1, description="Number needed")
    zone_locations: list[str] = Field(
        default_factory=list,
        description="Required zones (B=battlefield, H=hand, G=graveyard, L=library, C=command zone, E=exile)",
    )
    battlefield_card_state: str = Field(
        default="", description="Required battlefield state"
    )
    must_be_commander: bool = Field(
        default=False, description="Must be cast as commander"
    )


class TemplateRequirement(BaseModel):
    """A generic card requirement (e.g., 'any creature with persist')."""

    name: str = Field(description="Template name")
    scryfall_query: str = Field(default="", description="Scryfall search query to find matching cards")
    zone_locations: list[str] = Field(default_factory=list, description="Required zones")


class ComboResult(BaseModel):
    """A single combo from Commander Spellbook."""

    id: str = Field(description="Combo ID (e.g., '628-2292--5')")
    url: str = Field(description="Commander Spellbook combo page URL")
    status: str = Field(default="OK", description="Combo status")
    identity: str = Field(default="", description="Color identity")
    bracket_tag: str = Field(default="", description="Bracket tag")
    cards: list[CardInCombo] = Field(description="Specific cards used in the combo")
    requires: list[TemplateRequirement] = Field(
        default_factory=list,
        description="Generic card requirements (templates)",
    )
    produces: list[str] = Field(description="What the combo produces (e.g., 'Infinite ETB')")
    description: str = Field(default="", description="Step-by-step combo description")
    mana_needed: str = Field(default="", description="Mana required to start")
    easy_prerequisites: str = Field(default="", description="Simple prerequisites")
    notable_prerequisites: str = Field(default="", description="Complex prerequisites")
    notes: str = Field(default="", description="Additional notes")


class AlmostIncludedResult(BaseModel):
    """A combo that's 1-2 cards away from being in the deck."""

    combo: ComboResult = Field(description="The combo details")
    missing_cards: list[str] = Field(
        description="Card names from the combo not in the submitted decklist"
    )
    missing_templates: list[str] = Field(
        default_factory=list,
        description="Template requirements that must be fulfilled",
    )


class FindCombosResponse(BaseModel):
    """Response from find-my-combos API."""

    identity: str = Field(description="Deck color identity")
    included: list[ComboResult] = Field(description="Combos fully enabled by the decklist")
    almost_included: list[AlmostIncludedResult] = Field(
        description="Combos 1-2 cards away from being enabled"
    )
