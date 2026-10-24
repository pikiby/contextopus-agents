"""Real Core installation/child process with deterministic embeddings."""
import json
import shutil
import time
from pathlib import Path

import pytest
from contextopus.core.embeddings import default_config
from contextopus.core.resources import ProcessResources
from contextopus.startup import Application


ROOT = Path(__file__).resolve().parents[1]


class Provider:
    def embed(self, texts, purpose="document"):
        return [[1., 0.] for _ in texts]
    def tokenizer(self):
        return lambda text, **kw: {"input_ids": text.split()}
    def close(self):
        pass


@pytest.fixture
def app(tmp_path):
    shutil.copytree(ROOT / "module", tmp_path / "modules/agents")
    resources = ProcessResources(provider_factory=lambda config: Provider())
    with Application(tmp_path, discover=False, resources=resources) as application:
        config = default_config()
        config["profile"]["dimensions"] = 2
        application.index.embeddings = config
        with application.layout.guard():
            application.index._generic_table(create=True)
        application.execute("core.module_install", {"module": "agents"})
        application.module_manager.start_services()
        yield application
    resources.close()


def wait(check):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            result = check()
        except Exception as exc:
            if "Unknown deliveries ID" not in str(exc):
                raise
            result = False
        if result:
            return result
        time.sleep(.05)
    raise AssertionError("condition did not become true")


def profile(app):
    return app.execute("agents.record_save", {"record": {
        "id": "reviewer", "kind": "profile", "title": "Reviewer", "description": "Review a code change",
        "body": {"model": "local/test", "instructions": "Inspect evidence"}}})


def test_catalog_revision_shared_rag_and_lifecycle(app):
    saved = profile(app)
    def indexed():
        status = app.query("agents.status")
        assert not status["errors"], status
        return status["pending_index"] == 0
    wait(indexed)
    found = app.query("agents.search", {"query": "review a change"})
    assert [r["id"] for r in found["results"]] == ["reviewer"]
    assert "excerpt" not in found["results"][0]
    assert found["diagnostics"]["scope"]["module"] == "agents"
    assert found["diagnostics"]["algorithm"] == "distance_jump"
    with pytest.raises(Exception, match="revision"):
        profile(app)
    team = {"id": "engineering", "kind": "team", "title": "Engineering", "description": "Review work",
            "body": {"roles": {"review": {"profile": "reviewer"}}}}
    app.execute("agents.record_save", {"record": team})
    assert app.query("agents.team_resolve", {"team": "engineering", "role": "review"})["profile"]["body"]["model"] == "local/test"
    app.execute("core.module_disable", {"module": "agents"})
    app.execute("core.module_enable", {"module": "agents"})
    app.module_manager.start_services()
    assert app.query("agents.read", {"id": "reviewer"})["revision"] == saved["revision"]
    assert app.module_storage.for_module("agents").path.name == "agents.sqlite3"


def test_schema_rejects_unknown_fields_and_query_cannot_mutate(app):
    with pytest.raises(Exception):
        app.execute("agents.record_save", {"record": {"id": "bad", "kind": "profile", "secret": "no"}})
    with pytest.raises(Exception):
        app.query("agents.record_save", {"record": {}})


def test_built_zip_uses_standard_source_install(tmp_path):
    import subprocess
    import sys
    package = tmp_path / "agents.zip"
    subprocess.run([sys.executable, str(ROOT / "scripts/build.py"), "--output", str(package)], check=True)
    resources = ProcessResources(provider_factory=lambda config: Provider())
    try:
        with Application(tmp_path / "root", discover=False, resources=resources) as app:
            preview = app.query("core.module_source_plan", {"module": "agents", "source": str(package)})
            app.execute("core.module_install", {"module": "agents", "source": str(package), "source_revision": preview["revision"]})
            app.module_manager.start_services()
            assert (tmp_path / "root/modules/agents/module.json").is_file()
            assert app.query("agents.list") == []
    finally:
        resources.close()


