from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
import secrets
import base64
import bcrypt
from app.core.config import settings

# Use bcrypt directly to avoid passlib compatibility issues with bcrypt 5.0.0


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        if not plain_password or not isinstance(plain_password, str):
            return False
        
        if not hashed_password or not isinstance(hashed_password, str):
            return False
        
        # Convert password to bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify using bcrypt
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    Bcrypt has a 72-byte limit for passwords.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    
    # Bcrypt has a 72-byte limit for passwords
    if len(password_bytes) > 72:
        raise ValueError("Password is too long. Maximum length is 72 bytes.")
    
    # Generate salt and hash password using bcrypt directly
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, ""


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, min_length: int = 1000) -> str:
    """
    Create a JWT access token with minimum length requirement.
    Ensures token is at least min_length characters by adding padding data in payload.
    
    Args:
        data: Dictionary of claims to include in token
        expires_delta: Token expiration time delta
        min_length: Minimum token length in characters (default: 1000)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at time
        "jti": secrets.token_urlsafe(48),  # JWT ID for uniqueness
    })
    
    # Generate initial token to check length
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # If token is shorter than required, add padding data inside the payload
    if len(encoded_jwt) < min_length:
        # Calculate how much padding we need (accounting for base64 encoding)
        # Base64 encoding increases size by ~33%, so we need more bytes
        bytes_needed = int((min_length - len(encoded_jwt)) * 0.75) + 100
        padding_bytes = secrets.token_bytes(bytes_needed)
        padding_str = base64.urlsafe_b64encode(padding_bytes).decode('utf-8')
        
        # Add padding to payload and regenerate token
        to_encode["ext"] = padding_str
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Keep adding padding until we reach minimum length
        iteration = 0
        while len(encoded_jwt) < min_length and iteration < 5:
            additional_bytes = int((min_length - len(encoded_jwt)) * 0.75) + 50
            additional_padding = secrets.token_bytes(additional_bytes)
            additional_str = base64.urlsafe_b64encode(additional_padding).decode('utf-8')
            to_encode[f"ext{iteration}"] = additional_str
            encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            iteration += 1
    
    return encoded_jwt


def create_refresh_token(user_id: int, min_length: int = 1000) -> str:
    """
    Create a refresh token with minimum length requirement.
    Refresh tokens are longer-lived and stored in database.
    Ensures token is at least min_length characters by adding padding data in payload.
    
    Args:
        user_id: ID of the user
        min_length: Minimum token length in characters (default: 1000)
    """
    # Create a token with user_id and expiration
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    token_data = {
        "type": "refresh",
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(64),  # Long JWT ID for uniqueness
    }
    
    # Generate initial token
    encoded_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Add padding if needed
    if len(encoded_token) < min_length:
        bytes_needed = int((min_length - len(encoded_token)) * 0.75) + 100
        padding_bytes = secrets.token_bytes(bytes_needed)
        padding_str = base64.urlsafe_b64encode(padding_bytes).decode('utf-8')
        token_data["pad"] = padding_str
        encoded_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Keep adding padding until we reach minimum length
        iteration = 0
        while len(encoded_token) < min_length and iteration < 5:
            additional_bytes = int((min_length - len(encoded_token)) * 0.75) + 50
            additional_padding = secrets.token_bytes(additional_bytes)
            additional_str = base64.urlsafe_b64encode(additional_padding).decode('utf-8')
            token_data[f"pad{iteration}"] = additional_str
            encoded_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            iteration += 1
    
    return encoded_token


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Remove padding fields if present (ext, ext0, ext1, etc.)
        keys_to_remove = [key for key in payload.keys() if key.startswith("ext")]
        for key in keys_to_remove:
            payload.pop(key, None)
        
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and verify a refresh token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            return None
        
        # Remove padding fields if present (pad, pad0, pad1, etc.)
        keys_to_remove = [key for key in payload.keys() if key.startswith("pad")]
        for key in keys_to_remove:
            payload.pop(key, None)
        
        return payload
    except JWTError:
        return None

