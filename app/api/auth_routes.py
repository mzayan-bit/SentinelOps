import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import UserModel, SessionModel
from config.settings import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # Update last login
    user.last_login = datetime.utcnow()
    
    # Create session
    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(str(session_id))
    
    db_session = SessionModel(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=get_password_hash(refresh_token),
        device_info=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    db.add(db_session)
    await db.commit()
    
    access_token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id) if user.org_id else None)
    
    # Set HttpOnly cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, # Should be True in prod
        samesite="lax",
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
        
    payload = verify_token(refresh_token, "refresh")
    session_id = payload.get("sub")
    
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    db_session = result.scalar_one_or_none()
    
    if not db_session or db_session.is_revoked or not verify_password(refresh_token, db_session.refresh_token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
        
    result_user = await db.execute(select(UserModel).where(UserModel.id == db_session.user_id))
    user = result_user.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        
    access_token = create_access_token(user_id=str(user.id), role=user.role.value, org_id=str(user.org_id) if user.org_id else None)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = verify_token(refresh_token, "refresh")
            session_id = payload.get("sub")
            result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
            db_session = result.scalar_one_or_none()
            if db_session:
                db_session.is_revoked = True
                await db.commit()
        except Exception:
            pass # Ignore token validation errors during logout
            
    response.delete_cookie(key="refresh_token")
    return {"detail": "Successfully logged out"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # This is just a bootstrap endpoint for the first admin, 
    # typically this would be disabled in an enterprise platform
    result = await db.execute(select(UserModel).where(UserModel.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    new_user = UserModel(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=Role.SUPER_ADMIN
    )
    db.add(new_user)
    await db.commit()
    return {"detail": "User created successfully"}

import pyotp

class Verify2FARequest(BaseModel):
    code: str

@router.post("/2fa/setup")
async def setup_2fa(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA already enabled")
        
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="SentinelOps")
    
    user.mfa_secret = secret
    await db.commit()
    
    return {"secret": secret, "provisioning_uri": provisioning_uri}

@router.post("/2fa/verify")
async def verify_2fa(
    req: Verify2FARequest,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not setup")
        
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(req.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
        
    user.mfa_enabled = True
    await db.commit()
    return {"detail": "2FA successfully enabled"}

class PasswordResetRequest(BaseModel):
    email: EmailStr

@router.post("/password-reset")
async def password_reset(req: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == req.email))
    user = result.scalar_one_or_none()
    
    if user:
        # In a real enterprise system, send an email with a secure token.
        # We are mocking the email sending here.
        reset_token = create_access_token(user_id=str(user.id), role=user.role.value)
        # TODO: send_email(user.email, f"Click to reset: /reset?token={reset_token}")
        
    # Always return success to prevent email enumeration attacks
    return {"detail": "If that email exists, a password reset link has been sent."}
