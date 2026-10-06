import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query, Request
from sqlmodel import select, or_
from sqlalchemy.exc import IntegrityError
from app.api.deps import SessionDep, AdminDep, Depends, get_current_superuser
from app.models import Country, City, StopsIn, Stops, get_datetime_utc, Records, AdminAction, Route, RouteIn, TransportMode, CityBase, TripStore
from app.api.lib.sage_engine import refresh_sage_graph, SG, loader
from app.core.rlimiter import limiter

router = APIRouter(prefix='/admin', tags=['admin', 'admin_user'])

@router.post("/stops/add", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def add_stop(request: Request, session: SessionDep, admin_user: AdminDep, payload: StopsIn):
  """Create a Stop (Bus stop, car park, train station, etc.)"""
  if not loader.check_city(payload.city):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The city provided was not found")
  if not loader.check_country(payload.country):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The country provided was not found")

  try:
    stop = Stops(name=payload.name, latitude=payload.latitude, longitude=payload.longitude, city=city.id, country=country.id)
    record = Records(
      action=AdminAction.CREATED, 
      performed_by=admin_user.id, 
      performed_at=get_datetime_utc(), 
      message=f"created stop for {payload.name} at {city.name}, {country.name}"
    )
    session.add(stop)
    session.add(record)
    session.commit()
  except Exception as e:
    session.rollback()
    logging.exception("Failed to add stop %s", payload.name)
    if isinstance(e, IntegrityError):
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A conflict occured while adding this stop")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sorry, an unexpected error occured")    

  refresh_sage_graph(session=session, loader=loader, graph=SG)
  return stop

@router.get("/routes", dependencies=[Depends(get_current_superuser)])
@limiter.limit("10/minute")
def get_routes(request: Request, session: SessionDep, route_id: uuid.UUID|None = None, start_id: uuid.UUID|None=None, end_id: uuid.UUID|None=None, transport_modes: list[uuid.UUID]|None=None, offset: int=0, limit: int = Query(default=100, le=100)):
  """Get the routes in the database"""
  query = select(Route)
  if route_id:
    query = query.where(Route.id == route_id)
  if start_id:
    query = query.where(Route.start == start_id)
  if end_id:
    query = query.where(Route.end == end_id)
  if transport_modes:
    transport_modes_store = session.exec(select(TransportMode).where(TransportMode.id._in(transport_modes))).all()
    query = query.where(Route.transport_modes.in_(transport_modes_store))
  
  routes = session.exec(query.offset(offset).limit(limit)).all()
  return routes

@router.post("/routes/add", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def add_route(request: Request, session: SessionDep, admin_user: AdminDep, payload: RouteIn):
  """Create a route between two stops"""
  res = session.exec(select(Stops).where(or_(Stops.id == payload.start, Stops.id == payload.end))).all()
  if not len(res) >= 2:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The start stop or end stop was not found!")
  del res

  transport_modes = session.exec(select(TransportMode).where(TransportMode.id.in_(payload.transport_mode))).all()
  if len(transport_modes) != len(payload.transport_mode):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A transport mode provided does not exist!")
  
  try:
    route = Route(start=payload.start, end=payload.end, time=payload.time, price=payload.price, transport_modes=transport_modes)
    record = Records(
      action=AdminAction.CREATED,
      performed_by=admin_user.id,
      performed_at=get_datetime_utc(),
      message=f"created route for {route.start} -> {route.end}"
    )
    session.add(route)
    session.add(record)
    session.commit()
    session.refresh(route)
  except Exception as e:
    session.rollback()
    logging.exception("Failed to add route.")
    if isinstance(e, IntegrityError):
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A conflict occured while adding this route")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sorry, an unexpected error occured")    
  
  refresh_sage_graph(session=session, loader=loader, graph=SG)
  return route

