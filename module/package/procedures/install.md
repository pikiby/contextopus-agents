# Manage native profile installations

This procedure is shared by every host. The main agent performs it using that host's
existing configuration tools, CLI or editable agent definitions. No permanent sync service
or host-specific executable adapter is required. Contextopus remains the profile source;
this procedure does not itself write client files or launch models.

## Select and inspect

1. Read the full current profile through agents.read/team_resolve. Establish the target
   host, version and scope (user/project/profile home) from the actual environment and
   request. Do not assume Codex, infer model aliases, or configure unrelated clients.
2. Inspect the host's existing agent-management facilities and current official docs when
   support is unknown. See agents/hosts for starting references, not a universal schema.
   Determine discovery/reload behavior and which prompt, model, reasoning and permissions
   it actually supports. Profile settings are requests, not proof of enforcement.
3. Prefer the host's native management operation. Otherwise prepare its native config file.
   Keep the full profile instructions verbatim and map model/settings explicitly. A model-only
   profile needs no invented role prompt; if a host requires one, explain the minimal neutral
   wrapper. Do not expand the profile record schema with invented permission fields.
   Unsupported required settings or hard restrictions block launch. Text prohibitions do
   not substitute for permissions. A profile cannot override higher-priority host rules.

## Ownership and revisions

Use host-provided identity/revision metadata when available. For a dedicated generated
text file, add a valid native comment containing Contextopus work_root, profile ID,
profile revision and SHA-256 of the exact UTF-8 payload after that first comment line.
This identifies the source and detects local edits without a second profile database.
Use the host's supported comment syntax, not a foreign field that its loader might reject.
For shared/no-comment configuration, require a supported ownership/revision mechanism;
otherwise show and reconcile the exact target entry manually, without claiming automatic
ownership detection. Never replace an entire shared configuration for one profile.

Before writing, reread source revision and destination bytes. Refuse an unrelated name
collision or an owned file whose payload hash changed; show the conflict instead of
merging or discarding user edits silently. Preserve the previous file until verification.
Use atomic replacement when supported. For a new file, do not overwrite an existing path.
If identity and payload already match the current profile, do nothing.

After a profile edit, update only its known selected installations. After an authorized
removal and reference checks, remove only matching unchanged owned definitions and their
own registration entries. Do not delete directories, unrelated profiles or live sessions.
Disconnected hosts and unknown installations cannot be claimed synchronized. This version
has no central installation registry; identify managed files through native metadata in
the selected host/scope and report unvisited environments as unverified.

## Verify and launch

Validate syntax and compare decoded prompt/model/settings against the fetched profile.
Use the host's native discovery/config-inspection mechanism to confirm its loaded identity;
a file existing on disk is insufficient. Distinguish file installed from host loaded and
model execution tested. Request a reload only if needed, preserving ongoing work and the
user's GUI permission boundary. Never restart unrelated sessions automatically.

Run only the authorized task through the host's native agent launcher by that verified
name. Do not silently fall back to a generic agent if the installed profile is not visible.
A user may choose explicit verbatim prompt handoff if no native profile support exists,
provided required restrictions/settings are supported. After launch check result evidence.
Existing workers keep their original prompt; updates apply to subsequent loaded launches.

Recheck after profile edits, host configuration/version changes or lost verification.
Do not reread every rule or reinstall unchanged files on every task step.
