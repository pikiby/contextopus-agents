"""Real file edits, moves and deletes drive derived SQL/RAG; failures fail closed."""
import json
from pathlib import Path

import pytest

from test_profile_delete import catalog, create, vectors
from agents.catalog import Catalog
from agents.storage import encoded


def test_files_are_authority_and_body_is_the_only_embedding_text(catalog, monkeypatch):
    saved = create(catalog)
    path = Path(saved['path'])
    assert path.name == 'runner.md'
    assert 'model: local/test' in path.read_text()
    captured = []
    original = catalog.core.embeddings.embed_documents
    def embed(**kwargs):
        captured.extend(kwargs['texts'])
        return original(**kwargs)
    monkeypatch.setattr(catalog.core.embeddings, 'embed_documents', embed, raising=False)
    catalog.index_one()
    assert captured == ['Report evidence']
    path.write_text(path.read_text().replace('Report evidence', 'Read actual files'))
    read = catalog.read('runner')
    assert read['body']['instructions'] == 'Read actual files'
    assert read['revision'] != saved['revision']
    # Read did not modify or rewrite the SQL projection itself.
    assert json.loads(catalog.store.one('records', 'runner')['body'])['instructions'] == 'Report evidence'
    assert catalog.search('checks')['results'] == []
    catalog.index_one()
    assert catalog.search('checks')['results'][0]['revision'] == read['revision']
    assert captured[-1] == 'Read actual files'


def test_metadata_and_path_refresh_reuses_vectors(catalog, monkeypatch):
    saved = create(catalog)
    catalog.index_one()
    path = Path(saved['path'])
    raw = path.read_text().replace('title: Runner', 'title: New Runner')
    renamed = path.with_name('readable-name.md')
    path.rename(renamed)
    renamed.write_text(raw)
    def forbidden(**kwargs):
        raise AssertionError('Metadata/path-only update must not embed')
    monkeypatch.setattr(catalog.core.embeddings, 'embed_documents', forbidden, raising=False)
    assert catalog.index_one() is False
    read = catalog.read('runner')
    assert read['title'] == 'New Runner' and read['path'] == str(renamed)
    assert vectors(catalog)['revisions']
    assert catalog.search('checks')['results'][0]['title'] == 'New Runner'


def test_renamed_profile_reports_broken_wikilink_without_rewriting_team(catalog):
    profile = create(catalog)
    team = catalog.save(dict(id='checks',kind='team',title='Checks',description='Checks',
                             body={'roles': {'test': {'profile': 'runner'}},'instructions':'Check it'}))
    team_path = Path(team['path'])
    original = team_path.read_bytes()
    assert "[[modules/agents/data/profiles/runner]]" in original.decode()
    path = Path(profile['path'])
    path.rename(path.with_name('new-runner.md'))
    assert catalog.read('runner')['id'] == 'runner'
    members = catalog.team_read('checks')['members']
    assert members[0]['error'] == 'Missing profile wikilink'
    with pytest.raises(ValueError, match='Missing role reference'):
        catalog.resolve('checks', 'test')
    assert team_path.read_bytes() == original
    team_path.write_text(original.decode().replace('[[modules/agents/data/profiles/runner]]', '[[modules/agents/data/profiles/new-runner|Runner]]'))
    assert catalog.resolve('checks', 'test')['profile']['id'] == 'runner'


def test_external_deletion_never_resurrects_after_restart(catalog):
    saved = create(catalog)
    catalog.index_one()
    Path(saved['path']).unlink()
    catalog.index_one()
    assert vectors(catalog)['missing'] == ['runner']
    restarted = Catalog(catalog.core, catalog.store, catalog.writer)
    restarted.index_one()
    assert restarted.list() == []
    assert not Path(saved['path']).exists()


