# Create or edit profiles and teams

Read agents.instructions_read for applicable main-agent rules. Inspect the relevant catalog
and full records before editing. Use agents.record_save: provide expected_revision for an
existing record; omit it for a new ID. The revision protects the complete source file. Preserve unrelated rules. Show the intended changes
and follow the user's actual request; a request to discuss a profile does not save one.

The source is data/profiles/*.md or data/teams/*.md. YAML holds stable id, type, title,
description and model/settings or roles; the body holds complete instructions. Files have
meaningful names. Team profile bindings use Obsidian wikilinks to actual files. External
edits, moves and deletes are supported; broken links are reported for explicit repair.
Do not silently rename files or repair references while making an unrelated change.

A profile has purpose, model/settings and optional executor instructions. A team has role
bindings to profiles plus optional team instructions. Use descriptions
that make role selection possible. Main-agent routing/concurrency rules belong in the
separate instruction edited through agents/instructions, not copied into every profile.
Do not invent a default-team setting. Record updates do not launch participants.

After a requested profile change, use agents/install to reconcile its known installations
in the selected environments through native tools/configuration. Do not silently update
other machines or every installed client. Report saved catalog revision separately from
installed and host-loaded revisions; unavailable targets remain pending. Team membership
changes do not require rewriting an unchanged executor profile.

For a requested profile removal, read the current record and call agents.profile_delete
with id and expected_revision. A blocked result lists team
references: resolve only the dependencies authorized by the user, then retry. Never
automatically detach references or stop sessions. A deleted result confirms removal from
the catalog and shared RAG; RAG cleanup failures retain the source file for retry. A revision
conflict requires rereading. Team deletion is not supported by this operation. Clean only verified owned native definitions
under agents/install, preserving modified files and running sessions. An absent search
result or unreachable MCP is not evidence that a profile was deleted.

On revision conflict reread and reconcile. Verify saved content and report pending indexing
honestly. SQL/RAG are derived from the Markdown source through shared Core synchronization; never write module tables directly.
Malformed or unreadable files stop reconciliation. Inspect agents.status for source and
reference errors. Existing SQL catalogs require the explicit agents.catalog_migration_plan
and agents.catalog_migrate operations; startup never restores source files from SQL.
