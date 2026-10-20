from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from bot.services.hosting_service import _build_env


def test_runtime_env_does_not_inherit_host_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("BOT_TOKEN", "host-bot-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://host-secret")
    monkeypatch.setenv("HOSTING_API_TOKEN", "hosting-secret")
    monkeypatch.setenv("CI_JOB_TOKEN", "ci-secret")
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, env_vars=None)

    env = _build_env(project)

    assert env["PATH"] == "/usr/bin"
    assert env["LANG"] == "en_US.UTF-8"
    assert env["SODO_PROJECT_ID"] == str(project_id)
    assert "BOT_TOKEN" not in env
    assert "DATABASE_URL" not in env
    assert "HOSTING_API_TOKEN" not in env
    assert "CI_JOB_TOKEN" not in env


def test_runtime_env_includes_only_project_configured_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("PRIVATE_HOST_VALUE", "do-not-inherit")
    project_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        env_vars=json.dumps({"APP_MODE": "production", "APP_TOKEN": "project-secret"}),
    )

    env = _build_env(project)

    assert env["APP_MODE"] == "production"
    assert env["APP_TOKEN"] == "project-secret"
    assert "PRIVATE_HOST_VALUE" not in env
