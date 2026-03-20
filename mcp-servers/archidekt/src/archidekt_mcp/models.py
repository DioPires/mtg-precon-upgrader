"""Pydantic models for Archidekt MCP tools."""

from pydantic import BaseModel, Field


class ArchidektDeckSummary(BaseModel):
    """Summary of a deck from list endpoint."""

    id: int = Field(description="Archidekt deck ID")
    name: str = Field(description="Deck name")
    owner: str = Field(default="", description="Owner username")
    format: str = Field(default="commander", description="Deck format")
    card_count: int = Field(default=0, description="Number of cards")
    updated_at: str = Field(default="", description="Last updated timestamp")
    url: str = Field(default="", description="Archidekt deck URL")


class ListDecksResponse(BaseModel):
    """Response from archidekt_list_decks."""

    username: str = Field(description="Profile username")
    decks: list[ArchidektDeckSummary] = Field(description="Decks on the profile")
    total: int = Field(description="Total deck count")


class CardResolutionResult(BaseModel):
    """Result of resolving a card name to Scryfall ID."""

    name: str = Field(description="Card name")
    scryfall_id: str = Field(default="", description="Scryfall printing UUID")
    resolved: bool = Field(default=False, description="Whether resolution succeeded")
    error: str = Field(default="", description="Error message if failed")


class PublishDeckResult(BaseModel):
    """Result of publishing a deck to Archidekt."""

    deck_id: str = Field(description="Deck ID on Archidekt or 'dry-run'")
    name: str = Field(description="Deck name")
    card_count: int = Field(description="Number of cards published")
    commander: str = Field(description="Commander name")
    url: str = Field(default="", description="Archidekt deck URL")
    created: bool = Field(default=False, description="True if new deck was created")
    updated: bool = Field(default=False, description="True if existing deck was updated")
    dry_run: bool = Field(default=False, description="True if this was a dry run")
    errors: list[str] = Field(default_factory=list, description="Card resolution errors")


class SyncResult(BaseModel):
    """Result of syncing a single deck."""

    deck_id_local: str = Field(description="Local deck ID (from deck.json)")
    deck_name: str = Field(description="Deck name")
    status: str = Field(description="'published', 'skipped', 'error', or 'dry-run'")
    archidekt_id: str = Field(default="", description="Archidekt deck ID")
    url: str = Field(default="", description="Archidekt deck URL")
    error: str = Field(default="", description="Error message if failed")


class SyncAllResponse(BaseModel):
    """Response from archidekt_sync_all."""

    results: list[SyncResult] = Field(description="Per-deck sync results")
    total: int = Field(description="Total decks processed")
    published: int = Field(description="Decks successfully published")
    errors: int = Field(description="Decks with errors")
    skipped: int = Field(description="Decks skipped")
