from sqlmodel import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from collections.abc import Generator
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from app.core.db import engine
from app.core.config import settings
from app.core.security import ALGORITHM

from app.models import TokenPayload, User

reuasable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")

def get_db() -> Generator[Session]:
  with Session(engine) as session:
    yield session

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reuasable_oauth2)]

def get_current_user(session: SessionDep, token: TokenDep):
  try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    token_data = TokenPayload(**payload)
  except (InvalidTokenError, ValidationError):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")

  user = session.get(User, token_data.sub)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  if not user.is_active:
    raise HTTPException(status_code=400, detail="Inactive user")
  return user

CurrentUser = Annotated[User, Depends(get_current_user)]

def get_current_superuser(current_user: CurrentUser) -> User:
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="The user doesn't have enough priviledge")
  return current_user

AdminDep = Annotated[User, Depends(get_current_superuser)]