def test_main_agent_instructions_and_team_selection(app, tmp_path):
    initial = app.query('agents.instructions_read')
    assert initial['source'] == 'default'
    target = Path(initial['path'])
    assert not target.exists()
    content = '# Routing\n\n$a development\nRun at most two workers.\n'
    saved = app.execute('agents.instructions_save', {'content': content, 'expected_revision': initial['revision']})
    assert saved['source'] == 'user' and saved['content'] == content
    assert target.is_file() and target.read_text().endswith(content)
    assert app.query('agents.instructions_read')['content'] == content
    assert (tmp_path / 'modules/agents/data/instructions/main.md').is_file()
    with pytest.raises(Exception, match='revision'):
        app.execute('agents.instructions_save', {'content': 'lost update', 'expected_revision': initial['revision']})
    with pytest.raises(Exception):
        app.query('agents.instructions_save', {'content': 'forbidden', 'expected_revision': saved['revision']})
    profile(app)
    app.execute('agents.record_save', {'record': {'id': 'development', 'kind': 'team',
        'title': 'Development', 'description': 'Development work',
        'body': {'roles': {'review': {'profile': 'reviewer'}}, 'instructions': 'Check evidence'}}})
    team = app.query('agents.team_read', {'team': 'development'})
    assert team['members'] == [{'role': 'review', 'profile': 'reviewer', 'title': 'Reviewer', 'description': 'Review a code change'}]
    assert team['instructions'] == 'Check evidence'
    app.execute('core.module_disable', {'module': 'agents'})
    app.execute('core.module_enable', {'module': 'agents'})
    app.module_manager.start_services()
    assert app.query('agents.instructions_read')['content'] == content
    # The ordinary update must preserve config/, including user routing rules.
    app.execute('core.module_update', {'module': 'agents', 'source': str(ROOT / 'module')})
    app.module_manager.start_services()
    assert app.query('agents.instructions_read')['revision'] == saved['revision']
    assert app.query('agents.team_read', {'team': 'development'})['members'] == team['members']


def test_main_rules_external_edit_and_broken_reference_fail_closed(app, tmp_path):
    initial = app.query('agents.instructions_read')
    saved = app.execute('agents.instructions_save', {'content': 'Original rules', 'expected_revision': initial['revision']})
    target = Path(saved['path'])
    target.write_text(target.read_text().replace('Original rules', 'External rules'), encoding="utf-8", newline="")
    current = app.query('agents.instructions_read')
    assert current['content'] == 'External rules' and current['revision'] != saved['revision']
    with pytest.raises(Exception, match='revision'):
        app.execute('agents.instructions_save', {'content':'Lost update', 'expected_revision':saved['revision']})
    reference = tmp_path / 'modules/agents/data/instructions/main.md'
    assert '[[agents-main]]' in reference.read_text()
    target.rename(target.with_name('renamed-rules.md'))
    # Stable Core instruction ID is still agents-main, so replace the reference
    # with an actual path to exercise a broken file wikilink explicitly.
    reference.write_text(reference.read_text().replace('[[agents-main]]', '[[missing-rules]]'), encoding="utf-8", newline="")
    with pytest.raises(Exception, match='Missing or ambiguous instruction'):
        app.query('agents.instructions_read')
    assert 'missing-rules' in reference.read_text()


def test_legacy_rules_migration_is_explicit_and_retains_original(app, tmp_path):
    legacy = tmp_path / 'modules/agents/config/INSTRUCTIONS.md'
    legacy.write_text('# Legacy routing\nUse reviewer only.\n', encoding="utf-8", newline="")
    with pytest.raises(Exception, match='require agents.catalog_migrate'):
        app.query('agents.instructions_read')
    plan = app.query('agents.catalog_migration_plan')
    assert plan['instructions']['required']
    common = tmp_path / 'core/instructions/agents-main.md'
    assert not common.exists()
    legacy.write_text('# Legacy routing\nUse reviewer and tester.\n', encoding="utf-8", newline="")
    with pytest.raises(Exception, match='revision'):
        app.execute('agents.catalog_migrate', {'expected_revision':plan['revision']})
    plan = app.query('agents.catalog_migration_plan')
    result = app.execute('agents.catalog_migrate', {'expected_revision':plan['revision']})
    assert result['instructions']['status'] == 'migrated'
    assert result['instructions']['legacy_preserved'] and legacy.is_file()
    assert app.query('agents.instructions_read')['content'] == legacy.read_text()
    assert common.is_file()
    app.execute('core.module_disable', {'module':'agents'})
    app.execute('core.module_enable', {'module':'agents'})
    app.module_manager.start_services()
    assert app.query('agents.instructions_read')['content'] == legacy.read_text()


