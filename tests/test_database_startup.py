from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot import database


class FakeConnection:
    def __init__(self, dialect_name: str):
        self.dialect = SimpleNamespace(name=dialect_name)
        self.statements: list[str] = []
        self.sync_callbacks = []

    async def execute(self, statement):
        self.statements.append(str(statement))

    async def run_sync(self, callback):
        self.sync_callbacks.append(callback)


class FakeBegin:
    def __init__(self, connection: FakeConnection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    def __init__(self, connection: FakeConnection):
        self.connection = connection

    def begin(self):
        return FakeBegin(self.connection)


@pytest.mark.asyncio
async def test_postgres_schema_creation_uses_advisory_lock(monkeypatch):
    connection = FakeConnection("postgresql")
    monkeypatch.setattr(database, "_engine", FakeEngine(connection))

    await database.create_tables()

    assert len(connection.statements) == 1
    assert "pg_advisory_xact_lock" in connection.statements[0]
    assert len(connection.sync_callbacks) == 1


@pytest.mark.asyncio
async def test_non_postgres_schema_creation_skips_advisory_lock(monkeypatch):
    connection = FakeConnection("sqlite")
    monkeypatch.setattr(database, "_engine", FakeEngine(connection))

    await database.create_tables()

    assert connection.statements == []
    assert len(connection.sync_callbacks) == 1
