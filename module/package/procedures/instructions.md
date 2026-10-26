---
operations: ["agents.catalog_migrate", "agents.catalog_migration_plan", "agents.instructions_read", "agents.instructions_save"]
---

# Main-agent instructions

This procedure reads or edits the module-wide main-agent instruction referenced by
data/instructions/main.md; the default Core document is core/instructions/agents-main.md.
For creating, editing or binding rules of a selected Workspace context, use Workspace's
instructions procedure, regardless of the rules' subject. Do not replace that path with
an edit of this module-wide instruction. Ordinary Agents use does not require Workspace.
The body is one complete UTF-8 Markdown instruction; the outer YAML is metadata.
The packaged default is returned until a reference is explicitly saved; reading creates
no source file. Broken references and malformed sources are errors, not default fallbacks.

Read through agents.instructions_read. Read every complete record in documents in its
returned dependency order as well as the primary content. The primary appears only in
content; documents contains only additional required rules. YAML instructions mappings
require those documents; semantic search snippets are insufficient. The aggregate revision
protects the reference, primary rules and every required dependency. Keep main-agent rules
separate from Workspace instructions, team instructions and participant profiles.

## Save and verify

On an explicit change request, read the current text/revision, prepare and show the actual
changed passages, then save the requested content through agents.instructions_save with
expected_revision. This changes only the primary returned by agents.instructions_read;
it must not be used to replace another instruction named by the user. For another
document, follow its owning procedure and approval policy. The user's direct change
request authorizes this main-instruction change; ask only for
missing substantive choices, not invented approval policies. Preserve unrelated user text.
On revision conflict reread and reconcile; never overwrite a concurrent change blindly.
Updates to module code preserve data/ and the common instruction library. Re-read rules after editing them. Reporting rules
as saved requires a successful save and a verifying read of the content and direct links.
This procedure never starts workers.

Legacy config/INSTRUCTIONS.md is never silently migrated. Inspect
agents.catalog_migration_plan and use agents.catalog_migrate with its current revision
only when the user requested migration. The old file remains preserved afterward.
