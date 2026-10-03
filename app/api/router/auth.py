from datetime import timedelta

from typing import Annotated, Any

from fastapi import APIRouter, status, HTTPException, Depends
from app.api.deps import SessionDep, CurrentUser, get_current_superuser
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core import security

from app.models import User, Token, UserPublic, Message, UserUpdate, NewPassword
from app import crud
from app.utils import generate_password_reset_token, generate_reset_password_email, send_email, verify_password_reset_token

router = APIRouter(prefix="/auth", tags=["auth", "authentication"])

@router.post('/login/access-token')
async def login_user(session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
  user = crud.authenticate(session=session, email=form_data.username, password=form_data.password)
  if not user:
    raise HTTPException(status_code=400, detail="Incorrect email or password")
  elif not user.is_active:
    raise HTTPException(status_code=400, detail="Inactive user")
  
  access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES)
  return Token(access_token=security.create_access_token(user.id, expires_delta=access_token_expires))

@router.post("/login/test-token", response_model=UserPublic)
async def test_token(current_user: CurrentUser) -> Any:
  return current_user

@router.post("/password-recovery/{email}")
async def recover_password(email: str, session: SessionDep) -> Message:
  user = crud.get_user_by_email(session=session, email=email)

  if user:
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(email_to=user.email, email=email, token=password_reset_token)
    send_email(email_to=user.email, subject=email_data.html_content,)

  return Message(message="If you registered with an email, a recovery link has been set")

@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
  """Reset password"""
  email = verify_password_reset_token(token=body.token)
  if not email:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
  
  user = crud.get_user_by_email(session=session, email=email)
  if not user:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
  elif not user.is_active:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
  
  user_in_update = UserUpdate(password=body.new_password)
  crud.update_user(session=session, db_user=user, user_in=user_in_update)
  return Message(message="Password updated successfully")

@router.post("/password-recovery-html-content/{email}", dependencies=[Depends(get_current_superuser)], response_class=HTMLResponse)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
  user = crud.get_user_by_email(session=session, email=email)
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user with the username provided exists in the system.")

  password_reset_token = generate_password_reset_token(email=email)
  email_data = generate_reset_password_email(email_to=user.email, email=email, token=password_reset_token)
  return HTMLResponse(content=email_data.html_content, headers={"subject:": email_data.subject})