@router.put("/routes/update/{route_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def update_route(request: Request, session: SessionDep, route_id: uuid.UUID, payload: RouteIn, admin_user: AdminDep):
  """Update a route"""
  route = session.exec(select(Route).where(Route.id == route_id)).first()
  transport_modes = session.exec(select(TransportMode).where(TransportMode.id.in_(payload.transport_mode))).all()
  if len(transport_modes) != len(payload.transport_mode):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A transport mode provided does not exist!")
  
  if not route:
    raise HTTPException(detail="The route provided does not exist!", status_code=status.HTTP_404_NOT_FOUND)
  
  route.start = payload.start
  route.end = payload.end
  route.time = payload.time
  route.price = payload.price
  route.transport_mode = transport_modes

  record = Records(
    action=AdminAction.EDITED,
    performed_by=admin_user.id,
    performed_at=get_datetime_utc(),
    message=f"Edit on route {route.id}"
  )
  session.add(route)
  session.add(record)
  session.commit()
  session.refresh(route)

  return route

@router.put("/stops/update/{stop_id}", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def update_stop(request: Request, session: SessionDep, stop_id: uuid.UUID, payload: StopsIn, admin_user: AdminDep):
  """Update a stop"""
  if not loader.check_city(payload.city):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The city provided is invalid!")
  if not loader.check_country(payload.country):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The country provided is invalid!")
  
  stop = session.exec(select(Stops).where(Stops.id == stop_id)).first()
  if not stop:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The stop you tried updating does not exist!")

  stop.name = payload.name
  stop.latitude = payload.latitude
  stop.longitude = payload.longitude
  stop.city = payload.city
  stop.country = payload.country

  record = Records(action=AdminAction.EDITED, performed_by=admin_user.id, performed_at=get_datetime_utc(), message=f"Edited stop {stop.id}")
  session.add(record)
  try:
    session.commit()

  except Exception as e:
    session.rollback()
    logging.exception("Failed to update stop %s", stop_id)
    if isinstance(e, IntegrityError):
      raise HTTPException(status_code=409, detail="A conflict occurred while updating the data!")
    raise HTTPException(status_code=500, detail="An unexpected error occurred while updating the stop.")

  return stop

@router.get("/trips", dependencies=[Depends(get_current_superuser)], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def get_trips_admin(request: Request, session: SessionDep, trip_id: uuid.UUID | None=None, user_id: uuid.UUID|None=None, price: float|None=None, distance: float|None=None, country: uuid.UUID | None=None, city: uuid.UUID | None=None, offset: int=0, limit: int=Query(default=100, le=100)):
  """Get trips for an admin user"""
  query = select(TripStore)
  if trip_id:
    query = query.where(TripStore.id == trip_id)
  if user_id:
    query = query.where(TripStore.user_id == user_id)
  if price:
    query = query.where(TripStore.price == price)
  if distance:
    query = query.where(TripStore.distance == distance)
  if country:
    query = query.where(TripStore.country == country)
  if city:
    query = query.where(TripStore.city == city)
  
  trips = session.exec(query.offset(offset).limit(limit)).all()
  return trips

@router.get("/records", dependencies=[Depends(get_current_superuser)], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def get_records(request: Request, session: SessionDep, record_id: uuid.UUID | None=None, action: AdminAction | None=None, performed_by: uuid.UUID | None=None, performed_at: datetime | None=None, offset: int=0, limit: int=Query(default=100, le=100)):
  """Get records"""
  query = select(Records)
  if record_id:
    query = query.where(Records.id == record_id)
  if action:
    query = query.where(Records.action == action)
  if performed_by:
    query = query.where(Records.performed_by == performed_by)
  if performed_at:
    query = query.where(Records.performed_at == performed_at)
  
  records = session.exec(query.offset(offset).limit(limit)).all()
  return records

@router.post("/country/add/{name}", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def add_country(request: Request, session: SessionDep, admin_user: AdminDep, name: str):
  """Add a country"""
  country = session.exec(select(Country).where(Country.name.ilike(name))).first()
  if country:
    raise HTTPException(detail="The country exists already", status_code=status.HTTP_400_BAD_REQUEST)
  
  country = Country(name=name)
  record = Records(action=AdminAction.CREATED, performed_by=admin_user.id, performed_at=get_datetime_utc(), message=f"Created country {name}")
  session.add(country)
  session.add(record)
  session.commit()
  session.refresh(country)

  refresh_sage_graph(session=session, loader=loader, graph=SG)
  return country

@router.post("/city/add/", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def add_city(request: Request, session: SessionDep, admin_user: AdminDep, payload: CityBase):
  """Add a city"""
  if not loader.check_country(payload.country):
    raise HTTPException(detail="The country provided is not valid!", status_code=status.HTTP_400_BAD_REQUEST)
  
  city = City(name=payload.name, country=payload.country)
  record = Records(action=AdminAction.CREATED, performed_by=admin_user.id, performed_at=get_datetime_utc(), message=f"Created city {payload.name}")
  session.add(city)
  session.add(record)
  session.commit()
  session.refresh(city)

  refresh_sage_graph(session=session, loader=loader, graph=SG)
  return city