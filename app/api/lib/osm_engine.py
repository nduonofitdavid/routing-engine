import ast
import time

import osmium
from osmium import osm
import networkx as nx
from app.core.config import settings

import numpy as np
from shapely.geometry import Point
from shapely import STRtree

import folium

from app.api.lib.osm_lib import populate_edge_length, routing_sanity_checks, validate_routing_graph, shortest_path, get_coords_osm

ROAD_PENALTY = ast.literal_eval(settings.ROAD_PENALTY)
ROUTABLE = ast.literal_eval(settings.ROUTABLE)

class DirectedGraphBuilder(osmium.SimpleHandler):
  """parse a pbf file and build a directed graph"""

  def __init__(self, routable: set, road_penalty: dict[str, float]) -> None:
    super().__init__()
    self.graph: nx.DiGraph = nx.DiGraph()
    self.ROUTABLE: set = routable
    self.ROAD_PENALTY: dict[str, float] = road_penalty

  def way(self, w: osm.Way) -> None:
    if w.tags.get("highway") not in self.ROUTABLE:
      return

    node_refs: list[int] = []
    for nd in w.nodes:
      if not nd.location.valid():
        return
      self.graph.add_node(nd.ref, lat=nd.location.lat, lon=nd.location.lon)
      node_refs.append(nd.ref)

    if len(node_refs) < 2:
      return

    self._add_edges(w, node_refs)

  def _add_edges(self, w: osm.Way, node_refs: list[int])-> None:
    oneway = w.tags.get("oneway", "no").lower()
    is_roundabout = w.tags.get("junction", "").lower() == "roundabout"
    forward_only = oneway in {"yes", "true", "1"} or is_roundabout
    backward_only = oneway in {"-1", "reverse"}
    highway = w.tags.get("highway")

    attrs = {
      "highway": highway,
      "maxspeed": w.tags.get("maxspeed"),
      "name": w.tags.get("name", ""),
      "surface": w.tags.get("surface", ""),
      "road_penalty": self.ROAD_PENALTY[highway] if highway else 1.0,
      "length_m": 0.0
    }

    pairs = list(zip(node_refs, node_refs[1:]))
    if backward_only:
      pairs = [(v, u) for u, v in pairs]

    for u, v in pairs:
      if not self.graph.has_edge(u, v):
        self.graph.add_edge(u, v, **attrs)

    if not forward_only and not backward_only:
      for u, v in list(zip(node_refs, node_refs[1:])):
        if not self.graph.has_edge(u, v):
          self.graph.add_edge(v, u, **attrs)

  def build(self, pbf_path: str) -> nx.DiGraph:
    self.apply_file(pbf_path, locations=True)
    return self.graph

builder = DirectedGraphBuilder(routable=ROUTABLE, road_penalty=ROAD_PENALTY)
G = builder.build(settings.OSM_DATA_PATH)

populate_edge_length(G)

# snap the graph
snap_start = time.time()
node_ids = np.array(list(G.nodes()))
coords = np.array([(G.nodes[n]["lon"], G.nodes[n]['lat']) for n in node_ids])
tree = STRtree([Point(x, y) for x, y in coords])
snap_end = time.time()

def snap_to_graph(lon: float, lat: float) -> int:
  idx = tree.nearest(Point(lon, lat))
  return int(node_ids[idx])

def snap_and_traverse(start_coord: tuple[float, float], stop_coord: tuple[float, float]):
  start_node = snap_to_graph(start_coord[1], start_coord[0])
  stop_node = snap_to_graph(stop_coord[1], stop_coord[0])

  path, dist = shortest_path(G, start_node=start_node, stop_node=stop_node)
  if path:
    coords = get_coords_osm(G, path)
    return coords, dist
  return None

if __name__ == "__main__":
  report = validate_routing_graph(G)
  for k, v in report.items():
    print(f" {k}: {v}")
  
  routing_sanity_checks(G)
  print("snap: ", snap_end - snap_start)

  test_coord = 9.139035, 7.305419
  print(snap_to_graph(test_coord[1], test_coord[0]))
  start_l = 9.025069, 7.475762 
  stop_l =  9.029266, 7.469132 
  start_node = snap_to_graph(start_l[1], start_l[0])
  stop_node = snap_to_graph(stop_l[1], stop_l[0])

  path, dist = shortest_path(G, start_node=start_node, stop_node=stop_node)
  if path:
    coords = get_coords_osm(G, path)

    map = folium.Map(
      location=coords[0],
      zoom_start=11
    )

    folium.PolyLine(coords, tooltip="coast").add_to(map)
    map.save("try.html")