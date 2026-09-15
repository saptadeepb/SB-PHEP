"""
data_io.py
==========
Loaders for the *authenticated* public data that parameterise SB-PHEP-II.

Every number used by the model is read from a file in ``data/``; each file
carries a ``source`` column giving the publication the value comes from and an
``accessed`` date.  Nothing is hard-coded in the model itself.  See
``data/DATA_SOURCES.md`` for the full provenance discussion, including which
quantities are measured, which are published aggregates and which are
transparent allocation rules.

Road distances are *derived* unless a published driving distance is supplied.
By default an arc length is the great-circle distance between the two published
node coordinates multiplied by a per-corridor circuity factor, which is fitted to
one reference pair per corridor -- a calibration, not an independent validation,
and individual arcs can deviate substantially from it.  Where a published road
distance is known it is put in the ``road_km`` column of the arcs file and
overrides the derived value; ``DATA_SOURCES.md`` reports how much of each
corridor is published and how much derived.
"""
from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

EARTH_R_KM = 6371.0088


# --------------------------------------------------------------------------- #
#  low-level readers                                                           #
# --------------------------------------------------------------------------- #
def _read_csv(path: str) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_parameters() -> Dict[str, dict]:
    """Technical parameters with value/low/high and provenance."""
    out = {}
    for r in _read_csv(os.path.join(DATA, "parameters.csv")):
        out[r["parameter"]] = {
            "value": float(r["value"]),
            "unit": r["unit"],
            "low": float(r["low"]) if r["low"] else None,
            "high": float(r["high"]) if r["high"] else None,
            "source": r["source"],
            "accessed": r["accessed"],
        }
    return out


def load_energy_regimes() -> Dict[str, dict]:
    """Country energy regimes: electricity price, diesel price, grid CO2."""
    out = {}
    for r in _read_csv(os.path.join(DATA, "energy_regimes.csv")):
        out[r["country"]] = {
            "currency": r["currency"],
            "fx_per_usd": float(r["fx_per_usd"]),
            "elec_price": float(r["elec_price_usd_kwh"]),
            "diesel_price": float(r["diesel_price_usd_l"]),
            "wage": float(r["wage_usd_km"]),
            "wage_source": r["wage_source"],
            "ef_avg": float(r["ef_grid_avg"]),
            "ef_marginal": float(r["ef_grid_marginal"]),
            "ef_clean": float(r["ef_grid_clean"]),
            #  The CDM combined margin is published for India only.  It is not a
            #  scenario of the model -- the tree uses clean, average and marginal --
            #  but it is reported against the emission-neutral threshold, because it
            #  is the convention's own factor for a programme that adds new load and
            #  because omitting it would make the Indian result look like a two-way
            #  choice when the source publishes four factors.
            "ef_combined": (float(r["ef_grid_combined"])
                            if r.get("ef_grid_combined") else None),
            "ef_source": r["ef_source"],
            "price_source": r["price_source"],
            "diesel_source": r["diesel_source"],
            "accessed": r["accessed"],
        }
    return out


def load_ports() -> Dict[str, dict]:
    out = {}
    for r in _read_csv(os.path.join(DATA, "ports.csv")):
        out[r["network"]] = {
            "port": r["port"],
            "country": r["country"],
            "teu_year": r["teu_year"],
            "teu": float(r["teu"]),
            "cargo_mt": float(r["cargo_mt"]) if r["cargo_mt"] else None,
            "transshipment_share": float(r["transshipment_share"]),
            "road_share": float(r["road_share"]),
            "truck_teu_factor": float(r["truck_teu_factor"]),
            "circuity": float(r["circuity"]),
            "circuity_check": r["circuity_check"],
            "source": r["source"],
            "accessed": r["accessed"],
        }
    return out


# --------------------------------------------------------------------------- #
#  geography                                                                   #
# --------------------------------------------------------------------------- #
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


