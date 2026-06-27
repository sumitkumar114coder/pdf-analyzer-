import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from backend.database import get_db
from backend.models import User, HistoryLog

# JWT Configurations
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "ai-research-assistant-super-secret-key-998877")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REMEMBER_ME_EXPIRE_DAYS = 30

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Password Hashing Helpers
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# Token Generation Helper
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependency to verify token and return user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Pydantic Schemas
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = False

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    gemini_api_key: Optional[str] = None

# Routes
@router.post("/signup")
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # Check if username or email already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username is already taken.")
        
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log action
    log = HistoryLog(
        user_id=new_user.id,
        action_type="auth",
        description=f"Created user account: {new_user.username}"
    )
    db.add(log)
    db.commit()

    return {"message": "Account created successfully. Please log in."}

@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password.")

    # Expiration delta based on Remember Me option
    if user_data.remember_me:
        expires = timedelta(days=REMEMBER_ME_EXPIRE_DAYS)
    else:
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    access_token = create_access_token(data={"sub": user.username}, expires_delta=expires)

    # Log action
    log = HistoryLog(
        user_id=user.id,
        action_type="auth",
        description="Logged into account"
    )
    db.add(log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "email": user.email
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "profile_picture": current_user.profile_picture,
        "has_custom_key": current_user.gemini_api_key is not None and len(current_user.gemini_api_key) > 0,
        "gemini_api_key": current_user.gemini_api_key or ""
    }

@router.put("/profile")
def update_profile(profile_data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if profile_data.username and profile_data.username != current_user.username:
        existing = db.query(User).filter(User.username == profile_data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username is already taken.")
        current_user.username = profile_data.username

    if profile_data.email and profile_data.email != current_user.email:
        existing = db.query(User).filter(User.email == profile_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already in use.")
        current_user.email = profile_data.email

    if profile_data.password:
        current_user.hashed_password = hash_password(profile_data.password)

    if profile_data.gemini_api_key is not None:
        current_user.gemini_api_key = profile_data.gemini_api_key.strip()

    db.commit()
    db.refresh(current_user)

    # Log action
    log = HistoryLog(
        user_id=current_user.id,
        action_type="auth",
        description="Updated profile settings"
    )
    db.add(log)
    db.commit()

    return {
        "message": "Profile updated successfully.",
        "username": current_user.username,
        "email": current_user.email,
        "has_custom_key": current_user.gemini_api_key is not None and len(current_user.gemini_api_key) > 0
    }
