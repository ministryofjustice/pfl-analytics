"""File handling utilities."""
import hashlib
import logging
import pandas as pd
import defusedxml
from io import BytesIO
from pathlib import Path

from utils.audit_log import log_event

defusedxml.defuse_stdlib()

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

_MAGIC_BYTES = {
    'xlsx': b'PK\x03\x04',
    'xls':  b'\xD0\xCF\x11\xE0',
}


def validate_file(file_path) -> None:
    """Validate a file's size and content before processing.

    Raises ValueError with a safe, user-facing message if validation fails.
    """
    path = Path(file_path)
    suffix = path.suffix.lower().lstrip('.')

    try:
        size = path.stat().st_size
    except OSError as exc:
        logger.error("Could not stat file %s: %s", path, exc)
        raise ValueError("The selected file could not be read.") from exc

    if size == 0:
        log_event("file_rejected", filename=path.name, reason="empty_file")
        raise ValueError("The selected file is empty.")
    if size > MAX_FILE_SIZE_BYTES:
        logger.warning("File %s rejected: size %d bytes exceeds limit", path, size)
        log_event("file_rejected", filename=path.name, reason="exceeds_size_limit", size_bytes=size)
        raise ValueError("File exceeds the maximum allowed size of 100 MB.")

    try:
        with open(path, 'rb') as fh:
            header = fh.read(512)
    except OSError as exc:
        logger.error("Could not read file %s: %s", path, exc)
        raise ValueError("The selected file could not be read.") from exc

    if suffix in _MAGIC_BYTES:
        expected = _MAGIC_BYTES[suffix]
        if not header[:len(expected)] == expected:
            logger.warning("File %s has extension .%s but unexpected magic bytes %s",
                           path, suffix, header[:4].hex())
            log_event("file_rejected", filename=path.name, reason="magic_byte_mismatch",
                      extension=suffix, magic_bytes=header[:4].hex())
            raise ValueError("File content does not match its declared type.")
    elif suffix == 'csv':
        for encoding in ('utf-8', 'latin-1'):
            try:
                header.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.warning("File %s rejected: not valid text content", path)
            log_event("file_rejected", filename=path.name, reason="invalid_text_encoding")
            raise ValueError("CSV file does not appear to contain valid text data.")

    sha256 = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            sha256.update(chunk)
    digest = sha256.hexdigest()
    logger.info("File accepted: %s | size=%d bytes | sha256=%s", path.name, size, digest)
    log_event("file_accepted", filename=path.name, size_bytes=size, sha256=digest)


def create_excel_download(dataframes_dict):
    """Create an Excel file with multiple sheets from a dictionary of DataFrames."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            df_copy = df.copy()
            for col in df_copy.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
                if hasattr(df_copy[col].dtype, 'tz') and df_copy[col].dtype.tz is not None:
                    df_copy[col] = df_copy[col].dt.tz_localize(None)
            df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output
