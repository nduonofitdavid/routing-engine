"""A group of functions for carrying out geometric calculations"""
import math
from app.core.config import settings

# constants
EARTH_RADIUS = 6_371_000

# functions
def haversine(first: tuple[float, float], second: tuple[float, float]) -> float:
  lat1, lon1 = first
  lat2, lon2 = second

  deltalat = math.radians(lat2 - lat1)
  deltalon = math.radians(lon2 - lon1)

  a = (
    (math.sin(deltalat / 2) ** 2) + math.cos(math.radians(lat1))
    *
    math.cos(math.radians(lat2)) * (math.sin(deltalon / 2) ** 2)
  )
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  distance = EARTH_RADIUS * c
  return distance

def bulk_haversine(coords: list[tuple[float, float]])-> float:
  """calculate the haversine distance for a list of coordinates, where each coordinate contains a latitude and a longitude"""
  total: float = 0.0
  for i in range(1, len(coords)):
    first = coords[i-1]
    second = coords[i]
    total += haversine(first, second)
  return total

def time_heuristic(first: tuple[float, float], second: tuple[float, float]):
  distance = haversine(first, second)
  distance_km = distance / 1000
  estimated_hours = distance_km / settings.OPTIMISTIC_SPEED
  estimated_minutes = estimated_hours * 60
  return estimated_minutes
    
def distance_to_time(distance: float, avg_speed: float | None = None) -> float:
  speed = avg_speed if avg_speed is not None else 45
  distance_km = distance / 1000
  hours = distance_km / speed
  return hours * 60

def price_estimator(distance: float) -> int:
  """
  Estimate price based on the distance to be covered
  Does not reflect how real prices are modeled
  """
  distance_copy = distance  
  hundreds_count = 1
    
  while distance_copy >= 100:
    distance_copy-=100
    hundreds_count+=1
  
  trip_price = settings.BASE_PRICE * hundreds_count
  if trip_price < settings.STANDARD_PRICE:
    return settings.STANDARD_PRICE
  return int(trip_price)