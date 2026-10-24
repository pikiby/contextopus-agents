"""Main-agent rules in the common Core instruction library, referenced by YAML."""
import hashlib
import os
from pathlib import Path
from .storage import revision


class Instructions:
    def __init__(self, core, writer):
        self.core, self.writer = core, writer
        self.legacy = Path(os.environ['CONTEXTOPUS_MODULE_CONFIG']) / 'INSTRUCTIONS.md'
        self.default = Path(__file__).resolve().parents[1] / 'defaults/INSTRUCTIONS.md'

    def _reference(self, allow_missing=False):
        directory = Path(os.environ['CONTEXTOPUS_MODULE_DATA']) / 'instructions'
        if allow_missing and not directory.exists() and not directory.is_symlink():
            return None
        scanned = self.core.documents.scan(directory='instructions', collection='instructions')
        if not scanned.get('complete'):
            raise ValueError('Instruction reference source scan incomplete')
        documents = scanned['documents']
        if not documents:
            return None
        if len(documents) != 1:
            raise ValueError('Expected one main-agent instruction reference')
        document = documents[0]
        meta = document['metadata']
        if set(meta) != {'id', 'type', 'document'} or meta['id'] != 'main' or meta['type'] != 'instruction-reference' or document['text'].strip():
            raise ValueError('Invalid main-agent instruction reference')
        if not isinstance(meta['document'], str) or not (meta['document'].startswith('[[') and meta['document'].endswith(']]') and meta['document'][2:-2].strip()):
            raise ValueError('Instruction reference must be a Core document wikilink')
        return document

    def read(self):
        with self.writer:
            reference = self._reference()
            if reference is None:
                if self.legacy.exists():
                    raise ValueError('Legacy instructions require agents.catalog_migrate; files were not changed')
                raw = self.default.read_bytes()
                return {'path': str(Path(os.environ['CONTEXTOPUS_ROOT']) / 'core/instructions/agents-main.md'), 'content': raw.decode('utf-8'),
                        'revision': hashlib.sha256(raw).hexdigest(), 'source': 'default'}
            required = self.core.instructions.resolve(references=[reference['metadata']['document']])
            # Core resolves dependencies first, with the selected primary last.
            document = required['instructions'][-1]
            return {'path': str(Path(os.environ['CONTEXTOPUS_ROOT']) / 'core/instructions' / document['path']), 'content': document['content'],
                    'revision': revision([reference['file_revision'], required['revision']]), 'source': 'user',
                    'required_revision': required['revision'],
                    'documents': [item for item in required['instructions'] if item['id'] != document['id']],
                    'document_revision': document['revision'], 'reference_revision': reference['file_revision'],
                    'reference': reference['metadata']['document']}

    def save(self, content, expected_revision):
        if len(content.encode('utf-8')) > 262144:
            raise ValueError('Instructions exceed the transport storage budget of 256 KiB')
        with self.writer:
            current = self.read()
            if current['revision'] != expected_revision:
                raise ValueError('Instructions changed; read the current revision before saving')
            reference = self._reference()
            if (reference['file_revision'] if reference else None) != current.get('reference_revision'):
                raise ValueError('Instruction reference revision changed; reread before saving')
            resolved = self.core.instructions.read(reference=reference['metadata']['document']) if reference else None
            target = resolved['path'] if resolved else 'agents-main.md'
            metadata = ({'id': 'agents-main', 'type': 'instruction', 'title': 'Agents main instructions'}
                        if resolved is None else resolved['metadata'])
            self.core.instructions.save(path=target, metadata=metadata, content=content,
                                        expected_revision=current.get('document_revision'))
            if reference is None:
                self.core.documents.write(directory='instructions', collection='instructions', path='main.md',
                    metadata={'id': 'main', 'type': 'instruction-reference', 'document': '[[agents-main]]'},
                    text='', expected_revision=None)
            return self.read()

    def migration_state(self):
        raw = self.legacy.read_bytes() if self.legacy.exists() else None
        return {'required': raw is not None and self._reference(allow_missing=True) is None,
                'revision': hashlib.sha256(raw).hexdigest() if raw is not None else None}

    def migrate(self, expected_revision):
        with self.writer:
            raw = self.legacy.read_bytes() if self.legacy.exists() else None
            actual = hashlib.sha256(raw).hexdigest() if raw is not None else None
            if actual != expected_revision:
                raise ValueError('Legacy instruction revision changed; read the current migration plan')
            if raw is None:
                return {'status': 'absent'}
            content = raw.decode('utf-8')
            self.core.documents.prepare(directory='instructions')
            reference = self._reference()
            if reference is not None:
                if self.read()['content'] != content:
                    raise ValueError('Legacy instructions conflict with current Core document')
                return {'status': 'already_migrated'}
            target = 'agents-main.md'
            try:
                existing = self.core.instructions.read(reference=target)
            except Exception as exc:
                # Child protocol represents a missing document as a remote error.
                if 'Missing instruction:' not in str(exc) and not isinstance(exc, FileNotFoundError):
                    raise
                existing = None
            if existing is not None and existing['content'] != content:
                raise ValueError('Legacy instructions conflict with existing Core document')
            if existing is None:
                self.core.instructions.save(path=target, metadata={'id': 'agents-main', 'type': 'instruction',
                    'title': 'Agents main instructions'}, content=content, expected_revision=None)
            self.core.documents.write(directory='instructions', collection='instructions', path='main.md',
                metadata={'id': 'main', 'type': 'instruction-reference', 'document': '[[agents-main]]'}, text='', expected_revision=None)
            return {'status': 'migrated', 'legacy_path': str(self.legacy), 'legacy_preserved': True}
