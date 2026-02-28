#!/usr/bin/env python3
"""
Snaptron MCP Server for Claude Desktop
Provides tools to query the Snaptron web services API for RNA-seq splice junction data.

Based on documentation at: https://snaptron.cs.jhu.edu/

Installation:
    pip install mcp httpx

Add to Claude Desktop config (~/.config/claude/claude_desktop_config.json):
    {
        "mcpServers": {
            "snaptron": {
                "command": "python",
                "args": ["/path/to/snaptron_mcp_server.py"]
            }
        }
    }
"""

import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_URL = "http://snaptron.cs.jhu.edu"

# Known compilations as of 2023-02-11 (registry endpoint will fetch live list)
KNOWN_COMPILATIONS = [
    "gtexv2", "srav3h", "srav1m", "tcgav2", "tcga", "gtex", "srav2"
]

server = Server("snaptron")


def build_url(compilation: str, endpoint: str, params: dict) -> str:
    """Build a Snaptron API URL."""
    base = f"{BASE_URL}/{compilation}/{endpoint}"
    # Build query string manually to support repeated params (e.g. rfilter)
    parts = []
    for key, value in params.items():
        if isinstance(value, list):
            for v in value:
                parts.append(f"{key}={v}")
        elif value is not None and value != "":
            parts.append(f"{key}={value}")
    if parts:
        return base + "?" + "&".join(parts)
    return base


