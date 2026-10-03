import uuid
import json
from sqlmodel import Session, create_engine, select, SQLModel
from app import crud
from app.core.config import settings
from app.models import *

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)

def add_nodes(session: Session, stop_file: str, route_file: str) -> None: 
  cab = session.exec(select(TransportMode).where(TransportMode.name.ilike("%Car%"))).first()
  if not cab:
    cab = TransportMode(name="Car")
    session.add(cab)
    session.commit()
    session.refresh(cab)

  naija = session.exec(select(Country).where(Country.name.ilike(f"%Nigeria%"))).first()
  abj = session.exec(select(City).where(City.name.ilike(f"%Abuja%"))).first()
  if not naija:
    naija = Country(name="Nigeria")
    session.add(naija)
    session.commit()
    session.refresh(naija)

  if not abj:
    abj = City(name="Abuja", country=naija.id)
    session.add(abj)
    session.commit()
    session.refresh(abj)

  stop_int_to_uuid: dict[int, uuid.UUID] = {}
  with open(stop_file, 'r') as file:
    stops = json.load(file)

  for stop in stops:
    stop_store = Stops(
      name=stop["name"], 
      latitude=stop["latitude"], 
      longitude=stop["longitude"], 
      country=naija.id, 
      city=abj.id
    )
    session.add(stop_store)
    session.commit()
    session.refresh(stop_store)

    stop_int_to_uuid[stop["id"]] = stop_store.id

  with open(route_file, 'r') as file:
    routes = json.load(file)

  for route in routes:
    start_id = stop_int_to_uuid[route["start"]]
    end_id = stop_int_to_uuid[route["end"]]
    session.add(Route(
      start=start_id, 
      end=end_id,
      price=route["price"],
      time=route["time"],
      transport_modes=[cab]
    ))
    if route["bi_directional"]:
      session.add(Route(
        start=end_id,
        end=start_id,
        price=route["price"],
        time=route["time"],
        transport_modes=[cab]
      ))
    session.commit()

def init_db(session: Session) -> None:
  # uncomment if you did not run migration from alembic
  # SQLModel.metadata.create_all(engine)
  # we do this because we make assumptions, since we are using abuja and nigeria data for test, proper initialization later.
  # add_nodes(session=session, stop_file=settings.STOPS_PATH, route_file=settings.ROUTES_PATH)
  user = session.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
  if not user:
    user_in = UserCreate(
      email=settings.FIRST_SUPERUSER,
      password=settings.FIRST_SUPERUSER_PASSWORD,
      is_superuser=True,
    )
    user = crud.create_user(session=session, user_create=user_in)