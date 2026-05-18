"""Memory-aware upload normalization for regular files and archives before OCR begins."""

import asyncio
import os
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ArchiveExtractionError, UnsupportedFileTypeError
from app.services.logging_service import LoggingService


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}
SUPPORTED_DOC_EXTENSIONS = {".pdf", ".docx", ".doc"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".zip", ".tar", ".tgz", ".tar.gz"}
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS | SUPPORTED_ARCHIVE_EXTENSIONS


@dataclass
class NormalizedDocument:
    document_id: str
    filename: str
    source_filename: str
    file_path: Path
    file_extension: str
    content_type: str | None
    file_size_bytes: int
    is_archive_member: bool = False
    working_directory: Path | None = None


class FileHandlerService:
    def __init__(self) -> None:
        self.logger = LoggingService()
        settings.temp_directory_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_file_extension(filename: str) -> str:
        suffixes = Path(filename).suffixes
        if not suffixes:
            return ""
        if len(suffixes) >= 2 and "".join(suffixes[-2:]).lower() == ".tar.gz":
            return ".tar.gz"
        return suffixes[-1].lower()

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        return cls.get_file_extension(filename) in ALL_SUPPORTED_EXTENSIONS or filename.lower().endswith(".tar.gz")

    @classmethod
    def is_archive(cls, filename: str) -> bool:
        return cls.get_file_extension(filename) in {".zip", ".tar", ".tgz", ".tar.gz"} and (
            filename.lower().endswith(".zip")
            or filename.lower().endswith(".tar")
            or filename.lower().endswith(".tgz")
            or filename.lower().endswith(".tar.gz")
        )

    async def normalize_upload(self, upload: UploadFile) -> list[NormalizedDocument]:
        filename = upload.filename or "unnamed_upload"
        if not self.is_supported(filename):
            raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")

        upload_path = await self._spool_upload(upload)
        if self.is_archive(filename):
            # Archives are extracted to temp files so later stages can process each member independently.
            return await asyncio.to_thread(self._extract_archive_to_documents, filename, upload.content_type, upload_path)

        document = self._create_document(
            filename=filename,
            source_filename=filename,
            file_path=upload_path,
            content_type=upload.content_type,
            is_archive_member=False,
        )
        return [document]

    async def cleanup_documents(self, documents: Iterable[NormalizedDocument]) -> None:
        await asyncio.to_thread(self._cleanup_documents_sync, list(documents))

    async def _spool_upload(self, upload: UploadFile) -> Path:
        # Stream uploads to disk instead of reading everything into RAM at once.
        await upload.seek(0)
        suffix = self.get_file_extension(upload.filename or "") or ".bin"
        fd, path = tempfile.mkstemp(
            suffix=suffix,
            prefix="referral_upload_",
            dir=settings.temp_directory_path,
        )
        os.close(fd)
        destination = Path(path)

        def copy_stream() -> None:
            upload.file.seek(0)
            with destination.open("wb") as target:
                shutil.copyfileobj(upload.file, target, settings.SPOOL_CHUNK_SIZE_BYTES)

        await asyncio.to_thread(copy_stream)
        return destination

    def _extract_archive_to_documents(
        self,
        source_filename: str,
        content_type: str | None,
        archive_path: Path,
    ) -> list[NormalizedDocument]:
        # Each archive member becomes its own normalized document so batch isolation remains intact.
        documents: list[NormalizedDocument] = []
        working_directory = Path(
            tempfile.mkdtemp(prefix="referral_archive_", dir=settings.temp_directory_path)
        )

        try:
            if source_filename.lower().endswith(".zip"):
                iterator = self._iter_zip_members(archive_path)
            else:
                iterator = self._iter_tar_members(archive_path)

            for index, (member_name, member_stream, member_size) in enumerate(iterator, start=1):
                # Enforce file-count and member-size limits to avoid exhausting temp storage or memory.
                if index > settings.MAX_ARCHIVE_FILES:
                    raise ArchiveExtractionError(
                        f"Archive exceeded safe member count limit ({settings.MAX_ARCHIVE_FILES})"
                    )

                if member_size > settings.MAX_ARCHIVE_MEMBER_SIZE_MB * 1024 * 1024:
                    self.logger.warning(
                        "archive_member_skipped",
                        stage="intake",
                        document_id="-",
                        member_name=member_name,
                        reason="member_size_limit_exceeded",
                    )
                    continue

                if not self.is_supported(member_name) or self.is_archive(member_name):
                    continue

                destination = working_directory / f"{uuid4().hex}{self.get_file_extension(member_name)}"
                with destination.open("wb") as target:
                    shutil.copyfileobj(member_stream, target, settings.SPOOL_CHUNK_SIZE_BYTES)

                documents.append(
                    self._create_document(
                        filename=Path(member_name).name,
                        source_filename=source_filename,
                        file_path=destination,
                        content_type=content_type,
                        is_archive_member=True,
                        working_directory=working_directory,
                    )
                )

            if not documents:
                raise ArchiveExtractionError("Archive did not contain supported processable files")

            return documents
        except Exception:
            shutil.rmtree(working_directory, ignore_errors=True)
            raise
        finally:
            archive_path.unlink(missing_ok=True)

    def _iter_zip_members(self, archive_path: Path):
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = Path(member.filename).name
                if not member_name or member_name.startswith(".") or member_name.startswith("__"):
                    continue
                with archive.open(member, "r") as stream:
                    yield member_name, stream, member.file_size

    def _iter_tar_members(self, archive_path: Path):
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = Path(member.name).name
                if not member_name or member_name.startswith(".") or member_name.startswith("__"):
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    continue
                with stream:
                    yield member_name, stream, member.size

    def _create_document(
        self,
        *,
        filename: str,
        source_filename: str,
        file_path: Path,
        content_type: str | None,
        is_archive_member: bool,
        working_directory: Path | None = None,
    ) -> NormalizedDocument:
        return NormalizedDocument(
            document_id=uuid4().hex,
            filename=filename,
            source_filename=source_filename,
            file_path=file_path,
            file_extension=self.get_file_extension(filename),
            content_type=content_type,
            file_size_bytes=file_path.stat().st_size,
            is_archive_member=is_archive_member,
            working_directory=working_directory,
        )

    def _cleanup_documents_sync(self, documents: list[NormalizedDocument]) -> None:
        # Temp files are always best-effort cleanup because processing correctness matters more than cleanup races.
        cleaned_directories: set[Path] = set()
        for document in documents:
            document.file_path.unlink(missing_ok=True)
            if document.working_directory and document.working_directory not in cleaned_directories:
                shutil.rmtree(document.working_directory, ignore_errors=True)
                cleaned_directories.add(document.working_directory)
