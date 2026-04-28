# src/anki_builder/constants.py
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5"
GEMINI_ENRICH_MODEL = "gemini-3-flash-preview"
MINIMAX_IMAGE_URL = "https://api.minimax.io/v1/image_generation"
MINIMAX_IMAGE_MODEL = "image-01"
MAX_RETRIES = 3

# Card status values
STATUS_EXTRACTED = "extracted"
STATUS_ENRICHED = "enriched"
STATUS_COMPLETE = "complete"

# Supported file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".heic", ".heif"}
