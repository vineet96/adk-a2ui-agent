"""
Retail Product Search Agent — ADK 2.0 + Gemini + A2UI v0.9
===========================================================
Deployed to Vertex AI Agent Engine via:
    adk deploy agent_engine --project=... --region=... retail_agent

Local development:
    adk run retail_agent
    adk web retail_agent
"""

import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# ── Model ─────────────────────────────────────────────────────────────────────
# On Agent Engine, authentication is via the project service account.
# GOOGLE_GENAI_USE_VERTEXAI=true in .env routes calls through Vertex AI.
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

# ── Tool ─────────────────────────────────────────────────────────────────────
def search_products(query: str, category: str = "all", max_results: int = 5) -> dict:
    """
    Search for products matching the query.

    Args:
        query:       Natural language search query (e.g. "wireless headphones")
        category:    Filter by category: electronics, clothing, home, all
        max_results: Maximum number of results to return (1-10)

    Returns:
        Dictionary with matching products list and metadata.
    """
    CATALOG = [
        {"id": "e1", "name": "Sony WH-1000XM5 Headphones", "price": "$349.99",
         "category": "electronics", "rating": 4.8, "stock": 12},
        {"id": "e2", "name": "Apple AirPods Pro 2nd Gen", "price": "$249.00",
         "category": "electronics", "rating": 4.7, "stock": 45},
        {"id": "e3", "name": "Samsung Galaxy Buds2 Pro", "price": "$149.99",
         "category": "electronics", "rating": 4.5, "stock": 28},
        {"id": "e4", "name": "Bose QuietComfort 45", "price": "$279.00",
         "category": "electronics", "rating": 4.6, "stock": 7},
        {"id": "c1", "name": "Patagonia Nano Puff Jacket", "price": "$229.00",
         "category": "clothing", "rating": 4.9, "stock": 15},
        {"id": "c2", "name": "Levis 501 Original Jeans", "price": "$89.50",
         "category": "clothing", "rating": 4.4, "stock": 60},
        {"id": "h1", "name": "Instant Pot Duo 7-in-1", "price": "$99.95",
         "category": "home", "rating": 4.7, "stock": 32},
        {"id": "h2", "name": "Dyson V15 Detect Vacuum", "price": "$749.99",
         "category": "home", "rating": 4.8, "stock": 5},
    ]
    q = query.lower()
    results = [
        p for p in CATALOG
        if (category == "all" or p["category"] == category)
        and any(kw in p["name"].lower() for kw in q.split())
    ]
    if not results:
        results = [p for p in CATALOG
                   if category == "all" or p["category"] == category]
    return {
        "products": results[:max_results],
        "total": len(results[:max_results]),
        "query": query,
    }


# ── System prompt ─────────────────────────────────────────────────────────────
A2UI_INSTRUCTION = """
You are a helpful product search assistant for a retail store.

When a user asks about products, you MUST:

1. Call the search_products tool to retrieve real product data.
2. Wrap your ENTIRE response in <a2ui-json> ... </a2ui-json> tags.
3. Inside those tags, output ONLY a valid JSON array of exactly 3 A2UI v0.9 messages.

The 3 messages must always be in this order:

MESSAGE 1 - createSurface:
{
  "version": "v0.9",
  "createSurface": {
    "surfaceId": "products",
    "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"
  }
}

MESSAGE 2 - updateComponents:
Build one Card per product. Use {"path": "/products/N/field"} for all
data-bound values — never hardcode values from the tool result.
Component types allowed: Column, List, Card, Text, Button, Divider.

MESSAGE 3 - updateDataModel:
{
  "version": "v0.9",
  "updateDataModel": {
    "surfaceId": "products",
    "path": "/",
    "value": { "products": [...tool results here...], "query": "..." }
  }
}

STRICT RULES:
- Do NOT hardcode product names or prices in updateComponents.
  Always use {"path": "/products/N/name"} style bindings.
- Output valid JSON only — no trailing commas, no comments.
- Do NOT write anything outside the <a2ui-json> block.
- Every Button must have an action.event with name and context.
"""

# ── Agent ─────────────────────────────────────────────────────────────────────
# root_agent is the entry point ADK CLI looks for at module level.
root_agent = LlmAgent(
    name="retail_search_agent",
    model=MODEL,
    description="Retail product search agent returning A2UI v0.9 generative UI.",
    instruction=A2UI_INSTRUCTION,
    tools=[FunctionTool(func=search_products)],
)
