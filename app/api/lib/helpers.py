from dataclasses import dataclass
from fastapi import status, HTTPException
from app.models import RouteBlock, RouteTripOut, CachedStop, CoordTStopOut
from app.api.lib.osm_engine import snap_and_traverse
from app.api.lib.sage_lib import price_estimator, distance_to_time

def coord_to_stop(ac_start: tuple[float, float], kn_stop: CachedStop, route_index: int=1) -> CoordTStopOut:
  """Check if a path exists between a coordinate and a stop"""
  res = snap_and_traverse(start_coord=ac_start, stop_coord=kn_stop.get_coords())
  if res:
    path, dist = res
    price = price_estimator(dist)
    time = distance_to_time(dist)
    route = RouteTripOut(time=time, price=price, transport_modes=['Car'])
    route_block = RouteBlock(route_position=route_index, start_node=None, stop_node=None, route=route, route_geometry=path)
    return CoordTStopOut(rb=route_block, dist=dist)
  
  raise HTTPException(detail="Sorry, no route through stops found!", status_code=status.HTTP_404_NOT_FOUND)
