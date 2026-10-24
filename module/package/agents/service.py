"""Module operations and background work use Core's shared child SDK."""
import threading
from .storage import Store, revision
from .instructions import Instructions
from .catalog import Catalog


class Service:
    def __init__(self, core):
        self.writer = threading.RLock()
        self.core, self.store = core, Store(core.storage, self.writer)
        self.instructions = Instructions(core, self.writer)
        self.catalog = Catalog(core, self.store, self.writer)
        self.closed = threading.Event()
        self.workers = []
        self.errors = {}
        from .library import library
        self.operations = {
            "library": lambda **arguments: library(self, **arguments),
            "instructions_read": self.instructions.read, "instructions_save": self.instructions.save,
            "team_read": self.catalog.team_read,
            "status": self.status, "record_save": self.catalog.save,
            "profile_delete": self.catalog.delete_profile,
            "catalog_migration_plan": self.migration_plan, "catalog_migrate": self.migrate,
            "read": self.catalog.read, "list": self.list_records,
            "search": self.catalog.search, "team_resolve": self.catalog.resolve,
        }

    def start(self):
        try:
            capabilities = self.core.rag.capabilities()
        except Exception as exc:
            raise RuntimeError("Agents requires the Core child rag.search extension; update Core first") from exc
        if not capabilities.get("search"):
            raise RuntimeError("Core does not provide shared search selection")
        try:
            self.catalog.sync()
        except Exception as exc:
            self.errors['index'] = str(exc)[:500]
        worker = threading.Thread(target=self.loop, args=("index", self.catalog.index_one), name="agents-index", daemon=True)
        worker.start()
        self.workers.append(worker)

    def loop(self, name, function):
        while not self.closed.is_set():
            try:
                worked = function()
                self.errors.pop(name, None)
                self.closed.wait(.05 if worked else .5)
            except Exception as exc:
                self.errors[name] = str(exc)[:500]
                self.closed.wait(3)

    def dispatch(self, operation, arguments, context):
        if self.closed.is_set():
            raise RuntimeError("Module is stopping")
        name = operation.removeprefix("agents.")
        if operation != "agents." + name or name not in self.operations:
            raise ValueError("Unknown agents operation")
        return self.operations[name](**arguments)

    def list_records(self, kind=None, offset=0, limit=50):
        return self.catalog.list(kind=kind, offset=offset, limit=limit)

    def migration_plan(self):
        with self.writer:
            catalog = self.catalog.migration_plan()
            instructions = self.instructions.migration_state()
            return {'catalog': catalog, 'instructions': instructions,
                    'revision': revision([catalog, instructions])}

    def migrate(self, expected_revision):
        with self.writer:
            plan = self.migration_plan()
            if plan['revision'] != expected_revision:
                raise ValueError('Migration revision changed; read the current plan')
            result = self.catalog.migrate(plan['catalog']['revision'])
            result['instructions'] = self.instructions.migrate(plan['instructions']['revision'])
            return result


    def status(self):
        try:
            self.catalog.capture()
            catalog_error = None
        except Exception as exc:
            catalog_error = str(exc)[:500]
        return {"workers": {w.name: w.is_alive() for w in self.workers}, "errors": dict(self.errors),
                "pending_index": self.catalog.pending_count(), 'catalog_error': catalog_error,
                'reference_errors': self.catalog.reference_errors}

    def close(self):
        self.closed.set()
        for worker in self.workers:
            worker.join(timeout=16)
