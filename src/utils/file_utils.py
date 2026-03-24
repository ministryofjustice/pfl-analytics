"""File handling utilities."""
import hashlib
import logging
import pandas as pd
import defusedxml
from io import BytesIO
from pathlib import Path

# Patch stdlib XML parsers to block XML bomb / XXE attacks before openpyxl
# loads any Excel file.
defusedxml.defuse_stdlib()

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

# Magic-byte signatures for binary formats
_MAGIC_BYTES = {
    'xlsx': b'PK\x03\x04',        # ZIP-based Office Open XML
    'xls':  b'\xD0\xCF\x11\xE0',  # OLE2 Compound Document
}


def validate_file(file_path) -> None:
    """Validate a file's size and content before processing.

    Raises ValueError with a safe, user-facing message if the file fails
    validation.  The original details are written to the application log so
    they are visible to operators without being exposed to end-users.
    """
    path = Path(file_path)
    suffix = path.suffix.lower().lstrip('.')

    # --- size check ---
    try:
        size = path.stat().st_size
    except OSError as exc:
        logger.error("Could not stat file %s: %s", path, exc)
        raise ValueError("The selected file could not be read.") from exc

    if size == 0:
        raise ValueError("The selected file is empty.")
    if size > MAX_FILE_SIZE_BYTES:
        logger.warning("File %s rejected: size %d bytes exceeds limit", path, size)
        raise ValueError("File exceeds the maximum allowed size of 100 MB.")

    # --- magic-byte / content-type check ---
    try:
        with open(path, 'rb') as fh:
            header = fh.read(512)
    except OSError as exc:
        logger.error("Could not read file %s: %s", path, exc)
        raise ValueError("The selected file could not be read.") from exc

    if suffix in _MAGIC_BYTES:
        expected = _MAGIC_BYTES[suffix]
        if not header[:len(expected)] == expected:
            logger.warning(
                "File %s has extension .%s but unexpected magic bytes %s",
                path, suffix, header[:4].hex()
            )
            raise ValueError("File content does not match its declared type.")
    elif suffix == 'csv':
        # CSV must be decodable as UTF-8 or Latin-1 text
        for encoding in ('utf-8', 'latin-1'):
            try:
                header.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.warning("File %s rejected: not valid text content", path)
            raise ValueError("CSV file does not appear to contain valid text data.")

    # --- SHA-256 hash for audit trail ---
    sha256 = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            sha256.update(chunk)
    logger.info("File accepted: %s | size=%d bytes | sha256=%s", path.name, size, sha256.hexdigest())


def create_excel_download(dataframes_dict):
    """
    Create an Excel file with multiple sheets from a dictionary of DataFrames.

    Args:
        dataframes_dict: Dictionary with sheet names as keys and DataFrames as values

    Returns:
        BytesIO object containing the Excel file
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            # Create a copy to avoid modifying the original dataframe
            df_copy = df.copy()

            # Convert timezone-aware datetime columns to timezone-unaware
            for col in df_copy.select_dtypes(include=['datetime64[ns, UTC]', 'datetimetz']).columns:
                if hasattr(df_copy[col].dtype, 'tz') and df_copy[col].dtype.tz is not None:
                    df_copy[col] = df_copy[col].dt.tz_localize(None)

            df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output
