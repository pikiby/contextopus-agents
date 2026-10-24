# Verification

The test suite uses temporary roots, the actual Core module installer and child
process, module SQL and shared RAG with deterministic embeddings. It checks file
authority, revisions, profile/team resolution, semantic filtering, external edits
and deletions, broken links, explicit legacy migration and instruction dependencies.

Communication removal is checked at the manifest and dispatch boundaries. Only
the catalog indexing worker starts; old communication rows are left untouched.
ZIP installation and module update preserve user profiles and main-agent rules.

These checks do not prove model quality, native permissions or compatibility with
every client version. Native profile setup must verify the selected host's loaded
configuration separately. There are no live messaging tests in this release.
