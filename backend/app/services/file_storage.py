from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.app.core.settings import Settings


class FileStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    async def save_uploads(self, folder_name: str, files: list[UploadFile]) -> list[dict]:
        target_dir = self._prepare_dir(folder_name)
        records: list[dict] = []

        for index, file in enumerate(files, start=1):
            content = await file.read()
            original_name = file.filename or f"upload-{index}"
            safe_name = self._safe_filename(original_name, index)
            target_path = target_dir / safe_name
            target_path.write_bytes(content)
            records.append(
                {
                    "filename": original_name,
                    "stored_path": str(target_path),
                    "content_type": file.content_type or "application/octet-stream",
                    "size": len(content),
                    "kind": "uploaded",
                }
            )

        return records

    def save_generated_file(
        self,
        folder_name: str,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        kind: str,
    ) -> dict:
        target_dir = self._prepare_dir(folder_name)
        safe_name = self._safe_filename(filename, 0)
        target_path = target_dir / safe_name
        target_path.write_bytes(content)
        return {
            "filename": filename,
            "stored_path": str(target_path),
            "content_type": content_type,
            "size": len(content),
            "kind": kind,
        }

    def create_folder_name(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"

    def _prepare_dir(self, folder_name: str) -> Path:
        target_dir = self.settings.uploads_dir / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _safe_filename(self, filename: str, index: int) -> str:
        candidate = filename.replace("\\", "_").replace("/", "_").strip()
        if not candidate:
            candidate = f"document-{index}"
        return candidate
