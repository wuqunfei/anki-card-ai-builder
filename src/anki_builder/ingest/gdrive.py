import re
import tempfile
from pathlib import Path

import httpx

from anki_builder.schema import Card
from anki_builder.ingest.excel import ingest_excel
from anki_builder.ingest.pdf import ingest_pdf
from anki_builder.ingest.image import ingest_image

GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GDRIVE_URL_PATTERN = re.compile(r"(?:https?://)?drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)")

EXCEL_EXTENSIONS = {".xlsx", ".csv"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
ALL_EXTENSIONS = EXCEL_EXTENSIONS | PDF_EXTENSIONS | IMAGE_EXTENSIONS


def extract_folder_id(url_or_id: str) -> str:
    match = GDRIVE_URL_PATTERN.search(url_or_id)
    if match:
        return match.group(1)
    return url_or_id  # Assume it's already a folder ID


def list_files_in_folder(folder_id: str, google_api_key: str) -> list[dict]:
    files = []
    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "key": google_api_key,
            "fields": "nextPageToken, files(id, name, mimeType)",
            "pageSize": 100,
        }
        if page_token:
            params["pageToken"] = page_token
        resp = httpx.get(f"{GDRIVE_API_BASE}/files", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return files


def download_file(file_id: str, file_name: str, google_api_key: str, dest_dir: Path) -> Path:
    dest_path = dest_dir / file_name
    params = {"alt": "media", "key": google_api_key}
    with httpx.stream("GET", f"{GDRIVE_API_BASE}/files/{file_id}", params=params, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return dest_path


def ingest_gdrive_folder(
    url_or_id: str,
    target_language: str,
    google_api_key: str,
    minimax_api_key: str,
    source_language: str = "de",
) -> list[Card]:
    folder_id = extract_folder_id(url_or_id)
    files = list_files_in_folder(folder_id, google_api_key)

    all_cards: list[Card] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        for file_info in files:
            name = file_info["name"]
            suffix = Path(name).suffix.lower()
            if suffix not in ALL_EXTENSIONS:
                continue

            local_path = download_file(file_info["id"], name, google_api_key, dest_dir)

            if suffix in EXCEL_EXTENSIONS:
                cards = ingest_excel(local_path, target_language, source_language)
            elif suffix in PDF_EXTENSIONS:
                cards = ingest_pdf(local_path, target_language, minimax_api_key, source_language)
            elif suffix in IMAGE_EXTENSIONS:
                cards = ingest_image(local_path, target_language, minimax_api_key, source_language)
            else:
                continue

            all_cards.extend(cards)

    return all_cards
