"""Authentication routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, Token
from app.utils.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Extract the current user from a session cookie or Authorization header."""
    from app.utils.security import decode_token
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        return None
    try:
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception as e:
        logger.warning(f"Error resolving current user: {e}")
        return None


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that requires an authenticated user, redirects otherwise."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── API endpoints ─────────────────────────────────────────────────────────────

@router.post("/register")
async def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New user registered: {user.username}")
    return {"success": True, "message": "Account created successfully"}


@router.post("/login")
async def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate and return a JWT token and set the session cookie."""
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=False,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        path="/",
    )
    return {"success": True, "access_token": token, "username": user.username}


@router.get("/logout")
@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie."""
    res = RedirectResponse(url="/login", status_code=303)
    res.delete_cookie("access_token", path="/")
    return res
