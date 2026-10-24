"""Profile deletion against real Core SQL/RAG with deterministic embeddings."""
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'module/package'))
from agents.catalog import Catalog
from agents.storage import Store, encoded
from contextopus.core.embeddings import default_config
from contextopus.core.module_management.child import StorageClient, NamespaceClient
from contextopus.core.module_management.core_access import ModuleCoreAccess
from contextopus.core.module_storage import ModuleStorage
from contextopus.core.rag import RagIndex
from contextopus.core.resources import ProcessResources
from contextopus.core.storage import StorageLayout


class Provider:
    def embed(self, texts, purpose='document'):
        return [[1., 0.] for _ in texts]

    def tokenizer(self):
        return lambda text, **kw: {'input_ids': text.split()}

    def close(self):
        pass


@pytest.fixture
def catalog(tmp_path):
    layout = StorageLayout(tmp_path / 'root')
    layout.configuration.mkdir(parents=True)
    (layout.configuration / 'layout.json').write_text('{}')
    resources = ProcessResources(provider_factory=lambda config: Provider())
    index = RagIndex(layout, resources)
    config = default_config()
    config['profile']['dimensions'] = 2
    index.embeddings = config
    with layout.guard():
        index._generic_table(create=True)
    storage = ModuleStorage(layout)
    module = Path(__file__).resolve().parents[1] / 'module'
    contract = json.loads((module / 'module.json').read_text())['storage']
    plan = storage.prepare('agents', contract, module / 'package')
    storage.apply('agents', contract, module / 'package', plan['revision'])
    access = ModuleCoreAccess(SimpleNamespace(module_storage=storage, layout=layout, index=index,
                                             resources=resources), 'agents', storage_declared=True, rag_declared=True)
    core = SimpleNamespace(storage=StorageClient(access, 'storage'),
                           rag=NamespaceClient(access, 'rag'), embeddings=NamespaceClient(access, 'embeddings'),
                           documents=NamespaceClient(access, 'documents'), instructions=NamespaceClient(access, 'instructions'))
    writer = threading.RLock()
    try:
        yield Catalog(core, Store(core.storage, writer), writer)
    finally:
        access.close()
        resources.close()


def create(catalog, ident='runner'):
    return catalog.save(dict(id=ident, kind='profile', title='Runner', description='Runs checks',
                             body={'model':'local/test','instructions':'Report evidence'}))


def vectors(catalog):
    return catalog.core.rag.vector_revisions(collection='catalog', object_ids=['runner'])


def test_delete_removes_profile_and_real_rag(catalog):
    saved = create(catalog)
    catalog.index_one()
    assert catalog.search('checks')['results'][0]['id'] == 'runner'
    assert catalog.delete_profile('runner', saved['revision'])['status'] == 'deleted'
    with pytest.raises(ValueError, match='Unknown records ID'):
        catalog.read('runner')
    assert catalog.search('checks')['results'] == []
    assert vectors(catalog)['missing'] == ['runner']
    assert not vectors(catalog)['revisions']
    with pytest.raises(ValueError, match='Unknown records ID'):
        catalog.delete_profile('runner', saved['revision'])


def test_stale_revision_preserves_source_and_vector(catalog):
    saved = create(catalog)
    catalog.index_one()
    before = vectors(catalog)
    with pytest.raises(ValueError, match='revision'):
        catalog.delete_profile('runner', 'stale')
    assert catalog.read('runner')['revision'] == saved['revision']
    assert vectors(catalog) == before


def test_references_block_without_changes(catalog):
    saved = create(catalog)
    catalog.save(dict(id='team', kind='team', title='Team', description='Checks',
                      body={'roles':{'test':{'profile':'runner'}}}))
    result = catalog.delete_profile('runner', saved['revision'])
    assert result['status'] == 'blocked'
    assert {r['kind'] for r in result['references']} == {'team'}
    assert catalog.read('runner')['revision'] == saved['revision']
    with pytest.raises(ValueError, match='Expected a profile'):
        catalog.delete_profile('team', catalog.read('team')['revision'])


def test_index_failure_retains_profile_and_retry_succeeds(catalog, monkeypatch):
    saved = create(catalog)
    catalog.index_one()
    original = catalog.core.rag.delete_document
    def fail(**kwargs):
        raise RuntimeError('simulated RAG failure')
    monkeypatch.setattr(catalog.core.rag, 'delete_document', fail, raising=False)
    with pytest.raises(RuntimeError, match='simulated'):
        catalog.delete_profile('runner', saved['revision'])
    assert catalog.read('runner')['revision'] == saved['revision']
    assert catalog.read('runner')['indexed_revision'] is None
    monkeypatch.setattr(catalog.core.rag, 'delete_document', original)
    assert catalog.delete_profile('runner', saved['revision'])['status'] == 'deleted'


def test_inflight_embedding_cannot_resurrect_deleted_profile(catalog, monkeypatch):
    saved = create(catalog)
    entered, resume = threading.Event(), threading.Event()
    original = catalog.core.embeddings.embed_documents
    def pause(**kwargs):
        result = original(**kwargs)
        entered.set()
        assert resume.wait(5)
        return result
    monkeypatch.setattr(catalog.core.embeddings, 'embed_documents', pause, raising=False)
    errors = []
    def work():
        try:
            catalog.index_one()
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=work)
    thread.start()
    try:
        assert entered.wait(5)
        assert catalog.delete_profile('runner', saved['revision'])['status'] == 'deleted'
    finally:
        resume.set()
        thread.join(5)
    assert not thread.is_alive() and not errors
    assert vectors(catalog)['missing'] == ['runner']
    assert not vectors(catalog)['revisions']


def test_search_skips_vector_fetched_before_deletion(catalog, monkeypatch):
    saved = create(catalog)
    catalog.index_one()
    original = catalog.core.rag.search
    def search_then_delete(**kwargs):
        result = original(**kwargs)
        catalog.delete_profile('runner', saved['revision'])
        return result
    monkeypatch.setattr(catalog.core.rag, 'search', search_then_delete, raising=False)
    result = catalog.search('checks')
    assert result['results'] == [] and result['stale_results_omitted'] == 1
