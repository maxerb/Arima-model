"""T0.0: copy the shared files from the old thesis repository into this repository.

Before this project became its own repository, raw data, the codebook and the
requirements lived in the thesis folder. This script copies (never moves) them
here, so this repository no longer depends on anything outside itself.

Run once:
    python scripts/00_import_from_thesis_repo.py [path/to/Bachelors-Thesis]

Safe to run again: files that already exist here are skipped, never overwritten.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # this repository
DEFAULT_SOURCE = ROOT.parent / "Bachelors-Thesis"       # the old thesis repository


def copy_file(src: Path, dst: Path) -> None:
    """Copy one file byte for byte, unless the target already exists."""
    if dst.exists():
        print(f"skip  {dst.relative_to(ROOT)} (already here)")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)            # copy2 also keeps the file's timestamps
    print(f"copy  {src.name} -> {dst.relative_to(ROOT)}")


def copy_requirements_as_utf8(src: Path, dst: Path) -> None:
    """Copy requirements.txt and re-save it as UTF-8.

    The original was written by `pip freeze > requirements.txt` in Windows
    PowerShell, which saves UTF-16. pip cannot read UTF-16, so we convert it.
    """
    if dst.exists():
        print(f"skip  {dst.relative_to(ROOT)} (already here)")
        return
    raw = src.read_bytes()
    # A UTF-16 file starts with a byte-order mark (FF FE or FE FF).
    encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
    text = raw.decode(encoding)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"copy  {src.name} -> {dst.relative_to(ROOT)} ({encoding} -> utf-8, {len(lines)} packages)")


def main(source: Path) -> None:
    if not source.is_dir():
        sys.exit(f"Source folder not found: {source}")
    print(f"Importing from {source}\n")

    # 1. Raw downloads: Data/raw/* -> data/raw/*
    for src in sorted((source / "Data" / "raw").glob("*")):
        if src.is_file():
            copy_file(src, ROOT / "data" / "raw" / src.name)

    # 2. Codebook (header and any rows)
    copy_file(source / "codebook.csv", ROOT / "codebook.csv")

    # 3. Pinned packages, converted to UTF-8
    copy_requirements_as_utf8(source / "requirements.txt", ROOT / "requirements.txt")

    # 4. The original SNB loader, kept for reference. Its code now lives in
    #    src/arima_snb/io.py, with paths pointing to this repository.
    copy_file(source / "src" / "snb.py", ROOT / "scripts" / "explore" / "original_snb_loader.py")

    print("\nDone. Nothing was moved or deleted in the source folder.")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE)
