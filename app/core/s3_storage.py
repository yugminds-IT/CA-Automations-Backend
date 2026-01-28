"""
S3 storage utilities for handling file uploads to AWS S3 or S3-compatible services.
"""
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from app.core.file_storage import validate_file_size, generate_unique_filename
import logging

logger = logging.getLogger(__name__)


def get_s3_client():
    """
    Create and return an S3 client.
    
    Returns:
        boto3 S3 client
        
    Raises:
        HTTPException: If S3 configuration is missing
    """
    # Validate required S3 settings
    if not settings.AWS_ACCESS_KEY_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 storage is enabled but AWS_ACCESS_KEY_ID is not configured"
        )
    if not settings.AWS_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 storage is enabled but AWS_SECRET_ACCESS_KEY is not configured"
        )
    if not settings.AWS_S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 storage is enabled but AWS_S3_BUCKET_NAME is not configured"
        )
    
    client_kwargs = {
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region_name": settings.AWS_REGION or "us-east-1",
    }
    
    # Add endpoint URL for S3-compatible services (DigitalOcean Spaces, MinIO, etc.)
    if settings.AWS_S3_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
    
    return boto3.client("s3", **client_kwargs)


def get_s3_key(user_id: int, organization_id: int, stored_filename: str) -> str:
    """
    Generate S3 key (path) for a file.
    
    Args:
        user_id: ID of the user uploading the file
        organization_id: ID of the organization
        stored_filename: Unique stored filename
        
    Returns:
        S3 key (path)
    """
    return f"org_{organization_id}/user_{user_id}/{stored_filename}"


async def save_file_to_s3(file: UploadFile, user_id: int, organization_id: int) -> Tuple[str, str, str, int]:
    """
    Save an uploaded file to S3.
    
    Args:
        file: FastAPI UploadFile object
        user_id: ID of the user uploading the file
        organization_id: ID of the organization
        
    Returns:
        Tuple of (s3_key, stored_filename, file_type, file_size)
        
    Raises:
        HTTPException: If file cannot be saved
    """
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    validate_file_size(file_size)
    
    # Generate unique filename
    stored_filename, ext = generate_unique_filename(file.filename or "file")
    
    # Generate S3 key
    s3_key = get_s3_key(user_id, organization_id, stored_filename)
    
    # Get file type
    file_type = file.content_type or "application/octet-stream"
    
    # Upload to S3
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=content,
            ContentType=file_type,
            # Add metadata
            Metadata={
                "original_filename": file.filename or "file",
                "user_id": str(user_id),
                "organization_id": str(organization_id),
            }
        )
        logger.info(f"File uploaded to S3: {s3_key}")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to upload file to S3: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to S3: {str(e)}"
        )
    
    return s3_key, stored_filename, file_type, file_size


def delete_file_from_s3(s3_key: str) -> None:
    """
    Delete a file from S3.
    
    Args:
        s3_key: S3 key (path) of the file to delete
        
    Raises:
        HTTPException: If file cannot be deleted
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key
        )
        logger.info(f"File deleted from S3: {s3_key}")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to delete file from S3: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file from S3: {str(e)}"
        )


def get_s3_file_url(s3_key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for accessing a file from S3.
    
    Args:
        s3_key: S3 key (path) of the file
        expires_in: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Presigned URL for the file
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires_in
        )
        return url
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to generate S3 presigned URL: {str(e)}", exc_info=True)
        # Fallback to public URL if bucket is public
        if settings.AWS_S3_ENDPOINT_URL:
            return f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_S3_BUCKET_NAME}/{s3_key}"
        else:
            return f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION or 'us-east-1'}.amazonaws.com/{s3_key}"


def get_s3_file_stream(s3_key: str):
    """
    Get a file stream from S3 for downloading.
    
    Args:
        s3_key: S3 key (path) of the file
        
    Returns:
        File stream object
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key
        )
        return response["Body"]
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to get file from S3: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found in S3: {str(e)}"
        )


def create_s3_folder(folder_path: str, organization_id: Optional[int] = None, user_id: Optional[int] = None) -> str:
    """
    Create a folder (prefix) in S3.
    In S3, folders are created by uploading an empty object with a trailing slash.
    
    Args:
        folder_path: Folder path (e.g., "documents", "invoices/2024", "org_1/user_1/reports")
        organization_id: Optional organization ID to prepend to path
        user_id: Optional user ID to prepend to path
        
    Returns:
        S3 key of the created folder
        
    Raises:
        HTTPException: If folder cannot be created
    """
    try:
        s3_client = get_s3_client()
        
        # Build the full folder path
        if organization_id and user_id:
            # Use organization/user structure
            full_path = f"org_{organization_id}/user_{user_id}/{folder_path}"
        elif organization_id:
            # Use organization structure
            full_path = f"org_{organization_id}/{folder_path}"
        else:
            # Use root level
            full_path = folder_path
        
        # Ensure folder path ends with /
        if not full_path.endswith("/"):
            full_path += "/"
        
        # Create folder by uploading empty object with trailing slash
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=full_path,
            Body=b"",  # Empty body
            ContentType="application/x-directory"
        )
        
        logger.info(f"Created S3 folder: {full_path}")
        return full_path
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to create S3 folder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create folder: {str(e)}"
        )