@dataclass
class Network:
    name: str
    port_node: str
    nodes: List[str]
    node_info: Dict[str, dict]
    demand_nodes: List[str]
    edges: List[Tuple[str, str]]           # undirected physical links
    edge_info: Dict[Tuple[str, str], dict]
    arcs: List[Tuple[str, str]]            # directed arcs (both orientations)
    dist: Dict[Tuple[str, str], float]     # km, per directed arc
    edge_of_arc: Dict[Tuple[str, str], Tuple[str, str]]
    electrifiable: List[Tuple[str, str]]   # undirected edges that may be electrified

    @property
    def n_edges(self) -> int:
        return len(self.edges)


def load_network(name: str, circuity: float) -> Network:
    ndir = os.path.join(DATA, "networks")
    nrows = _read_csv(os.path.join(ndir, f"{name}_nodes.csv"))
    arows = _read_csv(os.path.join(ndir, f"{name}_arcs.csv"))

    node_info, nodes, port_node, demand_nodes = {}, [], None, []
    for r in nrows:
        nid = r["node"]
        nodes.append(nid)
        node_info[nid] = {
            "name": r["name"],
            "role": r["role"],
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "demand_weight": float(r["demand_weight"]),
            "exp_share": float(r["exp_share"]),
        }
        if r["role"] == "port":
            port_node = nid
        if r["role"] == "demand":
            demand_nodes.append(nid)
    if port_node is None:
        raise ValueError(f"network {name}: no node with role 'port'")

    edges, edge_info, electrifiable = [], {}, []
    for r in arows:
        e = (r["tail"], r["head"])
        if e[0] not in node_info or e[1] not in node_info:
            raise ValueError(f"network {name}: arc {e} references an unknown node")
        edges.append(e)
        gc = haversine_km(node_info[e[0]]["lat"], node_info[e[0]]["lon"],
                          node_info[e[1]]["lat"], node_info[e[1]]["lon"])
        published = r.get("road_km", "").strip()
        d = float(published) if published else circuity * gc
        edge_info[e] = {"highway": r["highway"], "km": round(d, 2),
                        "great_circle_km": round(gc, 2),
                        "source": "published" if published else "derived",
                        "road_km_source": r.get("road_km_source", ""),
                        "electrifiable": bool(int(r["electrifiable"]))}
        if edge_info[e]["electrifiable"]:
            electrifiable.append(e)

    arcs, dist, edge_of_arc = [], {}, {}
    for e in edges:
        for a in (e, (e[1], e[0])):
            arcs.append(a)
            dist[a] = edge_info[e]["km"]
            edge_of_arc[a] = e

    net = Network(name=name, port_node=port_node, nodes=nodes, node_info=node_info,
                  demand_nodes=demand_nodes, edges=edges, edge_info=edge_info,
                  arcs=arcs, dist=dist, edge_of_arc=edge_of_arc,
                  electrifiable=electrifiable)
    _check_connected(net)
    return net


def _check_connected(net: Network) -> None:
    """Every demand node must be reachable from the port (and back)."""
    adj: Dict[str, set] = {n: set() for n in net.nodes}
    for (i, j) in net.arcs:
        adj[i].add(j)
    seen, stack = {net.port_node}, [net.port_node]
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    missing = [d for d in net.demand_nodes if d not in seen]
    if missing:
        raise ValueError(f"network {net.name}: demand nodes unreachable from port: {missing}")


def available_networks() -> List[str]:
    ndir = os.path.join(DATA, "networks")
    return sorted({f.rsplit("_", 1)[0] for f in os.listdir(ndir) if f.endswith("_nodes.csv")})


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    ports = load_ports()
    for nm in available_networks():
        net = load_network(nm, ports[nm]["circuity"])
        tot = sum(net.edge_info[e]["km"] for e in net.edges)
        print(f"{nm:12s} nodes={len(net.nodes):2d} edges={net.n_edges:2d} "
              f"demand={len(net.demand_nodes):2d} total_km={tot:7.1f}")
        for e in net.edges:
            print(f"    {e[0]:>3s}-{e[1]:<3s} {net.edge_info[e]['highway']:>16s} "
                  f"{net.edge_info[e]['km']:7.1f} km")
