import networkx as nx
import numpy as np

import heapq
import time

R = 6_371_000.0

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  """Return the great-circle distance in metres between two WGS84 points."""
  phi1, phi2 = np.radians(lat1), np.radians(lat2)
  dphi = np.radians(lat2 - lat1)
  dlam = np.radians(lon2 - lon1)
  a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
  return float(2 * R * np.arcsin(np.sqrt(a)))

def populate_edge_length(G: nx.DiGraph) -> None:
  """Write length in-place using vectorized numpy operations"""
  u_arr = np.array([(G.nodes[u]['lat'], G.nodes[u]['lon']) for u, _ in G.edges()])
  v_arr = np.array([(G.nodes[v]['lat'], G.nodes[v]['lon']) for _, v in G.edges()])

  R = 6_371_000.0
  phi1, phi2 = np.radians(u_arr[:, 0]), np.radians(v_arr[:, 0])
  dphi = np.radians(v_arr[:, 0] - u_arr[:, 0])
  dlam = np.radians(v_arr[:, 1] - u_arr[:, 1])
  a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
  lengths = 2 * R * np.arcsin(np.sqrt(a))

  for (u, v), length in zip(G.edges(), lengths):
    G[u][v]["length_m"] = float(length)

def validate_routing_graph(G: nx.DiGraph) -> dict:
  """Returns a dict of validation metrics, raises if graph is heavily fragmented"""
  wcc = list(nx.weakly_connected_components(G))
  largest_wcc = max(wcc, key=len)
  coverage = len(largest_wcc) / G.number_of_nodes()

  dangling = [n for n in G.nodes() if G.degree(n) == 1]
  zero_length = [(u, v) for u, v, d in G.edges(data=True) if d.get("length_m", 1) <= 0]
  missing_highway = [(u, v) for u, v, d in G.edges(data=True) if not d.get("highway")]

  metrics = {
    "total_nodes": G.number_of_nodes(),
    "total_edges": G.number_of_edges(),
    "weakly_connected_components": len(wcc),
    "largest_component_coverage": round(coverage, 4),
    "dangling_nodes": len(dangling),
    "zero_length_edges": len(zero_length),
    "missing_highway_edges": len(missing_highway),
  }

  if coverage < 0.90:
    raise ValueError(
      f"Largest WCC covers only {coverage:.1%} of nodes"
      "graph is heavily fragmented."
    )

  return metrics

def routing_sanity_checks(G: nx.DiGraph) -> None:
  """Ensure structural integrity"""
  assert isinstance(G, nx.DiGraph)

  missing_coords = [n for n in G.nodes() if "lat" not in G.nodes[n]]
  assert not missing_coords, f"{len(missing_coords)} nodes missing coordinates"

  bad_lengths = [(u, v) for u, v, d in G.edges(data=True) if d.get("length_m", 0) <= 0]
  assert not bad_lengths, f"{len(bad_lengths)} edges with non-positive length" 

  loops = list(nx.selfloop_edges(G))
  assert not loops, f"{len(loops)} self-loop edges found"

  wcc = list(nx.weakly_connected_components(G))
  coverage = max(len(c) for c in wcc) / G.number_of_nodes()
  assert coverage >= 0.90, f"Largest WCC only {coverage:.1%} - graph fragmented"

  print("All sanity checks passed.")

def shortest_path(G: nx.DiGraph, start_node: int, stop_node: int, key: str="length_m"):
  """
  Implementation of shortest path algorithm that takes into consideration highway cost without directly
  modifying the distance of each node.
  """
  dist = {start_node: 0.0}
  prev = {}
  visited = set()
  pq = [(0.0, start_node)]

  while pq:
    d, u = heapq.heappop(pq)
    if u in visited:
      continue
    visited.add(u)
    if u == stop_node:
      break
    for v, attrs in G[u].items():
      if v in visited:
        continue
      cost = attrs[key] * attrs.get("road_penalty", 1.0)
      nd = d + cost
      if nd < dist.get(v, float("inf")):
        dist[v] = nd
        prev[v] = u
        heapq.heappush(pq, (nd, v))

  if stop_node not in dist:
    return None, float("inf")
  
  path = [stop_node]
  while path[-1] != start_node:
    path.append(prev[path[-1]])
  path.reverse()

  return path, dist[stop_node]
shortest_end = time.time()

def get_coords_osm(G: nx.DiGraph, path: list[int]) -> list[tuple[float, float]]:
  coords = [
    (G.nodes[node_id]['lat'], G.nodes[node_id]['lon'])
    for node_id in path
  ]
  return coords