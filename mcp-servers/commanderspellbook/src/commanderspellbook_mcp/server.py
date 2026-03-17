"""Commander Spellbook MCP Server."""

from fastmcp import FastMCP

from .models import FindCombosResponse
from .tools.combos import find_combos as _find_combos

mcp = FastMCP(
    name="commanderspellbook",
    instructions="""Commander Spellbook MCP Server for MTG combo lookup.

Queries Commander Spellbook's find-my-combos API to identify combos
in a decklist and combos that are 1-2 cards away.

Available tools:
- commanderspellbook_find_combos: Find included and near-miss combos for a decklist

Response includes:
- included: Combos fully enabled by the decklist
- almost_included: Combos 1-2 cards away, with missing_cards and missing_templates

Combo URLs link to https://commanderspellbook.com/combo/{id}/
""",
)


@mcp.tool()
async def commanderspellbook_find_combos(decklist: list[str]) -> FindCombosResponse:
    """Find combos in a decklist using Commander Spellbook.

    Pass the full decklist (card names, one per entry). Returns combos
    that are fully enabled (included) and combos that are 1-2 cards away
    (almost_included) with the missing card names identified.

    Args:
        decklist: List of card names in the deck.

    Returns:
        FindCombosResponse with included combos and near-miss combos.
    """
    return await _find_combos(decklist)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
