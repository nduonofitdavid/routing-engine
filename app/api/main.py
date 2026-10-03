from fastapi import APIRouter

from .router import trip, user, auth, ye, admin

api_router = APIRouter()
api_router.include_router(ye.router)
api_router.include_router(trip.router)
api_router.include_router(user.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
