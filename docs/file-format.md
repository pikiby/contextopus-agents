# Agents file format and migration

The authoritative sources live under modules/agents/data/ in the Contextopus root.
profiles/ and teams/ hold ordinary Markdown files; instructions/ holds the reference
to the main-agent document in Core's common library. Package updates preserve data/.

A profile file may be named reviewer.md:

```yaml
---
id: reviewer
type: profile
title: Reviewer
description: Review code changes and report evidence
model: local/test
settings:
  reasoning_effort: high
---
Inspect the changed code and report actionable findings with evidence.
```

A team file may be named engineering.md:

```yaml
---
id: engineering
type: team
title: Engineering
description: Implement and review changes
roles:
  review:
    profile: "[[modules/agents/data/profiles/reviewer]]"
---
Review the completed change before acceptance.
```

Each role binds exactly one profile. Profile links point to real files. The resolver supports
root-relative paths, module-data-relative profile paths and unambiguous basenames,
optionally with a Markdown suffix or Obsidian alias. It never treats a surviving YAML ID
as proof that a broken file link resolves. Missing/ambiguous links are reported without
rewriting the source. Stable YAML IDs still let API callers find a renamed profile.

Files created by tools use a readable title slug with a short identity suffix when needed.
Editing a record preserves its existing path. Source revisions hash the entire UTF-8 file;
body revisions hash only Markdown instructions. Metadata/path changes preserve embeddings when discovery text remains unchanged.
YAML metadata is never prepended to a nonempty body or used as executor instruction.

Main-agent rules live at core/instructions/agents-main.md, with type instruction and ID
agents-main. data/instructions/main.md contains metadata `id: main`,
`type: instruction-reference`, `document: "[[agents-main]]"` and an empty body.
The full rules are read through agents.instructions_read. An explicit save creates the
common document/reference; the packaged default remains read-only before that save.
The common document may declare an instructions mapping of roles to required wikilinks.
agents.instructions_read returns the primary exactly once in content and all other required documents in
documents, dependencies first, with required_revision and an aggregate revision covering the whole chain. An edit
to a required dependency invalidates an older save revision even if the primary is unchanged.
A missing/ambiguous/cyclic required link is an error. Main-agent rules do not belong in a participant profile.

Workspace owns authoring and binding instructions for its contexts, including agent-work
rules. Its instructions procedure defines common reuse, direct-link and routing rules.
Agents manages profiles, teams and its module-wide main instruction; editing that primary
document does not bind rules to a Workspace context. Agents remains usable without Workspace.

## Synchronization

Queries read validated current files. The service reconciles complete snapshots into SQL
and shared RAG through Core's common document planner. Tool edits use the same scanner.
A malformed source, duplicate ID, symlink, missing directory or incomplete scan stops
reconciliation before any derived deletion. Deleting a file externally removes its derived
record/vector on reconciliation, including after restart. Restarts never export cached SQL.

Source-profile deletion through agents.profile_delete uses the complete source revision,
checks team dependencies, cleans RAG, rechecks the observed
source snapshot and then removes that one file. A failed RAG cleanup retains the source.
Concurrent external dependency changes cause a retry; current references are never
silently detached. Native host definitions remain under the agents/install procedure.

## Explicit legacy migration

Read `agents.catalog_migration_plan` with no arguments. It returns catalog record count,
legacy instruction presence, their revisions and one aggregate `revision`. Execute
`agents.catalog_migrate` with `expected_revision` equal to that aggregate revision only
when migration is requested. Stale plans and conflicting existing files are rejected.

Migration writes profile/team files and the common main-agent instruction/reference.
It retains exact legacy SQL rows under cursor internal:catalog-legacy-backup and leaves
config/INSTRUCTIONS.md intact. Interrupted exports can resume when existing files match;
conflicting files require explicit reconciliation. SQL and RAG are derived afterward.
No source export or native-host installation occurs merely by restarting the service.

For an empty or whitespace-only profile/team instruction body, semantic discovery uses
only the title and description as derived search text. Source bytes and executor/team
instructions stay empty. Its vector revision hashes that actual discovery text, so a title
or description edit triggers reembedding; other metadata/path changes retain the vector.
