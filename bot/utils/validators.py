from __future__ import annotations
import io
import re
import zipfile


def validate_python_file(data: bytes, filename: str, max_mb: int) -> tuple[bool, str]:
    if len(data) > max_mb * 1024 * 1024:
        return False, f"File too large. Max {max_mb}MB."
    if not filename.endswith(".py"):
        return False, "Only .py files allowed on free plan."
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False, "File must be valid UTF-8 text."
    return True, ""


def validate_zip(data: bytes, max_mb: int, max_files: int = 100) -> tuple[bool, str]:
    if len(data) > max_mb * 1024 * 1024:
        return False, f"Archive too large. Max {max_mb}MB."
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if len(names) > max_files:
                return False, f"Too many files (max {max_files})."
            total = 0
            for info in zf.infolist():
                if ".." in info.filename or info.filename.startswith("/"):
                    return False, "Archive contains unsafe paths."
                total += info.file_size
                if total > 200 * 1024 * 1024:
                    return False, "Uncompressed size exceeds 200MB."
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file."
    return True, ""


def validate_github_url(url: str) -> tuple[bool, str]:
    if re.match(r"^https://github\.com/[\w\-\.]+/[\w\-\.]+(/.+)?$", url):
        return True, ""
    return False, "Must be: https://github.com/owner/repo"


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\-\. ]", "", name).strip()
    return cleaned[:64] or "project"
