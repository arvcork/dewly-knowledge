# Dewly knowledge feed → SQLite import contract

## Files and wire format

**Request 1:** `GET https://raw.githubusercontent.com/OWNER/REPO/main/publish/manifest.json`.

The manifest has:

- `format: "dewly.knowledge.manifest"` and integer `manifestSchemaVersion: 1`.
- A content-addressed `knowledgeRevision` derived from canonical relative file names and source-document SHA-256 values; changes to any included `data/*.json` change the revision.
- `sourceGameVersion`, `sourceGameContentFingerprint`, `dataSchemaVersion` for compatibility decisions.
- `payload.path` (`publish/knowledge.json`), `payload.sha256`, `payload.bytes`, `payload.encoding`.
- An index of `files[]` with their original paths and SHA-256 values.

**Request 2 (only when updated):** Download `publish/knowledge.json` from the same repository. Verify its full-byte SHA-256 against the manifest *before* JSON parsing or database mutation. The publisher uses canonical JSON serialization and a trailing newline.

The bundle has this shape:

```json
{
  "format": "dewly.knowledge.bundle",
  "bundleSchemaVersion": 1,
  "knowledgeRevision": "<computed revision>",
  "sourceGameVersion": "1.6.15.24354",
  "sourceGameContentFingerprint": "<content fingerprint>",
  "dataSchemaVersion": "0.1.0",
  "documentCount": 111,
  "documents": [
    {
      "path": "data/achievement-definitions/fishing.json",
      "content": { "schemaVersion": "0.1.0", "category": "fishing", "entries": [] }
    }
  ]
}
```

The `content` shown in this example is deliberately abbreviated; **the real bundle contains each original document without deleting any fields**. The document `path` is the type discriminator and preserves existing file and evidence references. Do not reinterpret the shape of all content files as one universal schema: different document families have different source schemas.

## Responsibility boundary

**Knowledge repository:** all JSON facts, stable text IDs, source references, selectors, evidence and rule definitions. The optional Python packer only assembles and validates the bundle. No SQLite tables or seed migrations are defined here.

**Dewly.Mod (C#):** knows the SQLite schema, migrations, relationship mapping, reader functions, scheduling logic, and how to turn the bundle into a validated local knowledge database. It owns runtime version/feature compatibility checks, multiplayer/save scoping, mod-content overrides, and UI.

## Safe update flow for Dewly.Mod

1. Never block the game loop on HTTP or JSON parsing. Fetch updates asynchronously, with network timeouts and download-size limits.
2. Check `format`, supported manifest/bundle schema version, compatible game version/content and condition operators **before importing**. Old binaries must refuse data they cannot interpret.
3. Compare the manifest revision/hash against the locally imported revision. If unchanged, do nothing.
4. Download the bundle and compute its **SHA-256**. If it does not match, retry later; keep the existing database. `main` can change between separate HTTP requests or be served from different caches.
5. Parse JSON with safe maximum sizes/depths. Validate `documentCount`, unique relative paths, `knowledgeRevision` match, required families, stable IDs, referential integrity, and expected content types.
6. Build a **new temporary SQLite database** from scratch, not by mutating the active DB. Enable `PRAGMA foreign_keys = ON` on every connection, use a single transaction for seeding, and create indexes. Use a migration/schema version owned by the mod.
7. Store the original source document path and ID/provenance link for each imported rule. A `source_documents` table with document path + hash is useful even when rules are fully normalized.
8. After import, run `PRAGMA foreign_key_check` and `PRAGMA integrity_check`; only activate if both succeed and compatibility checks pass. Retain a known-good backup/rollback.
9. Switch the active database only when it is safe to close existing readers (e.g. on next launch). Don't replace an open SQLite file, particularly on Windows.
10. Continue with the bundled/offline knowledge baseline if GitHub is unavailable. Knowledge downloads are **not** tied to the 30-minute in-game checklist reconciliation interval.

## Suggested relational model — implementation belongs to the mod

Use stable string IDs and explicit foreign keys for `achievements`, `requirements`, `actions`, `dependency_edges`, `content_records`, `acquisition_routes`, `progression_nodes`, `tracking_contracts`, `daily_task_generators`, `evidence_claims`, `evidence_sources`, `claim_source_links` and `route_evidence_links`. Some source documents are generation-time metadata, not necessarily runtime tables.

Preserve AND / OR / ANY / COUNT / SUM semantics, threshold and quantity semantics, item-qualified IDs, source scopes, unknown-state behaviour, and versioned runtime content authority. Do not force every `requires` edge into a simple logical AND. Preserve stable IDs and separate per-save/player state from shared knowledge data.

An alternative safe starting design is to import every source document into `source_documents(path TEXT PRIMARY KEY, json TEXT NOT NULL, sha256 TEXT NOT NULL)` **in addition** to normalized tables, to guarantee lossless traceability while adding relational views incrementally. Use parameterised SQL, not string concatenation.

## Local publishing / update policy

Run project-level checks in the original development repository before copying JSON, then run:

```powershell
python tools/rebuild_publish.py
python tools/rebuild_publish.py --verify
```

Commit `data/`, `publish/manifest.json`, and `publish/knowledge.json` together. No GitHub Actions required. Publishing `main` as a mutable channel is acceptable for development; for maximum update atomicity, optionally move to a manifest that contains a **commit-pinned** bundle URL or immutable release asset later.

Do not treat the versioned vanilla content index as overriding live modded content. Do not infer missing saved values are zero; unknown is a meaningful state. The aggregate-completion logic and C# runtime importer must be implemented and tested in Dewly.Mod independently of this JSON packaging.
