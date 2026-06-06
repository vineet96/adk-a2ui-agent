"""
Retail Product Search Agent — ADK 2.0 + Gemini + A2UI v0.9
"""

import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# gemini-2.0-flash: faster response, lower latency — better for Agent Engine
# where the default timeout can cut off slower gemini-2.5-flash tool+JSON calls.
# Switch back to gemini-2.5-flash via MODEL env var once confirmed working.
MODEL = os.environ.get("MODEL", "gemini-2.0-flash")


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


# ── Instructions ──────────────────────────────────────────────────────────────

INSTRUCTION_PLAIN = """
You are a helpful retail product search assistant.
When a user asks about products, call search_products to find items,
then respond with a clear list including name, price, and rating.
Keep your response concise and friendly.
"""

INSTRUCTION_A2UI = """
You are a helpful retail product search assistant.
When a user asks about products:

1. Call search_products to get real product data.
2. Return your ENTIRE response wrapped in <a2ui-json> tags like this:

<a2ui-json>
[
  {
    "version": "v0.9",
    "createSurface": {
      "surfaceId": "products",
      "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"
    }
  },
  {
    "version": "v0.9",
    "updateComponents": {
      "surfaceId": "products",
      "components": [
        {"id": "root", "component": "Column", "children": ["title", "list"]},
        {"id": "title", "component": "Text", "text": "Search Results", "variant": "h1"},
        {"id": "list", "component": "List", "children": ["card-0", "card-1"]},
        {"id": "card-0", "component": "Card", "children": ["name-0", "price-0"]},
        {"id": "name-0", "component": "Text", "text": {"path": "/products/0/name"}, "variant": "h3"},
        {"id": "price-0", "component": "Text", "text": {"path": "/products/0/price"}, "variant": "caption"},
        {"id": "card-1", "component": "Card", "children": ["name-1", "price-1"]},
        {"id": "name-1", "component": "Text", "text": {"path": "/products/1/name"}, "variant": "h3"},
        {"id": "price-1", "component": "Text", "text": {"path": "/products/1/price"}, "variant": "caption"}
      ]
    }
  },
  {
    "version": "v0.9",
    "updateDataModel": {
      "surfaceId": "products",
      "path": "/",
      "value": {
        "products": [],
        "query": ""
      }
    }
  }
]
</a2ui-json>

Fill updateDataModel.value.products with the REAL products from search_products.
Fill updateDataModel.value.query with the user's search term.
Add one card-N block per product in updateComponents.
Use {"path": "/products/N/name"} — never hardcode product names in components.
Output NOTHING outside the <a2ui-json> tags. JSON must be valid.
"""

# ── Active instruction ────────────────────────────────────────────────────────
# Set to INSTRUCTION_PLAIN first to verify end-to-end, then switch to A2UI.
ACTIVE_INSTRUCTION = INSTRUCTION_A2UI

root_agent = LlmAgent(
    name="retail_search_agent",
    model=MODEL,
    description="Retail product search agent.",
    instruction=ACTIVE_INSTRUCTION,
    tools=[FunctionTool(func=search_products)],
)