def test_main_rules_return_full_required_chain_and_guard_dependency_edits(app, tmp_path):
    initial = app.query('agents.instructions_read')
    saved = app.execute('agents.instructions_save', {'content':'Primary rules', 'expected_revision':initial['revision']})
    primary = Path(saved['path'])
    dependency = primary.parent / 'required-safety.md'
    dependency.write_text('---\nid: required-safety\ntype: instruction\ntitle: Required safety\n---\nRead this entire required instruction.\n', encoding="utf-8", newline="")
    primary.write_text(primary.read_text().replace('type: instruction\n', 'type: instruction\ninstructions:\n  safety: "[[required-safety]]"\n'), encoding="utf-8", newline="")
    current = app.query('agents.instructions_read')
    assert [document['id'] for document in current['documents']] == ['required-safety']
    assert current['documents'][0]['content'] == 'Read this entire required instruction.\n'
    assert current['content'] == 'Primary rules' and current['required_revision']
    dependency.write_text(dependency.read_text().replace('entire required instruction', 'new complete required instruction'), encoding="utf-8", newline="")
    changed = app.query('agents.instructions_read')
    assert changed['document_revision'] == current['document_revision']
    assert changed['required_revision'] != current['required_revision'] and changed['revision'] != current['revision']
    with pytest.raises(Exception, match='revision'):
        app.execute('agents.instructions_save', {'content':'Stale edit', 'expected_revision':current['revision']})
    updated = app.execute('agents.instructions_save', {'content':'Updated primary rules', 'expected_revision':changed['revision']})
    assert updated['documents'][0]['content'] == 'Read this new complete required instruction.\n'
    assert updated['content'] == 'Updated primary rules'
    assert 'required-safety' in primary.read_text()
    dependency.unlink()
    with pytest.raises(Exception, match='Missing or ambiguous instruction'):
        app.query('agents.instructions_read')


def test_communication_is_not_exposed_or_replayed(app):
    manifest = json.loads((ROOT / 'module/module.json').read_text(encoding='utf-8'))
    names = {op['name'] for op in manifest['operations']}
    removed = {'send', 'session_bind', 'session_create', 'session_read', 'sessions',
               'event', 'connection_save', 'subscription_save', 'delivery_read'}
    assert not names.intersection('agents.' + name for name in removed)
    assert not (ROOT / 'module/package/skills/a-sessions').exists()
    # Existing durable data survives update; it must not become active work.
    sql = app.module_storage.for_module('agents')
    sql.execute('agents', 'INSERT INTO "{{module}}::deliveries" (id,session,text,state,created) VALUES (?,?,?,?,?)',
                ['legacy-message', 'old-session', 'Do not deliver', 'pending', 0])
    app.execute('core.module_update', {'module':'agents', 'source':str(ROOT / 'module')})
    app.module_manager.start_services()
    assert set(app.query('agents.status')['workers']) == {'agents-index'}
    assert sql.query('agents', 'SELECT state FROM "{{module}}::deliveries" WHERE id=?', ['legacy-message'])['rows'] == [{'state':'pending'}]
    for name in removed:
        with pytest.raises(Exception):
            app.execute('agents.' + name, {})
    with pytest.raises(Exception, match='profile references only'):
        app.execute('agents.record_save', {'record': {'id':'legacy-team','kind':'team',
            'title':'Legacy', 'description':'No session binding',
            'body':{'roles':{'worker':{'session':'old-session'}}}}})
