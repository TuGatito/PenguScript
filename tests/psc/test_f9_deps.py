from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"


def env(tmp: Path) -> dict[str, str]:
    e = os.environ.copy()
    e.update(
        PENGU_STD_DIR=str(ROOT / "std"),
        PENGU_LIB_DIR=str(ROOT / "build" / "lib"),
        PENGU_INCLUDE_DIR=str(ROOT / "build" / "include"),
        PSC_CACHE_DIR=str(tmp / "cache"),
    )
    return e


def run(cwd: Path, *args: str, e: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(PSC), *args], cwd=cwd, env=e or env(cwd), text=True, capture_output=True)


def init(path: Path, name: str) -> None:
    r = run(path, "init", name)
    assert r.returncode == 0, r.stderr


def local_lib(base: Path, name: str = "leaf") -> Path:
    lib = base / name
    (lib / "src").mkdir(parents=True)
    (lib / "pengu.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\nentry = "src/{name}.pengu"\n\n'
        '[build]\nsrc_dir = "src"\nlib_dir = "lib"\n',
        encoding="utf-8",
    )
    (lib / "src" / f"{name}.pengu").write_text(
        'weave greet into string:\n    return "hola"\n', encoding="utf-8"
    )
    return lib


def app(base: Path, name: str = "app") -> Path:
    init(base, name)
    proj = base / name
    (proj / "src" / "main.pengu").write_text(
        'import std.spark\nimport leaf\n\nweave main into int:\n'
        '    calling spark.println with (calling greet)\n    return 0\n',
        encoding="utf-8",
    )
    return proj


def test_f9_add_local_build_verify_vendor(tmp_path: Path) -> None:
    lib = local_lib(tmp_path)
    proj = app(tmp_path)
    r = run(proj, "add", str(lib), "--name=leaf", "--no-build")
    assert r.returncode == 0, r.stderr
    assert (proj / "lib" / "leaf" / "src" / "leaf.pengu").is_file()
    assert "leaf = { path" in (proj / "pengu.toml").read_text(encoding="utf-8")
    assert "sha256" in (proj / "pengu.lock").read_text(encoding="utf-8")

    r = run(proj, "verify")
    assert r.returncode == 0, r.stderr

    r = run(proj, "vendor")
    assert r.returncode == 0, r.stderr
    assert (proj / "vendor" / "leaf" / "src" / "leaf.pengu").is_file()

    import shutil
    shutil.rmtree(proj / "lib" / "leaf")
    r = run(proj, "build", "--frozen")
    assert r.returncode == 0, r.stderr
    assert (proj / "build" / "app").is_file()


def test_f9_git_tag_and_remove(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    lib = local_lib(tmp_path, "gitlib")
    import shutil
    shutil.move(str(lib), str(repo))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init"], cwd=repo, check=True)
    subprocess.run(["git", "tag", "v1.0.0"], cwd=repo, check=True)

    proj = app(tmp_path, "app2")
    r = run(proj, "add", repo.as_uri(), "--name=leaf", "--version=^1.0", "--no-build")
    assert r.returncode == 0, r.stderr
    lock = (proj / "pengu.lock").read_text(encoding="utf-8")
    assert 'version = "v1.0.0"' in lock
    assert (proj / "lib" / "leaf" / ".git").is_dir()

    r = run(proj, "verify")
    assert r.returncode == 0, r.stderr
    r = run(proj, "remove", "leaf")
    assert r.returncode == 0, r.stderr
    assert "leaf =" not in (proj / "pengu.toml").read_text(encoding="utf-8")
    assert not (proj / "lib" / "leaf").exists()


def test_f9_yaml_rejected(tmp_path: Path) -> None:
    (tmp_path / "pengu.yaml").write_text("project:\n  name: demo\n", encoding="utf-8")
    r = run(tmp_path, "build")
    assert r.returncode == 1
    assert "only pengu.toml" in r.stderr


def test_f9_frozen_requires_lock(tmp_path: Path) -> None:
    lib = local_lib(tmp_path)
    proj = app(tmp_path, "app3")
    r = run(proj, "add", str(lib), "--name=leaf", "--no-build")
    assert r.returncode == 0, r.stderr
    (proj / "pengu.lock").unlink()
    r = run(proj, "build", "--frozen")
    assert r.returncode == 1
    assert "E0061" in r.stderr


def test_f9_unsafe_name_rejected(tmp_path: Path) -> None:
    lib = local_lib(tmp_path)
    proj = app(tmp_path, "app4")
    r = run(proj, "add", str(lib), "--name=..", "--no-build")
    assert r.returncode == 1
    assert "invalid dependency name" in r.stderr
    assert list((proj / "lib").iterdir()) == []


def test_f9_locked_does_not_rewrite(tmp_path: Path) -> None:
    lib = local_lib(tmp_path)
    proj = app(tmp_path, "app5")
    r = run(proj, "add", str(lib), "--name=leaf", "--no-build")
    assert r.returncode == 0, r.stderr
    before = (proj / "pengu.lock").read_bytes()
    r = run(proj, "build", "--locked")
    assert r.returncode == 0, r.stderr
    assert (proj / "pengu.lock").read_bytes() == before


def test_f9_build_script_trust(tmp_path: Path) -> None:
    lib = local_lib(tmp_path)
    (lib / "build.pengu").write_text(
        'import std.archivum\n\nweave main into int:\n'
        '    var ok as bool is calling archivum.write_text with "built.txt", "ok\\n"\n'
        '    return 0\n',
        encoding="utf-8",
    )
    proj = app(tmp_path, "app6")
    e = env(tmp_path)
    r = run(proj, "add", str(lib), "--name=leaf", e=e)
    assert r.returncode == 0, r.stderr
    assert not (proj / "lib" / "leaf" / "built.txt").exists()
    r = run(proj, "add", str(lib), "--name=leaf", "--trust", e=e)
    assert r.returncode == 0, r.stderr
    assert (proj / "lib" / "leaf" / "built.txt").is_file()