async def fetch(url: str) -> str:
    """Fetch a URL and return text content."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="snaptron_query_junctions",
            description=(
                "Query splice junctions (introns) from a Snaptron compilation. "
                "Supports region-based queries (gene symbol or chromosomal coordinates), "
                "range filters on statistics, sample metadata filters, sample ID filters, "
                "and direct snaptron ID lookups. "
                "Returns TAB-delimited junction records with fields: snaptron_id, chromosome, "
                "start, end, length, strand, annotated, samples_count, coverage_sum, coverage_avg, coverage_median, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compilation": {
                        "type": "string",
                        "description": (
                            "Snaptron compilation to query. Options include: "
                            "gtexv2 (GTEx recount3, ~19k samples), "
                            "srav3h (SRA human recount3, ~316k samples), "
                            "srav1m (SRA mouse recount3, ~417k samples), "
                            "tcgav2 (TCGA recount3, ~11k samples), "
                            "tcga (TCGA recount2), gtex (GTEx recount2), srav2 (SRA recount2). "
                            "Use snaptron_list_compilations to get current list."
                        ),
                        "enum": KNOWN_COMPILATIONS
                    },
                    "regions": {
                        "type": "string",
                        "description": (
                            "Genomic region to query. Can be a HUGO gene symbol (e.g. 'BRCA1') "
                            "or chromosomal coordinates (e.g. 'chr21:1-500'). "
                            "Required if using rfilter or sfilter."
                        )
                    },
                    "ids": {
                        "type": "string",
                        "description": (
                            "Comma-separated list of snaptron_ids to retrieve directly "
                            "(e.g. '5,7,8'). Cannot be used with other parameters."
                        )
                    },
                    "rfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "One or more range filter expressions on junction statistics. "
                            "Format: fieldname[>:|<:|:]value. "
                            "Fields: length, annotated, left_annotated, right_annotated, strand, "
                            "samples_count, coverage_sum, coverage_avg, coverage_median. "
                            "Examples: ['samples_count>:5', 'coverage_avg>:10.0', 'strand:+']"
                        )
                    },
                    "sfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "One or more sample metadata filter expressions. "
                            "Format: fieldname:value (text) or fieldname>:value / fieldname<:value (numeric). "
                            "Examples: ['description:cortex', 'SMRIN>:8', 'library_strategy:RNA-Seq']"
                        )
                    },
                    "sids": {
                        "type": "string",
                        "description": (
                            "Limit results to junctions found in specific samples. "
                            "Comma-separated rail_ids (e.g. '30,100,150') or a predefined group name "
                            "(e.g. 'Brain' for GTEx). Requires 'regions' to also be set."
                        )
                    },
                    "contains": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "If 1, return only junctions whose start AND end are within the region boundaries."
                    },
                    "exact": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "If 1, return only junctions whose coordinates exactly match the region."
                    },
                    "either": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "Return junctions where start (either=1) or end (either=2) matches the region boundary."
                    },
                    "header": {
                        "type": "integer",
                        "enum": [0, 1],
                        "default": 1,
                        "description": "Include header line (1) or not (0). Default is 1."
                    },
                    "fields": {
                        "type": "string",
                        "description": (
                            "Comma-separated list of fields to return "
                            "(e.g. 'snaptron_id,chromosome,start,end,samples_count'). "
                            "Can also include 'rc' to get result count."
                        )
                    }
                },
                "required": ["compilation"]
            }
        ),
        Tool(
            name="snaptron_query_genes",
            description=(
                "Query gene-level data from a Snaptron compilation using the /genes endpoint. "
                "Supports region-based queries, range filters, and sample filters. "
                "Returns gene-level junction aggregations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compilation": {
                        "type": "string",
                        "description": "Snaptron compilation to query (e.g. gtexv2, srav3h, tcgav2).",
                        "enum": KNOWN_COMPILATIONS
                    },
                    "regions": {
                        "type": "string",
                        "description": "Gene symbol (e.g. 'BRCA1') or coordinates (e.g. 'chr17:43044295-43170245')."
                    },
                    "ids": {
                        "type": "string",
                        "description": "Comma-separated snaptron_ids. Cannot be used with other parameters."
                    },
                    "rfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Range filter expressions (same format as snaptron_query_junctions)."
                    },
                    "sfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sample metadata filter expressions."
                    },
                    "sids": {
                        "type": "string",
                        "description": "Sample IDs or group name to filter by."
                    },
                    "contains": {"type": "integer", "enum": [0, 1]},
                    "exact": {"type": "integer", "enum": [0, 1]},
                    "either": {"type": "integer", "enum": [1, 2]},
                    "header": {"type": "integer", "enum": [0, 1]},
                    "fields": {"type": "string", "description": "Fields to return, comma-separated."}
                },
                "required": ["compilation"]
            }
        ),
        Tool(
            name="snaptron_query_samples",
            description=(
                "Query sample metadata from a Snaptron compilation using the /samples endpoint. "
                "Returns sample records with metadata fields like tissue, organism, library_strategy, etc. "
                "Supports filtering by metadata fields and direct sample ID lookup."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compilation": {
                        "type": "string",
                        "description": "Snaptron compilation to query.",
                        "enum": KNOWN_COMPILATIONS
                    },
                    "sfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Sample metadata filter expressions. "
                            "Format: fieldname:value or fieldname>:value / fieldname<:value. "
                            "Examples: ['description:cortex', 'library_strategy:RNA-Seq', 'SMRIN>:8']"
                        )
                    },
                    "ids": {
                        "type": "string",
                        "description": (
                            "Comma-separated rail_ids (sample IDs) to retrieve directly "
                            "(e.g. '20,40,100'). Cannot be used with sfilter."
                        )
                    },
                    "header": {
                        "type": "integer",
                        "enum": [0, 1],
                        "description": "Include header (1) or not (0)."
                    },
                    "fields": {
                        "type": "string",
                        "description": "Comma-separated list of fields to return."
                    }
                },
                "required": ["compilation"]
            }
        ),
        Tool(
            name="snaptron_list_compilations",
            description=(
                "Fetch the current registry of all active Snaptron compilations hosted by the Langmead lab. "
                "Returns a JSON object where keys are compilation names and values describe available "
                "metadata fields and their types (t=text, i=integer, f=float)."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="snaptron_get_result_count",
            description=(
                "Get the count of results for a junction query without returning all records. "
                "Uses the 'rc' field option to return only the count. "
                "Useful for gauging query size before fetching full results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compilation": {
                        "type": "string",
                        "description": "Snaptron compilation to query.",
                        "enum": KNOWN_COMPILATIONS
                    },
                    "regions": {
                        "type": "string",
                        "description": "Gene symbol or chromosomal coordinates."
                    },
                    "rfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Range filter expressions."
                    },
                    "sfilter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sample metadata filter expressions."
                    },
                    "sids": {
                        "type": "string",
                        "description": "Sample IDs or group name."
                    }
                },
                "required": ["compilation", "regions"]
            }
        ),
        Tool(
            name="snaptron_build_url",
            description=(
                "Build a Snaptron API URL from query parameters without executing the request. "
                "Useful for understanding the URL structure or sharing queries. "
                "Returns the full URL that would be called."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compilation": {
                        "type": "string",
                        "description": "Snaptron compilation name.",
                        "enum": KNOWN_COMPILATIONS
                    },
                    "endpoint": {
                        "type": "string",
                        "enum": ["snaptron", "genes", "samples"],
                        "description": "API endpoint to query."
                    },
                    "regions": {"type": "string"},
                    "ids": {"type": "string"},
                    "rfilter": {"type": "array", "items": {"type": "string"}},
                    "sfilter": {"type": "array", "items": {"type": "string"}},
                    "sids": {"type": "string"},
                    "contains": {"type": "integer", "enum": [0, 1]},
                    "exact": {"type": "integer", "enum": [0, 1]},
                    "either": {"type": "integer", "enum": [1, 2]},
                    "header": {"type": "integer", "enum": [0, 1]},
                    "fields": {"type": "string"}
                },
                "required": ["compilation", "endpoint"]
            }
        )
    ]


def extract_params(args: dict) -> dict:
    """Extract query parameters from tool arguments."""
    params = {}
    for key in ["regions", "ids", "sids", "contains", "exact", "either", "header", "fields"]:
        if key in args and args[key] is not None:
            params[key] = args[key]

    # Handle repeated params (rfilter and sfilter are lists)
    if "rfilter" in args and args["rfilter"]:
        params["rfilter"] = args["rfilter"]
    if "sfilter" in args and args["sfilter"]:
        params["sfilter"] = args["sfilter"]

    return params


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "snaptron_list_compilations":
            url = f"{BASE_URL}/snaptron/registry"
            result = await fetch(url)
            try:
                parsed = json.loads(result)
                formatted = json.dumps(parsed, indent=2)
                return [TextContent(type="text", text=f"Snaptron Compilation Registry:\n\n{formatted}")]
            except json.JSONDecodeError:
                return [TextContent(type="text", text=f"Registry response:\n{result}")]

        elif name == "snaptron_query_junctions":
            compilation = arguments["compilation"]
            params = extract_params(arguments)
            url = build_url(compilation, "snaptron", params)
            result = await fetch(url)
            lines = result.strip().split("\n")
            count = len([l for l in lines if l and not l.startswith("DataSource")])
            return [TextContent(
                type="text",
                text=f"Query URL: {url}\n\nResults ({count} records):\n\n{result}"
            )]

        elif name == "snaptron_query_genes":
            compilation = arguments["compilation"]
            params = extract_params(arguments)
            url = build_url(compilation, "genes", params)
            result = await fetch(url)
            lines = result.strip().split("\n")
            count = len([l for l in lines if l and not l.startswith("DataSource")])
            return [TextContent(
                type="text",
                text=f"Query URL: {url}\n\nResults ({count} records):\n\n{result}"
            )]

        elif name == "snaptron_query_samples":
            compilation = arguments["compilation"]
            params = extract_params(arguments)
            url = build_url(compilation, "samples", params)
            result = await fetch(url)
            lines = result.strip().split("\n")
            count = len([l for l in lines if l and not l.startswith("DataSource")])
            return [TextContent(
                type="text",
                text=f"Query URL: {url}\n\nResults ({count} records):\n\n{result}"
            )]

        elif name == "snaptron_get_result_count":
            compilation = arguments["compilation"]
            params = extract_params(arguments)
            params["fields"] = "rc"
            url = build_url(compilation, "snaptron", params)
            result = await fetch(url)
            return [TextContent(
                type="text",
                text=f"Query URL: {url}\n\nResult count response:\n{result}"
            )]

        elif name == "snaptron_build_url":
            compilation = arguments["compilation"]
            endpoint = arguments.get("endpoint", "snaptron")
            params = extract_params(arguments)
            url = build_url(compilation, endpoint, params)
            return [TextContent(
                type="text",
                text=f"Built Snaptron URL:\n{url}\n\nYou can test this with:\n  curl -L \"{url}\""
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"HTTP error {e.response.status_code}: {e.response.text}")]
    except httpx.RequestError as e:
        return [TextContent(type="text", text=f"Request error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
