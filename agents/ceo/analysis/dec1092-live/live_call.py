import asyncio, json, os, sqlite3, subprocess, sys, time
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader"
cfg = json.load(open(f"{ROOT}/.mcp.json"))["mcpServers"]["scryfall"]
CACHE = "/Users/dpires/.cache/scryfall-mcp"

def ls(p):
    try:
        return sorted((n, os.stat(os.path.join(p, n)).st_size) for n in os.listdir(p))
    except FileNotFoundError as e:
        return str(e)

async def main():
    env = dict(os.environ)
    env.update(cfg.get("env", {}))
    t = StdioTransport(command=cfg["command"], args=cfg["args"], env=env, cwd=ROOT)
    async with Client(t) as c:
        tools = sorted(x.name for x in await c.list_tools())
        print("tools:", tools)
        print("server pid check: env XDG_CACHE_HOME =", env["XDG_CACHE_HOME"], "SCRYFALL_LIMIT_DIR =", env["SCRYFALL_LIMIT_DIR"])
        t0 = time.time()
        r = await c.call_tool("scryfall_card_by_name", {"name": "Sol Ring"}, raise_on_error=False)
        t1 = time.time()
        print(f"call start {t0:.3f} end {t1:.3f}")
        print("isError:", r.is_error)
        text = "".join(getattr(b, "text", "") for b in r.content)
        print("text (first 400 chars):", text[:400].replace("\n", " | "))
        try:
            st = json.load(open(f"{env['SCRYFALL_LIMIT_DIR']}/state.json"))
            print("state.json:", st)
            for k in ("last_answer", "last_slow_answer"):
                if k in st:
                    print(f"  {k} - call end = {st[k] - t1:+.3f} s")
        except Exception as e:
            print("state.json:", repr(e))
        print("limit dir:", ls(env["SCRYFALL_LIMIT_DIR"]))
        print("cache dir while the server runs:", ls(CACHE))
        con = sqlite3.connect(f"file:{CACHE}/cards.db?mode=ro", uri=True)
        print("journal_mode:", con.execute("PRAGMA journal_mode").fetchone()[0])
        con.close()
    print("cache dir after the server ended:", ls(CACHE))

asyncio.run(main())
