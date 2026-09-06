import hashlib
import os
import re
import shutil
import uuid
from datetime import timedelta
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import TrashItem, UploadSession


WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def safe_relative(value, allow_empty=False):
    value = str(value or "").replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        raise ValueError("Absolute paths are not allowed.")
    value = value.rstrip("/")
    if not value and allow_empty:
        return PurePosixPath()
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Hidden, reserved, and traversal paths are not allowed.")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or len(value) > 900:
        raise ValueError("Invalid path.")
    for part in path.parts:
        stem = part.split(".", 1)[0].lower()
        if part.startswith(".") or stem in WINDOWS_RESERVED or any(ord(char) < 32 for char in part) or any(char in "?#" for char in part):
            raise ValueError("Hidden, reserved, and traversal paths are not allowed.")
    return path


def beneath(root, relative):
    root = Path(root).resolve()
    candidate = root.joinpath(*relative.parts)
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError("Path escapes managed storage.")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symbolic-link paths are not allowed.")
    return candidate


def public_path(value, allow_empty=False):
    return beneath(settings.MANAGED_ROOT / "public", safe_relative(value, allow_empty=allow_empty))


def check_space(required):
    usage = shutil.disk_usage(settings.MANAGED_ROOT)
    if usage.free - required < settings.MIN_FREE_BYTES:
        raise ValueError("Not enough free disk space to preserve the configured safety reserve.")


def trash_path(path, kind="file"):
    root = (settings.MANAGED_ROOT if kind == "file" else settings.MEDIA_ROOT) / "trash"
    relative = path.relative_to((settings.MANAGED_ROOT if kind == "file" else settings.MEDIA_ROOT) / "public")
    destination = root / timezone.now().strftime("%Y/%m/%d") / uuid.uuid4().hex / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, destination)
    return TrashItem.objects.create(
        kind=kind,
        label=str(relative),
        original_path=str(relative),
        trash_path=str(destination.relative_to(root)),
        expires_at=timezone.now() + timedelta(days=settings.TRASH_DAYS),
    )


def create_upload(relative_path, total_size, sha256, replace=False):
    relative = safe_relative(relative_path)
    total_size = int(total_size)
    sha256 = str(sha256).lower()
    if total_size < 0 or total_size > settings.MAX_UPLOAD_SIZE:
        raise ValueError("File size exceeds the configured 10 GiB limit.")
    if not SHA256_RE.fullmatch(sha256):
        raise ValueError("A lowercase SHA-256 digest is required.")
    destination = beneath(settings.MANAGED_ROOT / "public", relative)
    if destination.exists() and not replace:
        raise FileExistsError("A file or folder already exists at that path.")
    # Completion briefly needs both all chunks and the assembled file.
    check_space(total_size * 2 + settings.UPLOAD_CHUNK_SIZE)
    session = UploadSession.objects.create(
        relative_path=str(relative), total_size=total_size, sha256=sha256,
        chunk_size=settings.UPLOAD_CHUNK_SIZE, replace=bool(replace),
    )
    (settings.MANAGED_ROOT / "staging" / str(session.id) / "chunks").mkdir(parents=True, exist_ok=False)
    return session


def received_chunk_indices(session):
    chunks = settings.MANAGED_ROOT / "staging" / str(session.id) / "chunks"
    if not chunks.exists():
        return []
    indices = []
    for path in chunks.iterdir():
        if path.is_file() and path.name.isdigit() and len(path.name) == 8:
            index = int(path.name)
            if 0 <= index < session.total_chunks:
                indices.append(index)
    return sorted(set(indices))


def store_chunk(session, index, body):
    if session.status != "uploading":
        raise ValueError("Upload is no longer active.")
    index = int(index)
    if index < 0 or index >= session.total_chunks:
        raise ValueError("Chunk index is out of range.")
    expected = session.chunk_size
    if index == session.total_chunks - 1:
        expected = session.total_size - index * session.chunk_size
    if len(body) != expected:
        raise ValueError(f"Chunk has {len(body)} bytes; expected {expected}.")
    chunk = settings.MANAGED_ROOT / "staging" / str(session.id) / "chunks" / f"{index:08d}"
    temporary = chunk.with_suffix(f".{uuid.uuid4().hex}.tmp")
    with open(temporary, "xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, chunk)


def complete_upload(session):
    checksum_error = None
    destination = None
    with transaction.atomic():
        session = UploadSession.objects.select_for_update().get(pk=session.pk)
        if session.status != "uploading":
            raise ValueError("Upload is no longer active.")
        actual_chunks = received_chunk_indices(session)
        if set(actual_chunks) != set(range(session.total_chunks)):
            raise ValueError("Upload is missing chunks.")
        # Recheck immediately before assembling: other sessions or backup work
        # may have consumed space since this upload was created.
        check_space(session.total_size + session.chunk_size)
        session.received_chunks = actual_chunks
        session_dir = settings.MANAGED_ROOT / "staging" / str(session.id)
        assembled = session_dir / "assembled"
        assembled.unlink(missing_ok=True)
        digest = hashlib.sha256()
        with open(assembled, "xb") as output:
            for index in range(session.total_chunks):
                with open(session_dir / "chunks" / f"{index:08d}", "rb") as source:
                    while block := source.read(1024 * 1024):
                        digest.update(block)
                        output.write(block)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != session.sha256:
            assembled.unlink(missing_ok=True)
            session.status = "failed"
            session.error = "SHA-256 verification failed"
            session.save(update_fields=["status", "error", "updated_at"])
            checksum_error = session.error
            shutil.rmtree(session_dir, ignore_errors=True)
        else:
            destination = public_path(session.relative_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if not session.replace:
                    raise FileExistsError("Destination appeared while uploading.")
                trash_path(destination)
            os.replace(assembled, destination)
            shutil.rmtree(session_dir)
            session.status = "complete"
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at", "received_chunks", "updated_at"])
    if checksum_error:
        raise ValueError(checksum_error)
    return destination


def cancel_upload(session):
    if session.status == "uploading":
        shutil.rmtree(settings.MANAGED_ROOT / "staging" / str(session.id), ignore_errors=True)
        session.status = "cancelled"
        session.save(update_fields=["status", "updated_at"])
