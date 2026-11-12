# Dewly.Knowledge

**Portable JSON knowledge feed for Dewly.Mod.** This is a data-only GitHub publishing repository: no Git history, game binaries, SMAPI mod, SQLite schema, or GitHub Actions included. You can create a new GitHub repository and upload these files as its initial contents.

The current snapshot was assembled from the uploaded `Dewly-2.zip` project and its later aggregate-planning fix archive. **The aggregate-completion fix is Python planner logic, not an additional JSON dataset.** The knowledge JSON here is therefore the latest supplied data snapshot, not a new gameplay extraction.

## What is here?

| Folder | Purpose |
|---|---|
| `data/` | **111 canonical knowledge JSON files**: achievement definitions and rules; 2,039 graph nodes; versioned game-content indexes; acquisition research, routes and prerequisites; tracking and game-access contracts; daily task generators; source/evidence/audit records; schema documents. |
| `publish/manifest.json` | Small JSON update manifest containing a knowledge revision, payload SHA-256, compatibility evidence and source document hashes. |
| `publish/knowledge.json` | **One self-contained JSON bundle** containing all 111 source documents, with their original relative paths. This is the file Dewly.Mod should download and convert to local SQLite. |
| `tools/rebuild_publish.py` | Optional **local-only packer and integrity verifier**, written using Python's standard library. It does **not** create a SQLite database or depend on the installed game. |
| `docs/IMPORT-CONTRACT.md` | Detailed contract and recommended update/import behaviour for the C# mod. |

The `data/` tree is the human-editable source; **the mod downloads only `publish/manifest.json` and, when changed, `publish/knowledge.json`**. You do not need 111 HTTP requests.

## Publish to GitHub

1. Create a new GitHub repository (e.g. `Dewly.Knowledge`).
2. Upload the contents of this directory **as the repository root**, not the enclosing ZIP folder.
3. Push to `main`. No GitHub Actions, Python runtime on GitHub or build process is needed.
4. Configure Dewly.Mod to fetch the raw files:

   - `https://raw.githubusercontent.com/OWNER/REPO/main/publish/manifest.json`
   - `https://raw.githubusercontent.com/OWNER/REPO/main/publish/knowledge.json`

Replace `OWNER/REPO` with your real GitHub repository path. The URLs above are templates, not live links.

## When knowledge changes

Edit the JSON documents under `data/` on your computer, run your original Dewly development project's validators, and **locally** rebuild the publish artifacts:

```powershell
python tools/rebuild_publish.py
python tools/rebuild_publish.py --verify
```

Commit and push the updated `data/` files **and both `publish/` files in the same commit**. The mod compares the content-derived `knowledgeRevision`/SHA-256 and imports only if changed. The packer produces identical output for identical inputs; it does not contact GitHub or run game extraction.

**Important:** The update feed has no automatic CI enforcement. Publishing invalid or inconsistent gameplay data is possible if you skip local validation. The `--verify` flag checks JSON parsing, bundle freshness and checksums, but it is **not** a replacement for the original repository's comprehensive schema and graph tests.

## Game version and limits

The included content index was derived for **Stardew Valley 1.6.15.24354**. It does not imply live SMAPI testing, a fully implemented acquisition chain for every item, or an automatically known Xbox achievement award status. Some runtime bindings are contracts only, and several platform-specific interpretations require later verification.

**The loaded game is authoritative** for modded or updated content. The shipped knowledge is a versioned baseline. The SQLite importer, database schema/migrations, C# runtime evaluator, save-state observation, and local player data belong to **Dewly.Mod**, not this repository.

For the import/update algorithm and SQLite provenance relationships, see [docs/IMPORT-CONTRACT.md](docs/IMPORT-CONTRACT.md).
