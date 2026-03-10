"""Scryfall MCP Server."""

from fastmcp import FastMCP

from .models import CardResult, CollectionResult, RulingsResult, SearchResults
from .tools.cards import card_by_id, card_by_name, search
from .tools.collection import collection_lookup
from .tools.rulings import rulings_lookup

mcp = FastMCP(
    name="scryfall",
    instructions="""Scryfall MCP Server for MTG card data.

Provides structured access to Scryfall's card database with response caching.
Use these tools to look up card details, search for cards, verify card names,
and check rulings.

Available tools:
- scryfall_card_by_name: Look up a single card by name (fuzzy or exact)
- scryfall_search: Search using Scryfall syntax (e.g., "t:creature c:green cmc<=3")
- scryfall_collection: Bulk lookup multiple cards by name
- scryfall_card_by_id: Look up by Scryfall UUID
- scryfall_rulings: Get rulings for a card

Scryfall search syntax examples:
- t:creature — type contains "creature"
- c:green — color includes green
- ci:boros — color identity within Boros (RW)
- cmc<=3 — mana value 3 or less
- o:"draw a card" — oracle text contains phrase
- set:mkm — from a specific set
- f:commander — legal in Commander
- is:dfc — double-faced cards
- name:/^lightning/ — regex card name
""",
)


@mcp.tool()
async def scryfall_card_by_name(name: str, exact: bool = False) -> CardResult:
    """Look up a Magic card by name.

    Use fuzzy matching (default) when unsure of exact spelling.
    Use exact=True for precise lookups.

    Args:
        name: Card name to search for.
        exact: If True, require exact name match. Default False (fuzzy).

    Returns:
        CardResult with full card data.
    """
    return await card_by_name(name, exact)


@mcp.tool()
async def scryfall_search(
    query: str, order: str = "name", max_results: int = 20
) -> SearchResults:
    """Search for cards using Scryfall search syntax.

    Args:
        query: Scryfall search query (e.g., "t:creature c:green cmc<=3 f:commander").
        order: Sort order — name, set, released, rarity, color, usd, eur, edhrec.
        max_results: Maximum cards to return (default 20).

    Returns:
        SearchResults with matching cards.
    """
    return await search(query, order, max_results)


@mcp.tool()
async def scryfall_collection(card_names: list[str]) -> CollectionResult:
    """Look up multiple cards by name in a single call.

    Efficient for validating decklists or fetching data for many cards.
    Batches into groups of 75 (Scryfall limit). Results are cached individually.

    Args:
        card_names: List of card names to look up.

    Returns:
        CollectionResult with found cards and not_found names.
    """
    return await collection_lookup(card_names)


@mcp.tool()
async def scryfall_card_by_id(scryfall_id: str) -> CardResult:
    """Look up a card by its Scryfall UUID.

    Args:
        scryfall_id: Scryfall UUID for the card.

    Returns:
        CardResult with full card data.
    """
    return await card_by_id(scryfall_id)


@mcp.tool()
async def scryfall_rulings(scryfall_id: str, card_name: str = "") -> RulingsResult:
    """Get official rulings for a card.

    Args:
        scryfall_id: Scryfall UUID for the card.
        card_name: Optional card name (for display in results).

    Returns:
        RulingsResult with list of rulings.
    """
    return await rulings_lookup(scryfall_id, card_name)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
