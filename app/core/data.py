import os
from pathlib import Path
import httpx

from app.core.config import Settings

SUPABASE_URL = os.getenv("SUPABASE_URL", None)
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", None)
BUCKET_STR = os.getenv("BUCKET_STR", None)

if not all([SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, BUCKET_STR]):
  raise Exception("Incomplete credentials!")

async def download_from_supabase(bucket: str, remote_path: str, local_path: str,) -> None:
  url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{remote_path}"
  headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",}
  destination = Path(local_path)
  temporary = destination.with_suffix(destination.suffix + ".tmp")
  destination.parent.mkdir(parents=True, exist_ok=True)

  async with httpx.AsyncClient() as client:
    async with client.stream("GET", url, headers=headers,) as response:
      response.raise_for_status()
      with temporary.open("wb") as file:
        async for chunk in response.aiter_bytes():
          file.write(chunk)

  temporary.replace(destination)

async def ensure_data_files(settings: Settings):
  if not Path(settings.OSM_DATA_PATH).exists():
    await download_from_supabase(bucket=BUCKET_STR, remote_path="abuja.osm.pbf", local_path=settings.OSM_DATA_PATH,)
  if not Path(settings.STOPS_PATH).exists():
    await download_from_supabase(bucket=BUCKET_STR, remote_path="stops.json", local_path=settings.STOPS_PATH,)
  if not Path(settings.ROUTES_PATH).exists():
    await download_from_supabase(bucket=BUCKET_STR, remote_path="routes.json", local_path=settings.ROUTES_PATH,)