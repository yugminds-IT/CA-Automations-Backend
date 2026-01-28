"""
File storage utilities for handling file uploads.
Supports both local filesystem and S3 storage backends.
"""
import os
import uuid
import re
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings


# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

# Base upload directory (relative to project root)
UPLOAD_DIR = "uploads"


def get_upload_directory() -> Path:
    """
    Get the upload directory path. Creates it if it doesn't exist.
    
    Returns:
        Path object for the upload directory
    """
    upload_path = Path(UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks and ensure safety.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components (../, ./, etc.)
    filename = os.path.basename(filename)
    
    # Remove any characters that could be problematic
    # Allow: alphanumeric, dots, hyphens, underscores, spaces
    filename = re.sub(r'[^a-zA-Z0-9._\s-]', '', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = "file"
    
    # Limit filename length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    return filename


def generate_unique_filename(original_filename: str) -> Tuple[str, str]:
    """
    Generate a unique filename to prevent conflicts.
    
    Args:
        original_filename: Original filename from upload
        
    Returns:
        Tuple of (stored_filename, file_extension)
    """
    # Sanitize the original filename
    sanitized = sanitize_filename(original_filename)
    
    # Get file extension
    _, ext = os.path.splitext(sanitized)
    
    # Generate unique filename using UUID
    unique_id = str(uuid.uuid4())
    stored_filename = f"{unique_id}{ext}"
    
    return stored_filename, ext


def validate_file_size(file_size: int) -> None:
    """
    Validate file size against maximum allowed size.
    
    Args:
        file_size: File size in bytes
        
    Raises:
        HTTPException: If file size exceeds maximum
    """
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
        )


async def save_uploaded_file(file: UploadFile, user_id: int, organization_id: int) -> Tuple[str, str, str, int]:
    """
    Save an uploaded file using the configured storage backend (local or S3).
    
    Args:
        file: FastAPI UploadFile object
        user_id: ID of the user uploading the file
        organization_id: ID of the organization
        
    Returns:
        Tuple of (file_path_or_key, stored_filename, file_type, file_size)
        - For local: file_path is the full file path
        - For S3: file_path is the S3 key
        
    Raises:
        HTTPException: If file cannot be saved
    """
    # Use S3 if configured, otherwise use local storage
    if settings.FILE_STORAGE_BACKEND == "s3":
        from app.core.s3_storage import save_file_to_s3
        return await save_file_to_s3(file, user_id, organization_id)
    else:
        # Local filesystem storage
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        validate_file_size(file_size)
        
        # Generate unique filename
        stored_filename, ext = generate_unique_filename(file.filename or "file")
        
        # Create organization-specific directory structure: uploads/org_{org_id}/user_{user_id}/
        upload_dir = get_upload_directory()
        org_user_dir = upload_dir / f"org_{organization_id}" / f"user_{user_id}"
        org_user_dir.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = org_user_dir / stored_filename
        
        # Write file to disk
        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Get file type
        file_type = file.content_type or "application/octet-stream"
        
        return str(file_path), stored_filename, file_type, file_size


def delete_file(file_path_or_key: str) -> None:
    """
    Delete a file using the configured storage backend.
    
    Args:
        file_path_or_key: For local: file path, For S3: S3 key
        
    Raises:
        HTTPException: If file cannot be deleted
    """
    if settings.FILE_STORAGE_BACKEND == "s3":
        from app.core.s3_storage import delete_file_from_s3
        delete_file_from_s3(file_path_or_key)
    else:
        # Local filesystem storage
        try:
            path = Path(file_path_or_key)
            if path.exists():
                path.unlink()
                # Try to remove empty parent directories
                try:
                    path.parent.rmdir()
                    # Try to remove org directory if empty
                    try:
                        path.parent.parent.rmdir()
                    except OSError:
                        pass  # Directory not empty, ignore
                except OSError:
                    pass  # Directory not empty, ignore
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )


def get_file_url(file_path_or_key: str, stored_filename: str) -> str:
    """
    Generate access URL for a file.
    
    Args:
        file_path_or_key: For local: full file path, For S3: S3 key
        stored_filename: Stored filename
        
    Returns:
        Access URL for the file
    """
    if settings.FILE_STORAGE_BACKEND == "s3":
        from app.core.s3_storage import get_s3_file_url
        # For S3, return presigned URL (expires in 1 hour)
        # In production, you might want to use a CDN URL instead
        return get_s3_file_url(file_path_or_key, expires_in=3600)
    else:
        # Local filesystem storage
        # Extract relative path from uploads directory
        path = Path(file_path_or_key)
        upload_dir = get_upload_directory()
        
        try:
            # Get relative path from uploads directory
            relative_path = path.relative_to(upload_dir)
            # Convert to URL path (use forward slashes)
            url_path = f"/uploads/{str(relative_path).replace(os.sep, '/')}"
            return url_path
        except ValueError:
            # If file is not in uploads directory, use stored filename
            return f"/uploads/{stored_filename}"

