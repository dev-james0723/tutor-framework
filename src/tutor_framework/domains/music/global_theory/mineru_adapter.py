"""Reuse the installed MinerU helper; never retrieve credentials or bypass access."""
from __future__ import annotations
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from .mineru import load_existing_mineru_result, mineru_configuration


@dataclass(frozen=True)
class ExistingMinerUResult:
    resource_id: str
    result_directory: Path
    expected_sha256: str
    requires_external_processing = False
    verified_mineru_adapter = True

    def __call__(self, original_bytes: bytes) -> dict:
        if hashlib.sha256(original_bytes).hexdigest() != self.expected_sha256:
            raise ValueError('original bytes differ from the requested MinerU resource')
        return load_existing_mineru_result(self.result_directory, expected_pdf_sha256=self.expected_sha256,
                                           extract_questions=True)


@dataclass(frozen=True)
class ExistingMinerUHelper:
    resource_id: str
    original_path: Path
    output_directory: Path
    expected_sha256: str
    cloud_processing_authorized: bool = False
    cost_authorized: bool = False
    no_save: bool = False
    language: str = 'en'
    requires_external_processing = True
    verified_mineru_adapter = True

    def __call__(self, original_bytes: bytes) -> dict:
        for flag in (self.cloud_processing_authorized, self.cost_authorized, self.no_save):
            if type(flag) is not bool:
                raise ValueError('processing and privacy consent must be explicit booleans')
        if self.no_save or not self.cloud_processing_authorized or not self.cost_authorized:
            raise PermissionError('MinerU requires separate cloud/cost consent and cannot satisfy no-save')
        if not os.environ.get('MINERU_API_TOKEN'):
            raise RuntimeError('MINERU_CREDENTIAL_UNAVAILABLE: supply through an approved environment; no credential-store access is attempted')
        configuration = mineru_configuration()
        if not configuration['helper_found']:
            raise RuntimeError('existing MinerU helper not found; no replacement parser is created')
        original = Path(self.original_path).expanduser().resolve(strict=True)
        if original.is_symlink() or original.stat().st_size > 100_000_000:
            raise ValueError('original PDF exceeds the authorized bounded input')
        if original.read_bytes() != original_bytes or hashlib.sha256(original_bytes).hexdigest() != self.expected_sha256:
            raise ValueError('original resource bytes changed')
        destination = Path(self.output_directory).expanduser().resolve()
        if destination.exists():
            raise ValueError('MinerU output requires a new destination')
        command = [sys.executable, configuration['helper_path'], '--pdf', str(original),
                   '--output-dir', str(destination), '--model-version', 'vlm',
                   '--language', self.language, '--max-wait', '600', '--poll-interval', '5']
        # Do not publish helper output: provider messages may contain signed URLs.
        try:
            process = subprocess.run(command, capture_output=True, timeout=660, check=False,
                                     env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('MinerU timed out; preserve provider receipt and reconcile before retrying') from error
        if process.returncode:
            raise RuntimeError('existing MinerU helper failed; inspect local provider receipt without exposing signed URLs')
        result = load_existing_mineru_result(destination, expected_pdf_sha256=self.expected_sha256,
                                             extract_questions=True)
        result.update(parser_origin='existing_mineru_helper_api', new_api_submission=True)
        return result
