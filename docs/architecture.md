# Architecture

Agents is a standard optional folder module. Its manifest declares operations,
procedures, four skills, versioned SQL migrations and a persistent child service.
Core owns service lifetime, independent module SQL, documents, instructions,
embeddings and RAG. There is no module-specific branch in Core.

Catalog and instruction operations use Core's child SDK. A background indexing
worker reconciles complete valid file snapshots and retries pending RAG writes.
Queries read current files; full-file revisions protect edits. Metadata-only
changes reuse vectors where discovery text is unchanged. Empty prompts use title
and description for discovery without inventing executor instructions.

Main-agent rules are shared Core instruction documents referenced by a small
module file. Reads return the primary prompt once and all required dependencies.
The combined revision protects edits against changes anywhere in that chain.

Native creation, registration and launch are performed by the main agent through
the host's applicable skills and tools. Registration is not a universal prerequisite;
the host may support direct profile handoff. Contextopus only manages its own records.
There are no delivery adapters, chat listeners or session operations.
Legacy experimental communication tables remain inert for migration compatibility;
they are not read, replayed or deleted by this release. The original version-one
migration is retained byte-for-byte so installed roots can update safely.
Legacy team session bindings remain readable as explicit reference errors; new
team writes accept profiles only. No existing session is stopped or replaced.
