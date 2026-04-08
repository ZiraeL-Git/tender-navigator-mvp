from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from backend.app.api.schemas import CompanyProfileCreate
from backend.app.core.settings import Settings


class MvpAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._bootstrap_imports()

        from schemas import CompanyProfile  # type: ignore[import-not-found]
        from services.analysis import analyze_tender_package  # type: ignore[import-not-found]
        from services.document_io import build_tender_documents  # type: ignore[import-not-found]

        self.company_profile_model = CompanyProfile
        self.analyze_tender_package = analyze_tender_package
        self.build_tender_documents = build_tender_documents

    def _bootstrap_imports(self) -> None:
        mvp_dir = str(self.settings.mvp_dir)
        if mvp_dir not in sys.path:
            sys.path.insert(0, mvp_dir)

    def build_company_profile(self, payload: CompanyProfileCreate):
        return self.company_profile_model(
            company_name=payload.company_name,
            inn=payload.inn,
            region=payload.region,
            categories=payload.categories,
            has_license=payload.has_license,
            has_experience=payload.has_experience,
            can_prepare_fast=payload.can_prepare_fast,
            notes=payload.notes,
        )

    async def analyze_uploads(self, files: list[UploadFile], company_profile):
        uploaded_files = []

        for file in files:
            content = await file.read()
            buffer = BytesIO(content)
            buffer.name = file.filename or "uploaded-file"
            uploaded_files.append(buffer)

        documents = self.build_tender_documents(uploaded_files)
        return self.analyze_tender_package(documents=documents, profile=company_profile)

    def analyze_file_records(self, file_records: list[dict], company_profile):
        uploaded_files = []

        for file_record in file_records:
            file_path = Path(file_record["stored_path"])
            content = file_path.read_bytes()
            buffer = BytesIO(content)
            buffer.name = file_record["filename"]
            uploaded_files.append(buffer)

        documents = self.build_tender_documents(uploaded_files)
        return self.analyze_tender_package(documents=documents, profile=company_profile)
