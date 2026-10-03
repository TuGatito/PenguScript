"""Roadmap Phase 4 / §4.11 — TOML is the canonical manifest format.

Reading already preferred ``pengu.toml``; writing (``pengu init`` and
``pengu add``) used to produce ``pengu.yaml``.  YAML/JSON stay readable for
backwards compatibility.
"""

import os
import tomllib

from pengu_project import (
    OutputType,
    ProjectConfig,
    _dump_toml,
    _update_config_dependency,
    init_project,
)


def test_dump_toml_round_trips():
    data = {
        "project": {"name": "app", "output": "exe", "version": "0.1.0"},
        "build": {"links": ["m", "z"], "cc": "gcc", "cflags": ["-Wall", "-std=c11"]},
        "assets": {"embed": True},
        "dependencies": {"webui": {"url": "https://x/y.git", "branch": "main"}},
    }
    text = "\n".join(_dump_toml(data)) + "\n"
    assert tomllib.loads(text) == data


def test_init_defaults_to_toml_and_round_trips(tmp_path):
    proj = init_project("toml_app", output_type="exe", target_dir=str(tmp_path),
                        links=["m"], cc="clang")
    manifest = os.path.join(proj, "pengu.toml")
    assert os.path.isfile(manifest)
    assert not os.path.isfile(os.path.join(proj, "pengu.yaml"))

    raw = tomllib.loads(open(manifest, encoding="utf-8").read())
    assert raw["project"]["name"] == "toml_app"
    assert raw["build"]["cc"] == "clang"
    assert raw["build"]["links"] == ["m"]

    cfg = ProjectConfig.load(proj)
    assert cfg.name == "toml_app"
    assert cfg.output == OutputType.EXE
    assert cfg.cc == "clang"
    assert cfg.resolve_entry() == os.path.abspath(
        os.path.join(proj, "src", "main.pengu"))


def test_init_yaml_format_still_available(tmp_path):
    proj = init_project("yaml_app", output_type="exe", target_dir=str(tmp_path),
                        manifest_format="yaml")
    assert os.path.isfile(os.path.join(proj, "pengu.yaml"))
    assert not os.path.isfile(os.path.join(proj, "pengu.toml"))
    assert ProjectConfig.load(proj).name == "yaml_app"


def test_toml_wins_when_both_manifests_exist(tmp_path):
    init_project("both_app", output_type="exe", target_dir=str(tmp_path),
                 manifest_format="yaml")
    proj = os.path.join(str(tmp_path), "both_app")
    with open(os.path.join(proj, "pengu.toml"), "w", encoding="utf-8") as f:
        f.write('[project]\nname = "from_toml"\nentry = "src/main.pengu"\n')
    assert ProjectConfig.load(proj).name == "from_toml"


def test_update_config_dependency_creates_toml(tmp_path):
    _update_config_dependency(str(tmp_path), "webui", "https://example.com/webui.git",
                              branch="main")
    manifest = tmp_path / "pengu.toml"
    assert manifest.is_file()
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    assert data["dependencies"]["webui"]["url"] == "https://example.com/webui.git"
    assert data["dependencies"]["webui"]["branch"] == "main"


def test_update_config_dependency_preserves_existing_toml(tmp_path):
    init_project("dep_app", output_type="exe", target_dir=str(tmp_path))
    proj = os.path.join(str(tmp_path), "dep_app")
    _update_config_dependency(proj, "alpha", "https://example.com/a.git")
    _update_config_dependency(proj, "beta", "https://example.com/b.git", branch="dev")
    data = tomllib.loads(open(os.path.join(proj, "pengu.toml"), encoding="utf-8").read())
    assert set(data["dependencies"]) == {"alpha", "beta"}
    # Existing sections survive the rewrite.
    assert data["project"]["name"] == "dep_app"
    assert data["build"]["src_dir"] == "src"


def test_update_config_dependency_updates_yaml_in_place(tmp_path):
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: yaml_app\n  entry: src/main.pengu\n", encoding="utf-8"
    )
    _update_config_dependency(str(tmp_path), "zed", "https://example.com/z.git")
    txt = (tmp_path / "pengu.yaml").read_text(encoding="utf-8")
    assert "zed" in txt
    assert not (tmp_path / "pengu.toml").exists()