@pytest.mark.parametrize('failure', ['invalid', 'missing-directory', 'duplicate-id', 'symlink'])
def test_failed_scan_never_infers_deletion(catalog, failure):
    saved = create(catalog)
    catalog.index_one()
    path = Path(saved['path'])
    raw = path.read_text()
    path.unlink()
    if failure == 'invalid':
        (path.parent / 'broken.md').write_text('---\nid: broken\ntype: profile\n---\nInvalid schema')
    elif failure == 'missing-directory':
        path.parent.rmdir()
    elif failure == 'duplicate-id':
        (path.parent / 'one.md').write_text(raw)
        (path.parent / 'two.md').write_text(raw)
    else:
        (path.parent / 'linked.md').symlink_to('/etc/passwd')
    with pytest.raises(Exception):
        catalog.index_one()
    assert catalog.store.one('records', 'runner')['id'] == 'runner'
    assert vectors(catalog)['revisions']


def test_explicit_sql_migration_preserves_legacy_and_never_runs_on_start(catalog):
    body = {'model':'local/test', 'instructions':'Legacy instructions'}
    catalog.store.sql.execute('INSERT INTO "{{module}}::records" (id,kind,title,description,body,revision) VALUES (?,?,?,?,?,?)',
        ['legacy','profile','Legacy reviewer','Legacy checks',encoded(body),'old-revision'])
    with pytest.raises(ValueError, match='requires agents.catalog_migrate'):
        catalog.index_one()
    plan = catalog.migration_plan()
    assert plan['required'] and plan['records'] == 1
    with pytest.raises(ValueError, match='revision'):
        catalog.migrate('stale')
    result = catalog.migrate(plan['revision'])
    assert result['status'] == 'migrated'
    saved = catalog.read('legacy')
    assert saved['body'] == body and Path(saved['path']).name.startswith('legacy-reviewer--')
    backup = catalog._cursor('internal:catalog-legacy-backup')
    assert backup[0]['revision'] == 'old-revision'
    assert json.loads(backup[0]['body']) == body
    Path(saved['path']).unlink()
    Catalog(catalog.core, catalog.store, catalog.writer).index_one()
    assert catalog.store.rows('SELECT * FROM "{{module}}::records"') == []
    assert not Path(saved['path']).exists()


def test_tool_can_repair_a_broken_file_binding(catalog):
    saved = create(catalog)
    team = catalog.save(dict(id='team',kind='team',title='Team',description='Team',
                             body={'roles':{'test':{'profile':'runner'}}}))
    path = Path(saved['path'])
    path.rename(path.with_name('renamed-runner.md'))
    current = catalog.read('team')
    assert catalog.reference_errors
    record = {key:current[key] for key in ('id','kind','title','description','body')}
    record['body']['roles']['test'] = {'profile':'runner'}
    repaired = catalog.save(record, expected_revision=current['revision'])
    assert 'renamed-runner' in Path(repaired['path']).read_text()
    assert catalog.resolve('team','test')['profile']['id'] == 'runner'


def test_deletion_rechecks_external_dependency_changes_after_rag_cleanup(catalog, monkeypatch):
    saved = create(catalog)
    catalog.index_one()
    original = catalog.core.rag.delete_document
    def change_source(**kwargs):
        result = original(**kwargs)
        # An external editor does not share the tool writer lock.
        team_dir = Path(saved['path']).parent.parent / 'teams'
        (team_dir / 'new-team.md').write_text('---\nid: new-team\ntype: team\ntitle: Team\ndescription: Checks\nroles:\n  test:\n    profile: "[[modules/agents/data/profiles/runner]]"\n---\nCheck evidence')
        return result
    monkeypatch.setattr(catalog.core.rag, 'delete_document', change_source, raising=False)
    with pytest.raises(ValueError, match='Catalog changed during deletion'):
        catalog.delete_profile('runner', saved['revision'])
    assert Path(saved['path']).is_file()
    monkeypatch.setattr(catalog.core.rag, 'delete_document', original, raising=False)
    blocked = catalog.delete_profile('runner', saved['revision'])
    assert blocked['status'] == 'blocked' and blocked['references'][0]['kind'] == 'team'
    while catalog.index_one():
        pass
    assert vectors(catalog)['revisions']
