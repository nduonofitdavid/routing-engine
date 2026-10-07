from pathlib import Path
from pydantic import computed_field, PostgresDsn, field_validator, EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Self


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / '.env'

class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file = ENV_FILE,
    env_ignore_empty=True,
    extra="ignore"
  )

  API_V1_STR: str = "/api/v1"
  SECRET_KEY: str 
  ACCESS_TOKEN_EXPIRES_MINUTES: int = 60 * 24 * 8
  FRONTEND_HOST: str = "http://localhost:5173"
  PROJECT_NAME: str
  DATABASE_URL: PostgresDsn
  OPTIMISTIC_SPEED: int
  STANDARD_PRICE: int
  BASE_PRICE: int
  ROUTABLE: str
  ROAD_PENALTY: str
  OSM_DATA_PATH: str | None = None
  STOPS_PATH: str | None = None
  ROUTES_PATH: str | None = None

  @model_validator(mode="after")
  def set_data_paths(self) -> Self:
    data_dir = Path("/tmp/hhiker")
    data_dir.mkdir(parents=True, exist_ok=True)
    if self.OSM_DATA_PATH is None:
      self.OSM_DATA_PATH = str(data_dir / "abuja.osm.pbf")
    if self.STOPS_PATH is None:
      self.STOPS_PATH = str(data_dir / "stops.json")
    if self.ROUTES_PATH is None:
      self.ROUTES_PATH = str(data_dir / "routes.json")
    return self

  @field_validator("DATABASE_URL", mode="before")
  @classmethod
  def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
    database_url = str(value)
    for scheme in ("postgres://", "postgresql://"):
      if database_url.startswith(scheme):
        return database_url.replace(scheme, "postgresql+psycopg://", 1)
    return database_url

  SMTP_TLS: bool = True
  SMTP_SSL: bool = False
  SMTP_PORT: int = 587
  SMTP_HOST: str | None = None
  SMTP_USER: str | None = None
  SMTP_PASSWORD: str | None = None
  EMAILS_FROM_EMAIL: EmailStr | None = None
  EMAILS_FROM_NAME: str | None = None

  @model_validator(mode="after")
  def _set_default_emails_from(self) -> Self:
    if not self.EMAILS_FROM_NAME:
      self.EMAILS_FROM_NAME = self.PROJECT_NAME
    return self

  EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

  @computed_field
  @property
  def emails_enabled(self) -> bool:
    return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)
  
  EMAIL_TEST_USER: EmailStr = "test@example.com"
  FIRST_SUPERUSER: EmailStr
  FIRST_SUPERUSER_PASSWORD: str

settings = Settings() # type: ignore