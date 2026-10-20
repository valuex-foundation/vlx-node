#!/usr/bin/env python3
"""Build public ZIP, TAR and TAR.GZ packages from the same selected source files."""
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = {".env.example", ".gitignore", ".dockerignore", ".gitattributes",
       "README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE",
       "Makefile", "versions.env", "docker-compose.yml", "vlx-node.sh"}
DIRECTORIES = {".github", "deploy", "docker", "config", "genesis", "chainlist",
               "monitoring", "scripts", "docs", "tests"}
EXTENSIONS = {".md", ".sh", ".py", ".yml", ".yaml", ".json", ".example"}


def public_files():
    candidates = [ROOT / name for name in TOP]
    for directory in sorted(DIRECTORIES):
        candidates.extend((ROOT / directory).rglob("*"))
    for path in sorted(candidates):
        rel = path.relative_to(ROOT)
        if path.is_symlink() or not path.is_file():
            continue
        if len(rel.parts) == 1:
            if rel.name in TOP:
                yield path, rel
            continue
        if rel.parts[0] not in DIRECTORIES:
            continue
        if any(part in ("__pycache__", "superpowers") for part in rel.parts):
            continue
        if path.name == "NODE_SNAPSHOT_ADDRESSES.md":
            continue
        if rel.parts[0] == "config" and path.suffix != ".example" and path.suffix != ".md":
            continue
        if (path.suffix in EXTENSIONS
                or rel.as_posix() in {"docker/Dockerfile", "docs/assets/logo-full.png"}):
            yield path, rel


def main():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    files = list(public_files())
    dest = output / "vlx-node-public.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, rel in files:
            archive.write(path, "vlx-node/" + rel.as_posix())
    print(dest)
    for extension, mode in (("tar", "w"), ("tar.gz", "w:gz")):
        dest = output / f"vlx-node-public.{extension}"
        with tarfile.open(dest, mode) as archive:
            for path, rel in files:
                info = archive.gettarinfo(str(path), "vlx-node/" + rel.as_posix())
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if path.suffix == ".sh" else 0o644
                with path.open("rb") as source:
                    archive.addfile(info, source)
        print(dest)


if __name__ == "__main__":
    main()
