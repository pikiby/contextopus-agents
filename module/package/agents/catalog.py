"""Markdown authority and replayable SQL/shared-RAG projections.

No startup path exports SQL back to files. Legacy SQL requires explicit migration.
"""
import json
import hashlib
import re
from pathlib import PurePosixPath
from .storage import encoded, revision


class Catalog:
    def __init__(self, core, store, writer):
        self.core, self.store, self.writer = core, store, writer
        self.documents = {}
        self.reference_errors = []
        self.link_errors = {}
        self.encoding_records = {}

    def _cursor(self, name):
        rows = self.store.rows('SELECT value FROM "{{module}}::cursors" WHERE source=?', [name])
        return json.loads(rows[0]['value']) if rows else None

    def _put_cursor(self, name, value, tx=None):
        (tx or self.store.sql).execute('INSERT INTO "{{module}}::cursors" VALUES (?,?) '
            'ON CONFLICT(source) DO UPDATE SET value=excluded.value', [name, encoded(value)])

    def _validate(self, record):
        if set(record) != {'id', 'kind', 'title', 'description', 'body'}:
            raise ValueError('Record requires id, kind, title, description and body')
        for name in ('id', 'title', 'description'):
            if not isinstance(record[name], str) or not record[name].strip():
                raise ValueError('Record requires text ' + name)
        body, kind = record['body'], record['kind']
        if not isinstance(body, dict) or len(encoded(body).encode()) > 32768:
            raise ValueError('Profile or team body must be an object within 32 KiB')
        if not isinstance(body.get('instructions', ''), str):
            raise ValueError('instructions must be text')
        if kind == 'profile':
            if set(body) - {'model', 'instructions', 'settings'} or not isinstance(body.get('model'), str) or not body['model'].strip():
                raise ValueError('Profile requires model and optional instructions/settings')
            if not isinstance(body.get('settings', {}), dict):
                raise ValueError('settings must be an object')
        elif kind == 'team':
            if set(body) - {'roles', 'instructions'} or not isinstance(body.get('roles'), dict) or not body['roles']:
                raise ValueError('Team requires a nonempty roles object')
            for name, role in body['roles'].items():
                if not isinstance(name, str) or not name or not isinstance(role, dict) or set(role) not in ({'profile'}, {'session'}):
                    raise ValueError('Each role requires one profile reference')
                if not all(isinstance(value, str) and value for value in role.values()):
                    raise ValueError('Role references must be nonempty text')
        else:
            raise ValueError('Unsupported record kind')
        return record

    def _decode(self, document, kind):
        metadata = document['metadata']
        allowed = {'id', 'type', 'title', 'description', 'model', 'settings'} if kind == 'profile' else {'id', 'type', 'title', 'description', 'roles'}
        if set(metadata) - allowed or metadata.get('type') != kind:
            raise ValueError('Unexpected metadata or document type in ' + document['location'])
        body = {'instructions': document['text']}
        if kind == 'profile':
            body['model'] = metadata.get('model')
            if 'settings' in metadata:
                body['settings'] = metadata['settings']
        else:
            roles = metadata.get('roles')
            if not isinstance(roles, dict):
                raise ValueError('Team requires roles')
            body['roles'] = {}
            for name, binding in roles.items():
                if not isinstance(binding, dict):
                    raise ValueError('Team roles require profile wikilinks or session IDs')
                binding = dict(binding)
                if 'profile' in binding:
                    link = binding['profile']
                    if not isinstance(link, str) or not re.fullmatch(r'\[\[[^\[\]#]+\]\]', link):
                        raise ValueError('Team profile bindings require wikilinks')
                    binding['profile'] = link[2:-2].split('|', 1)[0].strip()
                body['roles'][name] = binding
        return self._validate({'id': metadata.get('id'), 'kind': kind, 'title': metadata.get('title'),
                               'description': metadata.get('description'), 'body': body})

    @staticmethod
    def _filename(record):
        slug = re.sub(r'[^\w.-]+', '-', record['title'].lower()).strip('.-') or 'record'
        slug = slug[:160]
        suffix = '' if slug == record['id'] else '--' + revision(record['id'])[:8]
        return slug + suffix + '.md'

    def _profile_link(self, ident):
        document = self.documents.get(ident)
        if document is not None:
            target = 'profiles/' + str(PurePosixPath(document['location']).with_suffix(''))
        else:
            record = self.encoding_records.get(ident)
            if record is None:
                raise ValueError('Missing profile reference: ' + ident)
            target = 'profiles/' + str(PurePosixPath(self._filename(record)).with_suffix(''))
        return '[[modules/agents/data/' + target + ']]'

    def _encode(self, record):
        metadata = {key: record[key] for key in ('id', 'title', 'description')}
        metadata['type'] = record['kind']
        for key, value in record['body'].items():
            if key != 'instructions':
                metadata[key] = value
        if record['kind'] == 'team':
            metadata['roles'] = {role: ({'profile': self._profile_link(binding['profile'])} if 'profile' in binding else binding)
                                 for role, binding in record['body']['roles'].items()}
        return metadata, record['body'].get('instructions', '')

    def _scan(self):
        documents, records = {}, {}
        for directory, kind in (('profiles', 'profile'), ('teams', 'team')):
            scanned = self.core.documents.scan(directory=directory, collection='catalog')
            if not scanned.get('complete'):
                raise ValueError('Catalog source scan incomplete; no deletion can be inferred')
            for document in scanned['documents']:
                record = self._decode(document, kind)
                ident = record['id']
                if ident in documents:
                    raise ValueError('Duplicate catalog identity: ' + ident)
                document = dict(document, directory=directory)
                documents[ident], records[ident] = document, record
        self.link_errors = {}
        for record in records.values():
            if record['kind'] != 'team':
                continue
            for role, binding in record['body']['roles'].items():
                if 'profile' not in binding:
                    continue
                matches = self.reference_matches(binding['profile'],documents=documents,records=records,kind='profile')
                if len(matches) == 1:
                    binding['profile'] = matches[0]
                else:
                    self.link_errors[(record['id'], role)] = 'Missing profile wikilink' if not matches else 'Ambiguous profile wikilink'
        return documents, records

    def reference_matches(self, reference, *, records, documents=None, kind=None):
        """Use the catalog's native path aliases for roles and ordinary links."""
        documents = self.documents if documents is None else documents
        if reference.startswith('[[') and reference.endswith(']]'):
            reference = reference[2:-2].split('|',1)[0].strip()
        matches = []
        for ident, document in documents.items():
            record_kind = records[ident]['kind']
            if kind is not None and record_kind != kind:
                continue
            path = PurePosixPath(document['location'])
            directory = record_kind + 's/'
            choices = {directory+path.as_posix(), directory+str(path.with_suffix('')),
                       path.as_posix(), str(path.with_suffix('')), path.stem, path.name,
                       'modules/agents/data/'+directory+path.as_posix(),
                       'modules/agents/data/'+directory+str(path.with_suffix(''))}
            if reference in choices:
                matches.append(ident)
        return matches

    def resolve_reference(self, reference, *, records):
        matches = self.reference_matches(reference, records=records)
        return matches[0] if len(matches)==1 else None

    def _references(self, records):
        errors = []
        for record in records.values():
            if record['kind'] != 'team':
                continue
            for role, binding in record['body']['roles'].items():
                if 'profile' in binding:
                    target = records.get(binding['profile'])
                    link_error = self.link_errors.get((record['id'], role))
                    if target is None or target['kind'] != 'profile' or link_error:
                        errors.append({'team': record['id'], 'role': role, 'profile': binding['profile'],
                                       'error': link_error or 'Missing profile reference'})
                else:
                    errors.append({'team': record['id'], 'role': role, 'session': binding['session'], 'error': 'Legacy session binding is unsupported; select a profile explicitly'})
        return errors

    def sync(self):
        """Capture/validate all sources before applying a common Core change plan."""
        with self.writer:
            marker = self._cursor('internal:catalog-file-authority')
            old_rows = self.store.rows('SELECT * FROM "{{module}}::records"')
            if marker is None and not old_rows:
                for directory in ('profiles', 'teams', 'instructions'):
                    self.core.documents.prepare(directory=directory)
            if marker is None and old_rows:
                raise ValueError('Legacy SQL catalog requires agents.catalog_migrate; files were not changed')
            documents, records = self._scan()
            prior = self._cursor('internal:catalog-documents') or []
            current = [{k: v for k, v in doc.items() if k != 'directory'} for doc in documents.values()]
            plan = self.core.documents.plan(collection='catalog', documents=current, previous=prior, complete=True)
            # Retry cleanup after a crash; SQL and RAG are derived, never restored to source.
            deleted_ids = {key['id'] for key in plan['delete']}
            deleted_ids.update(row['id'] for row in old_rows if row['id'] not in records)
            for ident in deleted_ids:
                self.core.rag.delete_document(key={'collection': 'catalog', 'id': ident})
            changed_ids = {item['key']['id'] for item in plan['upsert'] + plan['refresh']}
            old_by_id = {row['id']: row for row in old_rows}
            for ident, record in records.items():
                old = old_by_id.get(ident)
                if old is None or old['revision'] != documents[ident]['file_revision'] or old['body'] != encoded(record['body']):
                    changed_ids.add(ident)
            if not deleted_ids and not changed_ids and marker is not None and current == prior:
                self.documents = documents
                self.reference_errors = self._references(records)
                return records
            with self.store.sql.transaction() as tx:
                for ident in deleted_ids:
                    tx.execute('DELETE FROM "{{module}}::records" WHERE id=?', [ident])
                for ident in sorted(changed_ids):
                    record, doc = records[ident], documents[ident]
                    tx.execute('INSERT INTO "{{module}}::records" (id,kind,title,description,body,revision) VALUES (?,?,?,?,?,?) '
                        'ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,title=excluded.title,description=excluded.description,'
                        'body=excluded.body,revision=excluded.revision,index_error=CASE WHEN revision!=excluded.revision THEN NULL ELSE index_error END',
                        [ident, record['kind'], record['title'], record['description'], encoded(record['body']), doc['file_revision']])
                self._put_cursor('internal:catalog-documents', current, tx)
                self._put_cursor('internal:catalog-file-authority', {'version': 1}, tx)
            self.documents = documents
            self.reference_errors = self._references(records)
            return records

    def capture(self):
        """Read authority for queries without requesting write capabilities."""
        with self.writer:
            if self._cursor('internal:catalog-file-authority') is None and self.store.rows('SELECT id FROM "{{module}}::records" LIMIT 1'):
                raise ValueError('Legacy SQL catalog requires agents.catalog_migrate; files were not changed')
            documents, records = self._scan()
            self.documents = documents
            self.reference_errors = self._references(records)
            return records

    def read(self, id):
        with self.writer:
            records = self.capture()
            if id not in records:
                raise ValueError('Unknown records ID: ' + id)
            row = records[id]
            indexed = self.store.rows('SELECT indexed_revision,index_error FROM "{{module}}::records" WHERE id=?', [id])
            document = self.documents[id]
            return {**row, **(indexed[0] if indexed else {'indexed_revision': None, 'index_error': None}),
                    'revision': document['file_revision'], 'path': document.get('path', document['directory'] + '/' + document['location']),
                    'text_revision': document['revision']}

    def list(self, kind=None, offset=0, limit=50):
        with self.writer:
            records = self.capture()
            result = []
            for ident, record in sorted(records.items()):
                if kind is not None and record['kind'] != kind:
                    continue
                indexed = self.store.rows('SELECT indexed_revision,index_error FROM "{{module}}::records" WHERE id=?', [ident])
                result.append({key: record[key] for key in ('id','kind','title','description')} |
                              {'revision': self.documents[ident]['file_revision']} |
                              (indexed[0] if indexed else {'indexed_revision': None, 'index_error': None}))
            return result[offset:offset + limit]

    def save(self, record, expected_revision=None):
        with self.writer:
            self._validate(record)
            if record['kind'] == 'team' and any('session' in role for role in record['body']['roles'].values()):
                raise ValueError('Teams support profile references only; session communication is not part of Agents')
            records = self.sync()
            old = records.get(record['id'])
            document = self.documents.get(record['id'])
            if old and old['kind'] != record['kind']:
                raise ValueError('A record cannot change kind; create a separate record')
            if (document['file_revision'] if document else None) != expected_revision:
                raise ValueError('Record changed; read its current revision before saving')
            # Proposed tool bindings are stable IDs, not the old source's broken links.
            self.link_errors = {key: error for key, error in self.link_errors.items() if key[0] != record['id']}
            errors = self._references({**records, record['id']: record})
            if any(error['team'] == record['id'] for error in errors):
                raise ValueError('Missing role reference: ' + encoded(errors))
            self.encoding_records = records
            metadata, text = self._encode(record)
            self.core.documents.write(directory=record['kind'] + 's', collection='catalog',
                path=document['location'] if document else self._filename(record), metadata=metadata, text=text,
                expected_revision=expected_revision)
            self.sync()
            return self.read(record['id'])

    def delete_profile(self, id, expected_revision):
        with self.writer:
            record = self.read(id)
            if record['kind'] != 'profile':
                raise ValueError('Expected a profile; teams cannot be deleted by profile_delete')
            if record['revision'] != expected_revision:
                raise ValueError('Record changed; read its current revision before deleting')
            references = []
            for team in self.capture().values():
                if team['kind'] != 'team':
                    continue
                for role, binding in team['body']['roles'].items():
                    if binding.get('profile') == id:
                        references.append({'kind': 'team', 'id': team['id'], 'role': role})
            if references:
                return {'id': id, 'status': 'blocked', 'references': references}
            source_revision = revision(self.documents)
            self.store.sql.execute('UPDATE "{{module}}::records" SET indexed_revision=NULL WHERE id=?', [id])
            self.core.rag.delete_document(key={'collection': 'catalog', 'id': id})
            self.capture()
            if revision(self.documents) != source_revision:
                raise ValueError('Catalog changed during deletion; reread references and retry')
            doc = self.documents[id]
            self.core.documents.delete(directory=doc['directory'], path=doc['location'], expected_revision=expected_revision)
            self.sync()
            return {'id': id, 'status': 'deleted', 'revision': expected_revision, 'index_status': 'deleted'}

    @staticmethod
    def _index_text(document):
        # Empty instructions are valid. Discovery still has purpose metadata,
        # without adding any text to the source or executor prompt.
        if document['text'].strip():
            return document['text']
        return document['metadata']['title'] + '\n' + document['metadata']['description']

    def _index_revision(self, document):
        return hashlib.sha256(self._index_text(document).encode('utf-8')).hexdigest()

    def pending_count(self):
        indexed = {row['id']: row['indexed_revision'] for row in
                   self.store.rows('SELECT id,indexed_revision FROM "{{module}}::records"')}
        return sum(indexed.get(ident) != self._index_revision(document) for ident, document in self.documents.items())

    def index_one(self):
        with self.writer:
            self.sync()
            profile = self.core.embeddings.profile()
            identity = revision(profile)
            if self._cursor('internal:catalog-profile') != identity:
                self.store.sql.execute('UPDATE "{{module}}::records" SET indexed_revision=NULL,index_error=NULL')
                self._put_cursor('internal:catalog-profile', identity)
            rows = self.store.rows('SELECT * FROM "{{module}}::records" ORDER BY index_error IS NOT NULL,id')
            row = next((row for row in rows if row['indexed_revision'] != self._index_revision(self.documents[row['id']])), None)
            if row is None:
                # Metadata/path changes retain vectors when the actual discovery text is unchanged.
                self._refresh_index_metadata()
                return False
            document = dict(self.documents[row['id']])
        try:
            vector = self.core.embeddings.embed_documents(texts=[self._index_text(document)], profile=profile)[0]
            with self.writer:
                self.sync()
                current = self.documents.get(row['id'])
                if current is None or current['file_revision'] != document['file_revision']:
                    return True
                self.core.rag.put_vector(document=self._rag_document(current), vector=vector, profile=profile)
                self.store.sql.execute('UPDATE "{{module}}::records" SET indexed_revision=?,index_error=NULL WHERE id=? AND revision=?',
                    [self._index_revision(current), row['id'], row['revision']])
        except Exception as exc:
            with self.writer:
                self.store.sql.execute('UPDATE "{{module}}::records" SET index_error=? WHERE id=? AND revision=?',
                    [str(exc)[:500], row['id'], row['revision']])
            raise
        return True

    def _rag_document(self, document):
        return {'key': {'collection': 'catalog', 'id': document['metadata']['id']},
                'revision': self._index_revision(document), 'text': self._index_text(document),
                'location': document.get('path', document['directory'] + '/' + document['location']),
                'metadata': document['metadata']}

    def _refresh_index_metadata(self):
        # Core retains vectors only for an unchanged discovery-text revision.
        previous = self._cursor('internal:catalog-rag-documents') or []
        current = [self._rag_document(doc) for doc in self.documents.values()]
        # Persist acknowledgement only after all refreshes succeed.
        for document in current:
            old = next((item for item in previous if item['key'] == document['key']), None)
            if old != document:
                self.core.rag.update_document(document=document)
        self._put_cursor('internal:catalog-rag-documents', current)

    def search(self, query, kind=None, selection=None):
        with self.writer:
            self.capture()
        args = {'query': query, 'collection': 'catalog'}
        if kind is not None:
            args['object_type'] = kind
        if selection is not None:
            args['selection'] = selection
        found = self.core.rag.search(**args)
        with self.writer:
            records = self.capture()
            results = []
            for item in found['results']:
                ident = item['key'][2]
                document = self.documents.get(ident)
                if document is None or self._index_revision(document) != item['revision']:
                    continue
                row = records[ident]
                if kind is not None and row['kind'] != kind:
                    continue
                results.append({key: row[key] for key in ('id', 'kind', 'title', 'description')} |
                               {'revision': document['file_revision'], 'distance': item['distance']})
            return {'results': results, 'diagnostics': found['diagnostics'], 'pending_count': self.pending_count(),
                    'reference_errors': self.reference_errors, 'stale_results_omitted': len(found['results']) - len(results)}

    def team_read(self, team):
        record = self.read(team)
        if record['kind'] != 'team':
            raise ValueError('Expected a team')
        members = []
        for role, binding in record['body']['roles'].items():
            error = next((item for item in self.reference_errors if item['team'] == team and item['role'] == role), None)
            if error:
                members.append({'role': role, **binding, 'error': error['error']})
            elif 'profile' in binding:
                profile = self.read(binding['profile'])
                members.append({'role': role, 'profile': profile['id'], 'title': profile['title'], 'description': profile['description']})
            else:
                raise ValueError('Session bindings are unsupported')
        return {'id': record['id'], 'title': record['title'], 'description': record['description'],
                'revision': record['revision'], 'instructions': record['body'].get('instructions', ''), 'members': members}

    def resolve(self, team, role):
        record = self.read(team)
        if record['kind'] != 'team':
            raise ValueError('Expected a team')
        binding = record['body']['roles'].get(role)
        if binding is None:
            raise ValueError('Unknown team role')
        if any(error['team'] == team and error['role'] == role for error in self.reference_errors):
            raise ValueError('Missing role reference; repair the source team explicitly')
        result = {'team': team, 'role': role, 'instructions': record['body'].get('instructions', '')}
        if 'profile' in binding:
            result['profile'] = self.read(binding['profile'])
        else:
            raise ValueError('Session bindings are unsupported')
        return result

    def migration_plan(self):
        with self.writer:
            rows = self.store.rows('SELECT id,kind,title,description,body,revision FROM "{{module}}::records" ORDER BY id')
            return {'revision': revision(rows), 'records': len(rows),
                    'required': self._cursor('internal:catalog-file-authority') is None and bool(rows)}

    def migrate(self, expected_revision):
        """Explicit, restart-safe export; keep the legacy source in a backup cursor."""
        with self.writer:
            plan = self.migration_plan()
            if plan['revision'] != expected_revision:
                raise ValueError('Migration revision changed; read the current plan')
            if self._cursor('internal:catalog-file-authority') is not None:
                return {'status': 'already_migrated', **plan}
            rows = self.store.rows('SELECT * FROM "{{module}}::records" ORDER BY id')
            records = {row['id']: self._validate({key: json.loads(row[key]) if key == 'body' else row[key]
                       for key in ('id', 'kind', 'title', 'description', 'body')}) for row in rows}
            for directory in ('profiles', 'teams', 'instructions'):
                self.core.documents.prepare(directory=directory)
            existing, _ = self._scan()
            self.documents = existing
            self.encoding_records = records
            for ident, record in sorted(records.items(), key=lambda item: item[1]['kind'] != 'profile'):
                metadata, text = self._encode(record)
                old = existing.get(ident)
                if old:
                    if old['metadata'] != metadata or old['text'] != text:
                        raise ValueError('Migration conflicts with existing file: ' + ident)
                    continue
                self.core.documents.write(directory=record['kind'] + 's', collection='catalog', path=self._filename(record),
                                          metadata=metadata, text=text, expected_revision=None)
            self._put_cursor('internal:catalog-legacy-backup', rows)
            self._put_cursor('internal:catalog-file-authority', {'version': 1})
            self.sync()
            return {'status': 'migrated', 'records': len(rows), 'reference_errors': self.reference_errors}
