"""
Media and Image Upload Service for CivicFlow.

Handles:
- MIME type verification.
- Server-side image magic byte validation (JPEG, PNG, WebP).
- Payload size validation.
- Secure UUID-based filename generation to neutralize path traversal attacks.
- Safe file persistence to dedicated uploads directory.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status

from app.config import settings

logger = logging.getLogger("civicflow.media")

# Magic bytes signatures for supported image types
MAGIC_BYTES = {
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF", b"WEBP"],  # RIFF at 0..4, WEBP at 8..12
}

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def get_upload_directory() -> Path:
    """Returns the dedicated complaints upload directory, creating it if needed."""
    p = Path(settings.UPLOAD_DIR)
    if p.is_absolute():
        base_upload_dir = p
    else:
        base_upload_dir = Path(__file__).resolve().parent.parent.parent / p
    complaints_dir = base_upload_dir / "complaints"
    complaints_dir.mkdir(parents=True, exist_ok=True)
    return complaints_dir


def detect_image_format(content: bytes) -> str:
    """
    Inspects raw file header bytes to verify and detect the real image format.
    Does not rely on client-provided file extensions or MIME types.
    Returns: 'jpeg', 'png', 'webp' or raises HTTPException if invalid.
    """
    if len(content) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is too small or empty to be a valid image."
        )

    # Check JPEG
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    # Check PNG
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    # Check WebP (RIFF....WEBP)
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid image content. File signature does not match supported image formats (JPEG, PNG, WebP)."
    )


async def save_uploaded_image(file: UploadFile) -> Tuple[str, str]:
    """
    Validates and securely persists an uploaded civic complaint image.

    Validations:
    1. File existence and non-empty content.
    2. Client MIME type header validation.
    3. Maximum file size check (10 MB).
    4. Server-side binary magic byte inspection.
    5. Secure UUID-based storage filename (neutralizing path traversal).

    Returns:
        Tuple[str, str]: (relative_url_path, absolute_filesystem_path)
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is required."
        )

    # 1. Validate client-reported MIME type
    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{content_type}'. Allowed types: image/jpeg, image/png, image/webp."
        )

    # 2. Read content and validate file size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty."
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )


    # 3. Server-side content inspection (Magic Bytes)
    detected_format = detect_image_format(content)

    # Determine extension from verified format
    ext_map = {
        "jpeg": ".jpg",
        "png": ".png",
        "webp": ".webp"
    }
    extension = ext_map.get(detected_format, ".jpg")

    # 4. Generate random UUID filename (never use original filename)
    safe_filename = f"{uuid.uuid4().hex}{extension}"

    # -------------------------------------------------------------------------
    # Supabase Cloud Storage Backend (Production Free Tier)
    # -------------------------------------------------------------------------
    if getattr(settings, "STORAGE_BACKEND", "local").lower() == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.error("STORAGE_BACKEND is 'supabase' but SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloud storage service is not properly configured on server."
            )

        bucket = (settings.SUPABASE_STORAGE_BUCKET or "complaints").strip()
        upload_endpoint = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{safe_filename}"
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY.strip()}",
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY.strip(),
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(upload_endpoint, content=content, headers=headers)
                if res.status_code not in (200, 201):
                    logger.error("Supabase Storage upload failed HTTP %s: %s", res.status_code, res.text)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Unable to upload the image. Please try again."
                    )
                public_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{bucket}/{safe_filename}"
                logger.info("Successfully persisted evidence image to Supabase Storage: %s", public_url)
                return public_url, safe_filename
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Supabase Storage request encountered exception: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to upload the image. Please try again."
            )

    # -------------------------------------------------------------------------
    # Local Filesystem Storage (Local Development Fallback)
    # -------------------------------------------------------------------------
    upload_dir = get_upload_directory()
    dest_path = (upload_dir / safe_filename).resolve()

    # Ensure path stays inside upload directory (path traversal defense)
    if not str(dest_path).startswith(str(upload_dir.resolve())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path detected."
        )

    # Persist file to disk
    with open(dest_path, "wb") as f:
        f.write(content)

    # Store relative URL path accessible via the mounted /uploads static route
    relative_url = f"/uploads/complaints/{safe_filename}"
    return relative_url, str(dest_path)


def delete_uploaded_image(image_url: str) -> bool:
    """
    Safely deletes the uploaded physical evidence image file associated with image_url.
    Supports both Supabase Storage objects and local filesystem uploads.
    """
    if not image_url:
        return True
    try:
        # Check if Supabase cloud storage URL
        if image_url.startswith("http://") or image_url.startswith("https://"):
            if "supabase" in image_url and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
                filename = os.path.basename(image_url.split("?")[0])
                bucket = (settings.SUPABASE_STORAGE_BUCKET or "complaints").strip()
                delete_endpoint = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}"
                headers = {
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY.strip()}",
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY.strip(),
                    "Content-Type": "application/json",
                }
                import httpx
                with httpx.Client(timeout=10.0) as client:
                    resp = client.request("DELETE", delete_endpoint, json={"prefixes": [filename]}, headers=headers)
                    if resp.status_code in (200, 204):
                        logger.info("Deleted object from Supabase Storage: %s", filename)
                        return True
                    logger.warning("Supabase delete returned HTTP %s: %s", resp.status_code, resp.text)
                    return False
            return True

        filename = os.path.basename(image_url)
        upload_dir = get_upload_directory().resolve()
        file_path = (upload_dir / filename).resolve()
        if not str(file_path).startswith(str(upload_dir)):
            logger.warning("Attempted path traversal in delete_uploaded_image: %s", image_url)
            return False
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.info("Deleted physical evidence file: %s", file_path)
        return True
    except Exception as e:
        logger.warning("Error deleting uploaded image %s: %s", image_url, e)
        return False


def read_image_bytes(image_url: str) -> Tuple[bytes, str]:
    """
    Reads image bytes and determines media type from a local or cloud-stored image.
    Supports both local filesystem paths and remote cloud storage URLs (with Supabase auth).
    """
    if not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image reference is missing."
        )

    if image_url.startswith("http://") or image_url.startswith("https://"):
        try:
            import httpx
            headers = {}
            if "supabase" in image_url and getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", ""):
                headers["Authorization"] = f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY.strip()}"
                headers["apikey"] = settings.SUPABASE_SERVICE_ROLE_KEY.strip()

            with httpx.Client(timeout=20.0) as client:
                resp = client.get(image_url, headers=headers)
                resp.raise_for_status()
                content = resp.content
                content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                return content, content_type
        except Exception as exc:
            logger.error("Failed to read image from remote storage: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to retrieve evidence image from cloud storage: {exc}"
            )

    # Local filesystem resolution
    filename = os.path.basename(image_url)
    upload_dir = get_upload_directory().resolve()
    image_path = (upload_dir / filename).resolve()

    if not str(image_path).startswith(str(upload_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image storage path."
        )

    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical image file not found on disk."
        )

    ext = image_path.suffix.lower()
    media_type = "image/jpeg"
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    with open(image_path, "rb") as f:
        return f.read(), media_type

