"""Non-destructive storage admission for new project and task records."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StorageAdmissionLimits:
    min_free_bytes: int = 128 * 1024 * 1024
    max_database_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 1 for value in (
            self.min_free_bytes, self.max_database_bytes,
        )):
            raise ValueError("Storage admission limits must be positive integers")


class StorageAdmissionError(Exception):
    pass


DEFAULT_STORAGE_LIMITS = StorageAdmissionLimits()


def check_storage_admission(
    db_path: Path,
    write_bytes: int,
    limits: StorageAdmissionLimits = DEFAULT_STORAGE_LIMITS,
) -> None:
    if type(write_bytes) is not int or write_bytes < 0:
        raise ValueError("The storage reservation must be a nonnegative integer")
    try:
        database_bytes = sum(
            path.stat().st_size
            for path in (db_path, Path(str(db_path) + "-wal"))
            if path.exists()
        )
        free_bytes = shutil.disk_usage(db_path.resolve().parent).free
    except OSError as exc:
        raise StorageAdmissionError("Storage capacity could not be verified") from exc
    if database_bytes + write_bytes > limits.max_database_bytes:
        raise StorageAdmissionError("The shared database admission limit is reached")
    if free_bytes - write_bytes < limits.min_free_bytes:
        raise StorageAdmissionError("The shared storage free-space reserve would be exceeded")
