# Snaptron MCP Server

Query RNA-seq splice junction data from [Snaptron](https://snaptron.cs.jhu.edu/) directly

Claude itself was mostly used to generate this repo.   
But it was manually (but briefly) tested the MCP server with Claude Desktop.

IMPORTANT NOTE: Snaptron can generate large amounts of [textual] data which can quickly eat up the context window and your tokens,
SO USE AT YOUR OWN RISK!

## Installation

### 1. Install dependencies

```bash
pip install mcp httpx
```

### 2. Configure Claude Desktop

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following:

```json
{
  "mcpServers": {
    "snaptron": {
      "command": "python",
      "args": ["/absolute/path/to/snaptron_mcp_server.py"]
    }
  }
}
```

> Replace `/absolute/path/to/snaptron_mcp_server.py` with the actual path where you saved the file.

### 3. Restart Claude Desktop

The Snaptron tools will appear in Claude's tool panel.

---

## Available Tools

### `snaptron_list_compilations`
Fetches the live registry of all Snaptron compilations from the Langmead lab.

**Example prompt:** *"List all available Snaptron compilations"*

---

### `snaptron_query_junctions`
Query splice junctions by gene, coordinates, or filters.

**Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `compilation` | Dataset to query | `gtexv2`, `srav3h`, `tcgav2` |
| `regions` | Gene symbol or chr coordinates | `BRCA1`, `chr21:1-500` |
| `ids` | Direct snaptron_id lookup | `5,7,8` |
| `rfilter` | Range filters on junction stats | `["samples_count>:5", "coverage_avg>:10"]` |
| `sfilter` | Sample metadata filters | `["description:cortex", "SMRIN>:8"]` |
| `sids` | Limit to specific sample IDs | `30,100,150` or `Brain` (GTEx) |
| `contains` | Only junctions within region | `1` |
| `exact` | Only junctions exactly matching region | `1` |
| `either` | Match start (`1`) or end (`2`) of region | `1` |
| `header` | Include header row | `1` (default) |
| `fields` | Specific fields to return | `snaptron_id,samples_count` |

**Example prompts:**
- *"Query junctions for BRCA1 in GTEx (gtexv2) with at least 5 samples"*
- *"Find junctions in chr21:1-5000 from tcgav2 with coverage_sum greater than 10"*

---

### `snaptron_query_genes`
Query gene-level junction aggregations (uses `/genes` endpoint).

Same parameters as `snaptron_query_junctions`.

---

### `snaptron_query_samples`
Query sample metadata from a compilation.

**Example prompts:**
- *"Find samples in srav3h with cortex in the description"*
- *"Get sample metadata for rail_ids 20, 40, 100 in gtexv2"*

---

### `snaptron_get_result_count`
Get the count of junctions matching a query without fetching all data. Useful for large queries.

---

### `snaptron_build_url`
Build a Snaptron API URL without executing it. Useful for debugging or sharing queries.

---

## Example Queries

### Find annotated junctions in BRCA1 with high coverage (GTEx)
Ask Claude: *"Query GTEx v2 for annotated junctions in BRCA1 with at least 100 supporting samples"*

This maps to:
```
http://snaptron.cs.jhu.edu/gtexv2/snaptron?regions=BRCA1&rfilter=samples_count>:100&rfilter=annotated:1
```

### Find cortex samples in SRA
Ask Claude: *"Find RNA-seq samples in srav3h from cortex tissue"*

This maps to:
```
http://snaptron.cs.jhu.edu/srav3h/samples?sfilter=description:cortex&sfilter=library_strategy:RNA-Seq
```

### Look up specific junctions by ID
Ask Claude: *"Get snaptron junctions with IDs 5, 7, and 8 from gtexv2"*

---

## Compilations Reference

| Name | Description | Samples |
|------|-------------|---------|
| `gtexv2` | GTEx recount3 (human, hg38) | ~19k |
| `srav3h` | SRA human recount3 (hg38) | ~316k |
| `srav1m` | SRA mouse recount3 (mm10) | ~417k |
| `tcgav2` | TCGA recount3 (human, hg38) | ~11k |
| `gtex` | GTEx recount2 (human, hg38) | ~10k |
| `srav2` | SRA recount2 (human, hg38) | ~49k |
| `tcga` | TCGA recount2 (human, hg38) | ~11k |

---

## Troubleshooting

**Server not appearing in Claude:** Make sure the path in the config is absolute and the file is executable. Try running `python /path/to/snaptron_mcp_server.py` manually to check for import errors.

**`ModuleNotFoundError: mcp`:** Run `pip install mcp httpx` to install dependencies.

**Slow or no results:** Snaptron queries on large compilations (e.g. `srav3h`) can be slow. Use `snaptron_get_result_count` first to check query size, and add `rfilter` constraints to narrow results.
