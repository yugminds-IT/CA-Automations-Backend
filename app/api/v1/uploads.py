"""
File upload API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from app.db.session import get_db
from app.db.models.upload_file import UploadFile as UploadFileModel
from app.db.models.user import User, UserRole
from app.db.models.organization import Organization
from app.db.models.client import Client
from app.core.file_storage import save_uploaded_file, delete_file, get_file_url
from app.core.security import decode_access_token


router = APIRouter()


# Pydantic schemas for API responses
class FileResponseSchema(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_at: datetime
    url: str
    organization_id: int
    organization_name: Optional[str] = None
    client_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class UploadFilesResponse(BaseModel):
    files: List[FileResponseSchema]
    message: str


def get_token_from_request(request: Request, token: Optional[str] = None) -> Optional[str]:
    """
    Extract token from Authorization header or query parameter.
    
    Args:
        request: FastAPI Request object
        token: Optional token from query parameter
        
    Returns:
        Token string or None
    """
    # First check query parameter
    if token:
        return token
    
    # Then check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            scheme, header_token = auth_header.split()
            if scheme.lower() == "bearer":
                return header_token
        except ValueError:
            pass
    
    return None


def get_current_user_id(request: Request, token: Optional[str] = None) -> Tuple[int, int]:
    """
    Extract user ID and org ID from JWT token.
    Accepts token from Authorization header or query parameter.
    Raises 401 if token is missing or invalid.
    
    Args:
        request: FastAPI Request object
        token: Optional token from query parameter (for preview support)
        
    Returns:
        Tuple of (user_id, org_id)
    """
    # Get token from query parameter or header
    token_str = get_token_from_request(request, token)
    
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid access token."
        )
    
    try:
        payload = decode_access_token(token_str)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = payload.get("user_id")
        org_id = payload.get("org_id")
        
        if not user_id or not org_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required information"
            )
        
        return user_id, org_id
    
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


def build_file_response_schema(db_file: UploadFileModel, db: Session, download_url: str) -> FileResponseSchema:
    """
    Build FileResponseSchema with organization and client information.
    
    Args:
        db_file: UploadFile database model instance
        db: Database session
        download_url: Download URL for the file
        
    Returns:
        FileResponseSchema instance
    """
    # Get organization information
    organization = db.query(Organization).filter(Organization.id == db_file.organization_id).first()
    organization_name = organization.name if organization else None
    
    # Find client_id if the user is a CLIENT
    client_id = None
    user = db.query(User).filter(User.id == db_file.user_id).first()
    if user and user.role == UserRole.CLIENT:
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if client:
            client_id = client.id
    
    return FileResponseSchema(
        id=db_file.id,
        filename=db_file.filename,
        file_type=db_file.file_type,
        file_size=db_file.file_size,
        uploaded_at=db_file.uploaded_at,
        url=download_url,
        organization_id=db_file.organization_id,
        organization_name=organization_name,
        client_id=client_id
    )


@router.post("/", response_model=UploadFilesResponse, status_code=status.HTTP_200_OK)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload one or more files.
    
    Accepts multiple files in a single request.
    Maximum file size: 50MB per file.
    Files are stored securely and associated with the authenticated user and organization.
    """
    # Get user ID and org ID from token
    user_id, org_id = get_current_user_id(request)
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify user belongs to the organization from token
    if user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    uploaded_files = []
    
    try:
        for file in files:
            if not file.filename:
                continue  # Skip empty files
            
            # Save file to disk
            file_path, stored_filename, file_type, file_size = await save_uploaded_file(
                file, user_id, org_id
            )
            
            # Generate URL
            url = get_file_url(file_path, stored_filename)
            
            # Create database record
            db_file = UploadFileModel(
                filename=file.filename,
                stored_filename=stored_filename,
                file_type=file_type,
                file_size=file_size,
                file_path=file_path,
                url=url,
                user_id=user_id,
                organization_id=org_id
            )
            db.add(db_file)
            db.flush()  # Flush to get the ID
            
            # Generate download URL (use the download endpoint)
            download_url = f"/api/v1/uploads/{db_file.id}/download"
            
            # Build response with organization and client info
            file_response = build_file_response_schema(db_file, db, download_url)
            uploaded_files.append(file_response)
        
        # Commit all files
        db.commit()
        
        return UploadFilesResponse(
            files=uploaded_files,
            message="Files uploaded successfully"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (like file size errors)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.get("/", response_model=List[FileResponseSchema])
def list_files(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    List uploaded files for the authenticated user.
    
    Returns only files from the user's organization.
    Files are sorted by upload date (newest first).
    """
    # Get user ID and org ID from token
    user_id, org_id = get_current_user_id(request)
    
    # Query files for this organization with organization relationship
    query = db.query(UploadFileModel).filter(
        UploadFileModel.organization_id == org_id
    ).order_by(UploadFileModel.uploaded_at.desc())
    
    # Get total count
    total = query.count()
    
    # Paginate
    files = query.offset(skip).limit(limit).all()
    
    # Build response with organization and client info
    return [
        build_file_response_schema(file, db, f"/api/v1/uploads/{file.id}/download")
        for file in files
    ]


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="Access token for preview support (alternative to Authorization header)"),
    db: Session = Depends(get_db)
):
    """
    Download/preview an uploaded file.
    
    Returns the file content with appropriate headers for preview/download.
    Only allows access to files from the user's organization.
    
    Supports token authentication via:
    - Authorization header: Bearer <token> (for downloads)
    - Query parameter: ?token=<token> (for previews in iframe/img tags)
    """
    # Get user ID and org ID from token (supports both header and query param)
    user_id, org_id = get_current_user_id(request, token)
    
    # Find the file
    db_file = db.query(UploadFileModel).filter(UploadFileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify file belongs to user's organization
    if db_file.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File does not belong to your organization."
        )
    
    # Check if file exists on disk
    file_path = Path(db_file.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    # Return file with appropriate headers for preview/download
    return FileResponse(
        path=str(file_path),
        filename=db_file.filename,
        media_type=db_file.file_type
    )


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
def delete_file_endpoint(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Delete an uploaded file.
    
    Only allows deletion of files from the user's organization.
    Deletes both the database record and the physical file.
    """
    # Get user ID and org ID from token
    user_id, org_id = get_current_user_id(request)
    
    # Find the file
    db_file = db.query(UploadFileModel).filter(UploadFileModel.id == file_id).first()
    
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify file belongs to user's organization
    if db_file.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File does not belong to your organization."
        )
    
    try:
        # Delete physical file
        delete_file(db_file.file_path)
        
        # Delete database record
        db.delete(db_file)
        db.commit()
        
        return {"message": "File deleted successfully"}
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )
