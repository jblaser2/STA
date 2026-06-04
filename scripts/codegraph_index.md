# CodeGraph Index — Package Source Locations

CodeGraph (https://github.com/colbymchenry/codegraph) creates a local SQLite semantic index
so Claude can answer architectural questions about each package without scanning files.

---

## Install (one-time, already done on Josh's machine)

`npm` is not in the system PATH — use the one bundled in the `eman2` conda env:

```bash
# Install
PATH=~/conda-envs/eman2/bin:$PATH npm i -g @colbymchenry/codegraph

# Create a PATH-aware wrapper so `codegraph` works from any shell
cat > ~/.local/bin/codegraph << 'EOF'
#!/usr/bin/env bash
export PATH=/home/jblaser2/conda-envs/eman2/bin:$PATH
exec /home/jblaser2/conda-envs/eman2/bin/codegraph "$@"
EOF
chmod +x ~/.local/bin/codegraph

# Wire MCP server into Claude Code (adds to ~/.claude.json + ~/.claude/settings.json)
codegraph install -y
```

Restart Claude Code after install for the MCP tools to appear.

---

## Package Source Map

| Package | Language | Source Root | Indexable? | Notes |
|---------|----------|-------------|------------|-------|
| PyTom | Python | `~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom/` | ✅ | 285 .py files; classification, alignment, GPU modules |
| RELION tomo scripts | Python | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/tomography_python_programs/` | ✅ | 72 .py files; tilt-series pipeline |
| RELION classranker | Python | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_classranker/` | ✅ | classification ranking model |
| RELION blush | Python | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_blush/` | ✅ | map-improvement model |
| starfile | Python | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/starfile/` | ✅ | STAR file I/O used by all RELION scripts |
| Dynamo | MATLAB | `~/Research/dynamo/matlab/` | ❌ | 21,668 .m files; MATLAB not in codegraph's supported languages |
| PEET | C binary | `~/Applications/IMOD/bin/` | ❌ | Compiled only; no Python/source available |
| DISCA | — | no source found | ❌ | conda env exists but no package .py files in site-packages |
| TomoFlow | — | no source found | ❌ | conda env exists but no package .py files in site-packages |
| ProTomo | C binary | `~/Applications/protomo-3.1.0/` | ❌ | bin/lib/util only; no source |
| emClarity | MATLAB binary | `~/Applications/emClarity_install/emClarity_extracted/emClarity_1.5.3.11/` | ❌ | binary + MATLAB param examples only |

---

## Index Commands (run after install; all already indexed on Josh's machine)

Each command creates a `.codegraph/codegraph.db` in that directory.

```bash
# PyTom — classification, alignment, GPU kernels (288 files, 8170 nodes)
codegraph init ~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom

# RELION Python — tomo pipeline scripts (72 files, 695 nodes)
codegraph init ~/conda-envs/relion-5.0/lib/python3.10/site-packages/tomography_python_programs

# RELION classranker (2 files), blush (3 files), starfile (7 files)
codegraph init ~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_classranker
codegraph init ~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_blush
codegraph init ~/conda-envs/relion-5.0/lib/python3.10/site-packages/starfile
```

To sync after a package update: `codegraph sync <path>`

---

## Verify / Query Examples

The CLI `query` command must be run from the package directory (codegraph uses cwd to find the DB):

```bash
# Check index status
codegraph status ~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom

# Symbol search (cd into the package dir first)
cd ~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom
codegraph query "cross_correlation"   # finds gpu/gpuFunctions.py:28 and gpu/gpuStructures.py:375
codegraph query "classify"
codegraph callers "mcoEXMX"
codegraph impact "correlationMatrix"

cd ~/conda-envs/relion-5.0/lib/python3.10/site-packages/tomography_python_programs
codegraph query "get_particle_poses"
```

Via MCP (in Claude sessions after restart): Claude can call `codegraph_search`, `codegraph_callers`,
`codegraph_explore`, etc. automatically when navigating PyTom/RELION code.

---

## DB File Locations (after indexing)

| Package | DB path |
|---------|---------|
| PyTom | `~/conda-envs/pytom_env/lib/python3.12/site-packages/pytom/.codegraph/codegraph.db` |
| RELION tomo | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/tomography_python_programs/.codegraph/codegraph.db` |
| RELION classranker | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_classranker/.codegraph/codegraph.db` |
| RELION blush | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/relion_blush/.codegraph/codegraph.db` |
| starfile | `~/conda-envs/relion-5.0/lib/python3.10/site-packages/starfile/.codegraph/codegraph.db` |

---

## Packages with No Indexable Source

- **Dynamo** — 21k MATLAB files at `~/Research/dynamo/matlab/`; MATLAB is not in codegraph's
  supported language list. Navigate with MATLAB editor or grep `.m` files directly.
- **PEET/IMOD** — C binary distribution, no Python/source available.
- **DISCA / TomoFlow** — conda envs have GPU+ML dependencies but no package-level Python source
  was found in site-packages. These appear to be run via standalone scripts, not installable packages.
- **ProTomo / emClarity** — binary-only distributions.
