"""
Firestore MCP Server
A simple MCP server exposing Firestore read/write tools to an agent.

Dependencies:
    pip install mcp firebase-admin

Authentication:
    Set GOOGLE_APPLICATION_CREDENTIALS env var to your service account JSON path,
    or call firebase_admin.initialize_app() with explicit credentials.
"""

import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ---------------------------------------------------------------------------
# Firebase initialisation
# ---------------------------------------------------------------------------

cred = credentials.ApplicationDefault()          # uses GOOGLE_APPLICATION_CREDENTIALS
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

server = Server("firestore-mcp")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="firestore_get_document",
            description="Read a single document from Firestore by collection and document ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Firestore collection name"},
                    "document_id": {"type": "string", "description": "Document ID to retrieve"},
                },
                "required": ["collection", "document_id"],
            },
        ),
        types.Tool(
            name="firestore_query_collection",
            description=(
                "Query documents in a Firestore collection with an optional simple filter. "
                "Returns up to `limit` documents (default 20)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Firestore collection name"},
                    "field": {"type": "string", "description": "Field name to filter on (optional)"},
                    "operator": {
                        "type": "string",
                        "enum": ["==", "!=", "<", "<=", ">", ">=", "array_contains"],
                        "description": "Comparison operator (required if field is set)",
                    },
                    "value": {"description": "Value to compare against (required if field is set)"},
                    "limit": {"type": "integer", "default": 20, "description": "Max documents to return"},
                },
                "required": ["collection"],
            },
        ),
        types.Tool(
            name="firestore_set_document",
            description=(
                "Write (create or overwrite) a document in Firestore. "
                "Pass `merge: true` to merge fields instead of overwriting."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Firestore collection name"},
                    "document_id": {
                        "type": "string",
                        "description": "Document ID. Omit to let Firestore auto-generate one.",
                    },
                    "data": {"type": "object", "description": "Key/value fields to write"},
                    "merge": {
                        "type": "boolean",
                        "default": False,
                        "description": "Merge into existing document instead of overwriting",
                    },
                },
                "required": ["collection", "data"],
            },
        ),
        types.Tool(
            name="firestore_delete_document",
            description="Delete a document from Firestore.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "description": "Firestore collection name"},
                    "document_id": {"type": "string", "description": "Document ID to delete"},
                },
                "required": ["collection", "document_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except Exception as exc:
        result = {"error": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def _dispatch(name: str, args: dict):
    if name == "firestore_get_document":
        return _get_document(args["collection"], args["document_id"])

    if name == "firestore_query_collection":
        return _query_collection(
            args["collection"],
            field=args.get("field"),
            operator=args.get("operator"),
            value=args.get("value"),
            limit=args.get("limit", 20),
        )

    if name == "firestore_set_document":
        return _set_document(
            args["collection"],
            args["data"],
            document_id=args.get("document_id"),
            merge=args.get("merge", False),
        )

    if name == "firestore_delete_document":
        return _delete_document(args["collection"], args["document_id"])

    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------

def _get_document(collection: str, document_id: str) -> dict:
    ref = db.collection(collection).document(document_id)
    doc = ref.get()
    if not doc.exists:
        return {"found": False, "collection": collection, "document_id": document_id}
    return {"found": True, "collection": collection, "document_id": document_id, "data": doc.to_dict()}


def _query_collection(
    collection: str,
    field: str | None = None,
    operator: str | None = None,
    value=None,
    limit: int = 20,
) -> dict:
    query = db.collection(collection)
    if field and operator is not None:
        query = query.where(field, operator, value)
    query = query.limit(limit)

    docs = [{"document_id": d.id, "data": d.to_dict()} for d in query.stream()]
    return {"collection": collection, "count": len(docs), "documents": docs}


def _set_document(
    collection: str,
    data: dict,
    document_id: str | None = None,
    merge: bool = False,
) -> dict:
    col_ref = db.collection(collection)
    if document_id:
        ref = col_ref.document(document_id)
        ref.set(data, merge=merge)
    else:
        _ts, ref = col_ref.add(data)
        document_id = ref.id

    return {"collection": collection, "document_id": document_id, "written": True}


def _delete_document(collection: str, document_id: str) -> dict:
    db.collection(collection).document(document_id).delete()
    return {"collection": collection, "document_id": document_id, "deleted": True}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
