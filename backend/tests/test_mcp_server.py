"""The MCP server: read-only evidence tools with the web app's safety rules."""
from __future__ import annotations

import asyncio
import json

from app.agents.citations import policy_violations


def _call(tool: str, args: dict) -> dict:
    from app.mcp_server import mcp

    result = asyncio.run(mcp.call_tool(tool, args))
    assert not result.is_error, result.content
    return result.structured_content or json.loads(result.content[0].text)


def test_only_read_only_evidence_tools_are_exposed(client):
    from app.mcp_server import mcp

    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(tools) == {"search_hair_evidence", "ask_hair_question", "list_sources"}
    assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools.values())


def test_search_returns_licensed_passages(client):
    r = _call("search_hair_evidence", {"query": "how many hairs do people normally shed each day", "k": 3})
    assert 1 <= len(r["results"]) <= 3
    assert all(x["url"].startswith("https://") and x["license"] and x["passage"] for x in r["results"])
    assert [x["rank"] for x in r["results"]] == list(range(1, len(r["results"]) + 1))


def test_ask_is_cited_and_verified(client):
    r = _call("ask_hair_question", {"question": "How many hairs a day is normal to lose?"})
    assert r["verified"] and r["citations"]
    assert all(c["url"] and c["license"] for c in r["citations"])


def test_ask_keeps_the_dose_guardrail(client):
    r = _call("ask_hair_question", {"question": "How many mg of finasteride should I take?"})
    assert r["answer"].startswith("HairGPT does not give doses")
    assert "dosing" not in policy_violations(r["answer"])


def test_sources_and_safety_policy(client):
    from app.mcp_server import mcp

    sources = _call("list_sources", {})
    assert sources["count"] == len(sources["documents"]) > 0
    policy = "".join(part.content for part in asyncio.run(mcp.read_resource("hairgpt://safety-policy")))
    assert "No doses" in policy and "not diagnosis" in policy
