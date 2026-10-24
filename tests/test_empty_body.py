"""Production-shaped provider rejects blank text; empty source bodies stay valid."""
from pathlib import Path

import pytest
from test_profile_delete import catalog, create, Provider


def settle(catalog):
    for _ in range(10):
        if not catalog.index_one():
            return
    raise AssertionError('index did not settle')


@pytest.mark.parametrize('kind', ['profile', 'team'])
@pytest.mark.parametrize('instructions', [None, '\n \t'])
def test_empty_body_discovery_and_metadata_edits_reembed_without_source_rewrite(catalog, monkeypatch, kind, instructions):
    captured = []
    def strict(self, texts, purpose='document'):
        if not isinstance(texts, list) or not texts or any(not isinstance(text,str) or not text.strip() for text in texts):
            raise ValueError('Embedding input must be a list of nonempty strings')
        if purpose == 'document':
            captured.extend(texts)
        return [[1.,0.] for _ in texts]
    monkeypatch.setattr(Provider, 'embed', strict)
    if kind == 'team':
        create(catalog)
        body = {'roles': {'review': {'profile':'runner'}}}
    else:
        body = {'model':'local/test'}
    if instructions is not None:
        body['instructions'] = instructions
    record = {'id':'empty','kind':kind,'title':'Purpose only','description':'Discover this role','body':body}
    saved = catalog.save(record)
    path = Path(saved['path'])
    before = path.read_bytes()
    settle(catalog)
    assert path.read_bytes() == before
    assert 'Purpose only\nDiscover this role' in captured
    assert catalog.read('empty')['body'].get('instructions','') == (instructions or '')
    assert catalog.pending_count() == 0
    def vector_revision():
        return catalog.core.rag.vector_revisions(collection='catalog', object_ids=['empty'])['revisions']
    previous = vector_revision()
    for old,new in [('title: Purpose only','title: Renamed purpose'),
                    ('description: Discover this role','description: New discovery purpose')]:
        path.write_text(path.read_text().replace(old,new))
        changed = path.read_bytes()
        read = catalog.read('empty')
        expected = read['title'] + '\n' + read['description']
        assert catalog.pending_count() == 1
        before_count = captured.count(expected)
        settle(catalog)
        assert captured.count(expected) == before_count + 1
        assert vector_revision() != previous
        previous = vector_revision()
        assert path.read_bytes() == changed
        assert catalog.read('empty')['body'].get('instructions','') == (instructions or '')
        assert catalog.pending_count() == 0
        found = catalog.search('discovery', kind=kind)
        assert 'empty' in {item['id'] for item in found['results']}
