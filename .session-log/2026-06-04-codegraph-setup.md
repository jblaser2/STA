# Session: CodeGraph Setup for Package Codebases
Date: 2026-06-04

## Goal
Set up codegraph (semantic code index + MCP server) so Claude can answer architectural questions
about Josh's packages without scanning files. Scope: Josh's packages only (not Eben's).

## What happened

1. **Surveyed all packages for indexable source:**
   - PyTom: 285 Python files at `~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom/`
   - RELION: 4 Python packages in `~/conda-envs/relion-5.0/lib/python3.10/site-packages/`
     (`tomography_python_programs`, `relion_classranker`, `relion_blush`, `starfile`)
   - Dynamo: 21k MATLAB files at `~/Research/dynamo/matlab/` — MATLAB not in codegraph's
     supported languages; not indexable
   - PEET, ProTomo, emClarity: binary-only distributions; not indexable
   - DISCA, TomoFlow: conda envs have no package-level Python source; not indexable

2. **Installed codegraph v0.9.9:**
   - `npm` not in system PATH; used eman2 conda env's npm
   - `PATH=~/conda-envs/eman2/bin:$PATH npm i -g @colbymchenry/codegraph`
   - Created PATH-aware wrapper at `~/.local/bin/codegraph` (already on PATH via .bashrc)

3. **Wired MCP server into Claude Code:**
   - `codegraph install -y` → updated `~/.claude.json` (mcpServers entry) and
     `~/.claude/settings.json` (auto-allow permissions for all codegraph tools)

4. **Indexed all indexable packages:**
   | Package | Files | Nodes | Edges |
   |---------|-------|-------|-------|
   | pytom | 288 | 8,170 | 21,090 |
   | tomography_python_programs | 72 | 695 | 1,081 |
   | relion_classranker | 2 | 13 | 16 |
   | relion_blush | 3 | 70 | 158 |
   | starfile | 7 | 103 | 160 |

5. **Verified:** `codegraph query "cross_correlation"` from pytom dir returned
   `gpu/gpuFunctions.py:28` and `gpu/gpuStructures.py:375` — correct.

## Files changed
- `scripts/codegraph_index.md` — new; documents all package source locations, working install
  commands, index commands, query examples, and non-indexable package notes

## Where I stopped
All indexes are built and green. MCP server config is in `~/.claude.json`. Wrapper is at
`~/.local/bin/codegraph`.

## Next step
**Restart Claude Code** for the MCP tools (`codegraph_search`, `codegraph_explore`,
`codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_files`,
`codegraph_status`, `codegraph_node`) to become available in-session.

After restart: test MCP tools interactively (e.g. "where is the cross-correlation kernel in PyTom?").

To sync indexes after a conda env update: `codegraph sync <path>` for each package.
