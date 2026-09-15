"""
figures_osm.py
==============
The study-area figure on an OpenStreetMap or CartoDB raster base.

Why this is a separate module
-----------------------------
``figures.fig_study_areas`` draws the four corridors on the GSHHS shoreline and
the WDB political and river lines that ship with Basemap.  That base is
reproducible offline: it is part of the replication package's dependencies, it
needs no network, and it will look the same in ten years.  A raster tile base
does not have those properties --- it needs a live tile server, the tiles change
under you, and some providers now require an API key --- so it is offered here as
an alternative rather than as the default.

Run it where the tile servers are reachable::

    python3 -m src.figures_osm                    # OpenStreetMap Standard
    python3 -m src.figures_osm --source carto     # CartoDB Positron (API key)
    python3 -m src.figures_osm --out paper/figures/fig_study_areas.pdf

The panels, the projection, the label placement, the leader lines, the scale
bars and the layout audit are the same code as the offline figure: only the base
changes.  Attribution is drawn into the figure, as both providers require.

Tile-usage note
---------------
The OpenStreetMap Foundation's tile usage policy allows occasional, low-volume
use of its standard tiles and requires the credit line this module draws.  A few
dozen tiles for one figure is within it; a sweep over many corridors is not, and
should use a commercial provider or a local tile server.  CartoDB basemaps
require an API key, which contextily expects in the provider object.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from . import figures as F
from .data_io import load_network, load_ports

WEB_MERCATOR_R = 6378137.0

SOURCES = {
    "osm": ("OpenStreetMap.Mapnik",
            "Base map © OpenStreetMap contributors, ODbL."),
    "carto": ("CartoDB.PositronNoLabels",
              "Base map © OpenStreetMap contributors, © CARTO."),
    "carto-labels": ("CartoDB.Positron",
                     "Base map © OpenStreetMap contributors, © CARTO."),
}


def _to_mercator(lon, lat):
    x = math.radians(lon) * WEB_MERCATOR_R
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * WEB_MERCATOR_R
    return x, y


def _provider(name: str):
    import xyzservices.providers as P
    obj = P
    for part in SOURCES[name][0].split("."):
        obj = obj[part] if isinstance(obj, dict) else getattr(obj, part)
    return obj


def fig_study_areas_osm(networks=("vizag", "sanantonio", "manzanillo", "rotterdam"),
                        source: str = "osm", out: str | None = None,
                        zoom: str | int = "auto") -> str:
    """The four corridors over raster tiles, otherwise identical to the offline figure."""
    import contextily as cx

    ports = load_ports()
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.0))
    fig.subplots_adjust(left=0.045, right=0.985, top=0.955, bottom=0.105,
                        wspace=0.16, hspace=0.24)

    for ax, nm in zip(axes.ravel(), networks):
        net = load_network(nm, ports[nm]["circuity"])
        lons = [i["lon"] for i in net.node_info.values()]
        lats = [i["lat"] for i in net.node_info.values()]
        w, e, s_, n = F._panel_bbox(lons, lats)
        x0, y0 = _to_mercator(w, s_)
        x1, y1 = _to_mercator(e, n)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")

        cx.add_basemap(ax, source=_provider(source), zoom=zoom, attribution=False,
                       interpolation="bilinear")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(visible=False)

        xy = {k: _to_mercator(i["lon"], i["lat"]) for k, i in net.node_info.items()}
        for edge in net.edges:
            a, b = xy[edge[0]], xy[edge[1]]
            ax.plot([a[0], b[0]], [a[1], b[1]], "-",
                    color=F.CAT[0] if net.edge_info[edge]["electrifiable"] else "#6f6f6f",
                    linewidth=1.9, zorder=4, solid_capstyle="round",
                    path_effects=None, gid=F.OVERLAP_OK)
        for k, info in net.node_info.items():
            role = info["role"]
            ax.scatter(*xy[k], s=54 if role == "port" else 26,
                       marker="s" if role == "port" else ("^" if role == "junction" else "o"),
                       color=F.CAT[1] if role == "port" else
                       (F.INK2 if role == "junction" else F.CAT[2]),
                       zorder=6, edgecolor="white", linewidth=0.7)
        ax.set_title(f"{ports[nm]['port']} ({ports[nm]['country']})", fontsize=9)

        #  scale bar: a plain bar in Mercator metres, corrected for latitude
        span_m = (x1 - x0) * math.cos(math.radians((s_ + n) / 2))
        step_km = next((v for v in (25, 50, 100, 200, 400, 800)
                        if v >= span_m / 1000 / 4), 800)
        bar_m = step_km * 1000 / math.cos(math.radians((s_ + n) / 2))
        bx, by = x0 + (x1 - x0) * 0.06, y0 + (y1 - y0) * 0.06
        ax.plot([bx, bx + bar_m], [by, by], "-", color=F.INK, linewidth=2.4,
                solid_capstyle="butt", zorder=8, gid=F.OVERLAP_OK)
        ax.text(bx + bar_m / 2, by + (y1 - y0) * 0.012, f"{step_km} km",
                ha="center", va="bottom", fontsize=5.8, color=F.INK,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8),
                zorder=8)

        r = F._renderer(fig)
        obstacles = [t.get_window_extent(r) for t in ax.texts if t.get_text().strip()]
        marks = [F._point_box(ax, *xy[k], 5.5) for k in net.node_info]
        obstacles += marks
        rank = {"port": 0, "demand": 1, "junction": 2}
        for k, info in sorted(net.node_info.items(),
                              key=lambda kv: rank.get(kv[1]["role"], 1)):
            name = info["name"]
            if info["role"] == "junction":
                import re
                name = re.sub(r"\s+junction$", "", name, flags=re.I)
            txt = textwrap.fill(name, 15) if len(name) > 17 else name
            fs = {"port": 5.9, "demand": 5.5}.get(info["role"], 5.0)
            rch = ((14.0, 20.0, 28.0, 36.0, 45.0) if info["role"] == "port"
                   else (5.0, 9.0, 14.0, 20.0, 27.0, 35.0, 45.0))
            F._place_label(ax, xy[k], txt, obstacles, r, fs,
                           F.INK if info["role"] != "junction" else F.INK2,
                           bbox=dict(boxstyle="round,pad=0.12", fc="white",
                                     ec="none", alpha=0.85),
                           zorder=9, reach=rch, leader=True, hard=marks,
                           require_owner=(info["role"] == "junction"),
                           max_overlap=0.02 if info["role"] == "junction" else None,
                           others=[ax.transData.transform(xy[o]) for o in net.node_info
                                   if o != k])
        for edge in net.edges:
            a, b = xy[edge[0]], xy[edge[1]]
            for f in (0.5, 0.38, 0.62, 0.28, 0.72):
                mid = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
                before = len(obstacles)
                t = F._place_label(ax, mid, f"{net.edge_info[edge]['km']:.0f}",
                                   obstacles, r, 5.4, F.INK2,
                                   bbox=dict(boxstyle="round,pad=0.10", fc="white",
                                             ec="none", alpha=0.9),
                                   zorder=8, reach=(0.0, 5.0, 9.0))
                bb = obstacles[-1]
                if not any(F._inter_area(bb, o) / max(1e-9, bb.width * bb.height) > 0.05
                           for o in obstacles[:before]):
                    break
                t.remove()
                obstacles.pop()

    handles = [Line2D([], [], marker="s", color="none", markerfacecolor=F.CAT[1],
                      markersize=7, label="port"),
               Line2D([], [], marker="^", color="none", markerfacecolor=F.INK2,
                      markersize=7, label="junction"),
               Line2D([], [], marker="o", color="none", markerfacecolor=F.CAT[2],
                      markersize=7, label="hinterland demand node"),
               Line2D([], [], color=F.CAT[0], linewidth=1.8,
                      label="electrifiable corridor link"),
               Line2D([], [], color="#6f6f6f", linewidth=1.8,
                      label="link not electrifiable")]
    fig.legend(handles=handles, frameon=False, ncol=5, loc="lower center",
               bbox_to_anchor=(0.5, 0.028), fontsize=7.4, columnspacing=1.2)
    fig.text(0.5, 0.004, "Numbers on the links are road kilometres. "
             + SOURCES[source][1], ha="center", va="bottom", fontsize=6.4,
             color=F.INK2)

    out = out or os.path.join(F.FIG, "fig_study_areas.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    problems = F.audit_figure(fig, os.path.basename(out))
    if problems:
        print("layout audit findings:\n  - " + "\n  - ".join(problems))
    fig.savefig(out)
    fig.savefig(out.replace(".pdf", ".png"))
    plt.close(fig)
    print(f"wrote {out}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[3])
    ap.add_argument("--source", default="osm", choices=sorted(SOURCES),
                    help="tile provider (default: OpenStreetMap Standard)")
    ap.add_argument("--out", default=None, help="output .pdf path")
    ap.add_argument("--zoom", default="auto",
                    help="tile zoom level, or 'auto' (default)")
    a = ap.parse_args(argv)
    zoom = a.zoom if a.zoom == "auto" else int(a.zoom)
    try:
        import contextily  # noqa: F401
    except ImportError:
        print("contextily is not installed:  pip install contextily", file=sys.stderr)
        return 2
    try:
        fig_study_areas_osm(source=a.source, out=a.out, zoom=zoom)
    except Exception as exc:                      # network, key or provider error
        print(f"could not draw the tile-based figure: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        print("The offline figure in src/figures.py needs no network and is what "
              "the manuscript uses.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
