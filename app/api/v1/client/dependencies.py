"""
Dependencies for client API endpoints.
"""
from fastapi import Request, HTTPException, status
from app.core.security import decode_access_token
from app.db.models.user import UserRole


def get_current_user_role(request: Request) -> str:
    """
    Extract user role from JWT token in Authorization header.
    Raises 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme. Use Bearer token."
            )
        
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        role = payload.get("role")
        if not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing role information"
            )
        
        return role
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )


def require_admin_or_employee(request: Request):
    """
    Dependency to require admin or employee role.
    Raises 403 if user is not admin or employee.
    """
    role = get_current_user_role(request)
    
    if role not in [UserRole.ADMIN.value, UserRole.EMPLOYEE.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin or employee role"
        )
    
    return role

