"""Curated package catalog: registry, install status, and the install flow."""

import json

import pytest
from pydantic import ValidationError

from skill_manager.core.schemas import CatalogPackageTemplate
from skill_manager.core.skill_packages import catalog


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Point the catalog's user-file lookup at a scratch directory."""
    import importlib

    import skill_manager.core.config as config_mod

    monkeypatch.setenv("SKILL_MANAGER_DATA_DIR", str(tmp_path / "data"))
    importlib.reload(config_mod)
    import skill_manager.core.skill_packages.catalog as catalog_mod

    importlib.reload(catalog_mod)
    yield catalog_mod
    importlib.reload(config_mod)


# ── schema ────────────────────────────────────────────────────────────────


def test_template_validation():
    template = CatalogPackageTemplate(
        id="demo",
        display_name="Demo Pack",
        install_command="https://github.com/acme/demo.git",
    )
    assert template.source_type == "git"
    assert template.tags == []
    assert template.featured is False

    with pytest.raises(ValidationError):
        CatalogPackageTemplate(id="demo", display_name="", install_command="x")
    with pytest.raises(ValidationError):
        CatalogPackageTemplate(id="", display_name="Demo", install_command="x")


def test_template_normalises_source_type_and_tags():
    template = CatalogPackageTemplate(
        id="demo",
        display_name="Demo Pack",
        install_command="npx skills add acme/demo",
        source_type="NPX",
        tags="a, b ,c",
    )
    assert template.source_type == "npx"
    assert template.tags == ["a", "b", "c"]


# ── registry ─────────────────────────────────────────────────────────────


def test_builtin_catalog_entries_are_valid():
    """Every built-in entry must validate."""
    templates = catalog.get_catalog()
    assert templates, "the built-in catalog must not be empty"
    ids = [t.id for t in templates]
    assert len(ids) == len(set(ids)), "catalog ids must be unique"
    for template in templates:
        assert template.display_name
        assert template.install_command
        assert template.source_type in ("git", "npx", "script")


def test_find_catalog_entry():
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None
    assert entry.display_name == "Vercel Skills"
    assert catalog.find_catalog_entry("does-not-exist") is None
    assert catalog.find_catalog_entry("") is None


def test_user_catalog_merges_and_overrides(tmp_path, monkeypatch):
    """A user catalog file adds entries and can replace a built-in one."""
    path = tmp_path / "data" / "package_catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {"id": "my-pack", "display_name": "My Pack", "install_command": "npx acme"},
                {
                    "id": "vercel-skills",
                    "display_name": "My Vercel Fork",
                    "install_command": "https://github.com/me/skills.git",
                },
            ]
        ),
        encoding="utf-8",
    )

    entries = {t.id: t for t in catalog.get_catalog()}
    assert "my-pack" in entries
    assert entries["my-pack"].display_name == "My Pack"
    # The user entry wins on an id collision.
    assert entries["vercel-skills"].display_name == "My Vercel Fork"


def test_corrupt_user_catalog_is_ignored(tmp_path):
    path = tmp_path / "data" / "package_catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    templates = catalog.get_catalog()
    assert templates, "a corrupt user catalog must not break the built-in one"


# ── install status ───────────────────────────────────────────────────────


def test_installed_status_is_detected_by_repository():
    """A package pointing at the same repository counts as installed."""
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None

    installed = [
        {
            "package_id": "pkg_abc123",
            "name": "Vercel",
            "repository_url": "https://github.com/vercel-labs/skills.git",
        }
    ]
    entries = {e["id"]: e for e in catalog.catalog_with_status(installed)}
    assert entries["vercel-skills"]["is_installed"] is True
    assert entries["vercel-skills"]["installed_package_id"] == "pkg_abc123"


def test_installed_status_is_case_and_suffix_insensitive():
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None
    installed = [
        {
            "package_id": "pkg_x",
            "repository_url": "https://github.com/vercel-labs/skills",
        }
    ]
    assert catalog.matches_installed_package(entry, installed) == "pkg_x"


def test_known_repo_aliases_are_canonicalised():
    """`vercel-labs/find-skills` resolves to the same package as `vercel-labs/skills`."""
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None
    installed = [
        {
            "package_id": "pkg_alias",
            "repository_url": "https://github.com/vercel-labs/find-skills.git",
        }
    ]
    assert catalog.matches_installed_package(entry, installed) == "pkg_alias"


def test_not_installed_when_nothing_matches():
    entries = {e["id"]: e for e in catalog.catalog_with_status([])}
    for entry in entries.values():
        assert entry["is_installed"] is False
        assert entry["installed_package_id"] == ""


def test_npx_catalog_entry_matches_by_package_name():
    entry = catalog.find_catalog_entry("skills-npx")
    assert entry is not None
    installed = [{"package_id": "pkg_npm", "package_name": "skills"}]
    assert catalog.matches_installed_package(entry, installed) == "pkg_npm"


# ── install data ─────────────────────────────────────────────────────────


def test_template_to_package_data_parses_the_install_command():
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None
    data = catalog.template_to_package_data(entry)
    assert data["name"] == "Vercel Skills"
    assert data["source_type"] == "git"
    assert "vercel-labs/skills" in data["repository_url"]


def test_template_to_package_data_keeps_default_args():
    entry = catalog.find_catalog_entry("skills-npx")
    assert entry is not None
    data = catalog.template_to_package_data(entry)
    assert data["source_type"] == "npx"
    assert "--all" in data["package_args"]


def test_template_to_package_data_honours_the_target_path():
    entry = catalog.find_catalog_entry("vercel-skills")
    assert entry is not None
    data = catalog.template_to_package_data(entry, target_path="/tmp/pkgs")
    assert data["package_path"] == "/tmp/pkgs"


# ── controller ───────────────────────────────────────────────────────────


@pytest.fixture
def update_controller(mock_app):
    from skill_manager.controllers.update_controller import UpdateController

    mock_app._update_packages = []
    return UpdateController(mock_app)


def test_catalog_packages_property_lists_the_catalog(update_controller):
    packages = update_controller.catalogPackages
    assert packages
    assert all("is_installed" in p for p in packages)


def test_catalog_packages_marks_installed_entries(update_controller, mock_app):
    mock_app._update_packages = [
        {
            "package_id": "pkg_abc",
            "name": "Vercel",
            "repository_url": "https://github.com/vercel-labs/skills.git",
        }
    ]
    packages = {p["id"]: p for p in update_controller.catalogPackages}
    assert packages["vercel-skills"]["is_installed"] is True


def test_catalog_package_returns_one_entry(update_controller):
    entry = update_controller.catalogPackage("vercel-skills")
    assert entry["display_name"] == "Vercel Skills"
    assert update_controller.catalogPackage("nope") == {}


def test_install_catalog_package_default_rejects_unknown_id(update_controller, mock_app):
    result = json.loads(update_controller.installCatalogPackageDefault("nope"))
    assert result["ok"] is False
    assert "nope" in result["error"]


def test_install_catalog_package_default_uses_the_add_flow(update_controller, mock_app):
    """The catalog install reuses the regular add-package flow."""
    captured = {}

    def fake_add(data):
        captured["data"] = data
        return json.dumps({"ok": True, "name": data.get("name", "")})

    update_controller.addSkillPackage = fake_add

    result = json.loads(update_controller.installCatalogPackageDefault("vercel-skills"))
    assert result["ok"] is True
    assert captured["data"]["name"] == "Vercel Skills"
    assert "vercel-labs/skills" in captured["data"]["repository_url"]
