from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_access_token


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract org_id from JWT token and inject into request.state."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip middleware for certain paths
        if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        org_id = None
        
        if auth_header:
            try:
                # Extract token from "Bearer <token>"
                scheme, token = auth_header.split()
                if scheme.lower() == "bearer":
                    payload = decode_access_token(token)
                    if payload:
                        org_id = payload.get("org_id")
            except (ValueError, AttributeError):
                pass
        
        # Inject org_id into request.state
        request.state.org_id = org_id
        
        response = await call_next(request)
        return response

