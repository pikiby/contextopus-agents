# Main-agent instructions

This is the editable instruction for the main agent managing a team, not an executor
profile or the built-in procedure. Core stores it at core/instructions/agents-main.md.
The module's data/instructions/main.md contains a YAML wikilink to that common document.
The body is one complete UTF-8 Markdown instruction; the outer YAML is metadata.
The packaged default is returned until a reference is explicitly saved; reading creates
no source file. Broken references and malformed sources are errors, not default fallbacks.

Read through agents.instructions_read. Read every complete record in documents in its
returned dependency order as well as the primary content. The primary appears only in
content; documents contains only additional required rules. YAML instructions mappings
require those documents; semantic search snippets are insufficient. The aggregate revision
protects the reference, primary rules and every required dependency. A simple rule can be `$a development`; the user
may instead write arbitrary routing, delegation, concurrency, interaction and acceptance
rules. Do not require structured routing tables or software counters. Keep these rules
separate from Workspace instructions, team instructions and participant profiles.

On an explicit change request, read the current text/revision, prepare and show the actual
changed passages, then save the requested content through agents.instructions_save with
expected_revision. The user's direct change request authorizes that change; ask only for
missing substantive choices, not invented approval policies. Preserve unrelated user text.
On revision conflict reread and reconcile; never overwrite a concurrent change blindly.
Updates to module code preserve data/ and the common instruction library. Re-read rules after editing them. Reporting rules
as saved requires a successful save and a verifying read. This procedure never starts workers.

Legacy config/INSTRUCTIONS.md is never silently migrated. Inspect
agents.catalog_migration_plan and use agents.catalog_migrate with its current revision
only when the user requested migration. The old file remains preserved afterward.
