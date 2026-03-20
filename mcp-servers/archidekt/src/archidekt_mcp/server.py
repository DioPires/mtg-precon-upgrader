"""Archidekt MCP Server."""

from fastmcp import FastMCP

from .models import ListDecksResponse, PublishDeckResult, SyncAllResponse
from .tools.decks import list_decks as _list_decks
from .tools.decks import publish_deck as _publish_deck
from .tools.decks import sync_all as _sync_all

mcp = FastMCP(
    name="archidekt",
    instructions="""Archidekt MCP Server for publishing deck data.

Syncs deck.json files from The Grimoire to the Archidekt profile.

Available tools:
- archidekt_list_decks: List decks on the Archidekt profile
- archidekt_publish_deck: Create or update a single deck on Archidekt
- archidekt_sync_all: Sync all deck.json files to Archidekt

Auth: Set ARCHIDEKT_AUTH_TOKEN env var for write operations.
Read operations (list_decks) work without auth.
""",
)


@mcp.tool()
async def archidekt_list_decks(
    username: str = "",
) -> ListDecksResponse:
    """List decks on an Archidekt profile.

    Args:
        username: Archidekt username. Defaults to ARCHIDEKT_USERNAME env var.

    Returns:
        ListDecksResponse with deck summaries.
    """
    return await _list_decks(username or None)


@mcp.tool()
async def archidekt_publish_deck(
    deck_id: str,
    archidekt_deck_id: int = 0,
    dry_run: bool = False,
) -> PublishDeckResult:
    """Publish a deck.json to Archidekt (create or update).

    Resolves all card names to Scryfall IDs, builds the Archidekt
    payload, and creates or updates the deck.

    Args:
        deck_id: Local deck ID (e.g., 'titan-convergence').
        archidekt_deck_id: Existing Archidekt deck ID to update. 0 = create new.
        dry_run: If True, resolve cards but don't actually publish.

    Returns:
        PublishDeckResult with publication status.
    """
    return await _publish_deck(
        deck_id,
        archidekt_deck_id if archidekt_deck_id > 0 else None,
        dry_run,
    )


@mcp.tool()
async def archidekt_sync_all(
    dry_run: bool = False,
) -> SyncAllResponse:
    """Sync all deck.json files to Archidekt.

    Iterates through all commanders in data/index.json and publishes
    each deck. Uses known Archidekt IDs for updates, creates new
    decks for unknown IDs.

    Args:
        dry_run: If True, resolve cards but don't publish.

    Returns:
        SyncAllResponse with per-deck results.
    """
    return await _sync_all(dry_run)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
