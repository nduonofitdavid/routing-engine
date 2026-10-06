import uuid
from fastapi import APIRouter, Depends, status, Query

from app.api.deps import SessionDep, get_current_user
from app.models import Place

router = APIRouter(prefix='/places', tags=['places', 'closest'])

@router.get("/", dependencies=[Depends(get_current_user)])
def get_places(session: SessionDep, place_id: uuid.UUID | None=None, name: str | None=None, offset: int=0, limit: int=Query(default=100, le=100)):
  ...