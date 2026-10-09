"""
figures.py
==========
All manuscript figures, rendered from the CSV files that ``experiments.py``
writes, so that no figure can drift away from the numbers in the tables.

Style notes
-----------
Colour is assigned by the job it does: identity (instrument family, country,
method) uses a fixed categorical order, never a cycled one, and every series
also carries a distinct marker and line style so the figures survive greyscale
printing and colour-vision deficiency.  Axes and grids are recessive; no chart
uses two y-scales.

Layout is checked, not eyeballed
--------------------------------
Every figure passes through :func:`audit_figure` before it is written.  The
audit measures each piece of text with the renderer and rejects the figure if
two labels overlap, if a label placed in data coordinates falls outside its
axes, or if a legend sits on top of the data it is labelling.  Labels that have
to be positioned by hand -- the schematic's boxes, the map panels' place names
-- are therefore fitted and placed by the measuring helpers below rather than
by guessed offsets, and a layout regression becomes a build failure instead of
something a reader notices first.  :func:`make_all` writes the audit verdict to
``outputs/figures/FIGURE_AUDIT.txt``, which ``check_manuscript.py`` reads.
"""
from __future__ import annotations

import csv
import math
import os
import re
import textwrap
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import MaxNLocator, NullFormatter
from matplotlib.transforms import Bbox
from .corridors import NETWORKS, COUNTRIES, FOCAL

TAB = "outputs/tables"
FIG = "outputs/figures"

#  Validated categorical order (blue, orange, aqua, yellow, magenta, green,
#  violet, red).  Slots are used in order and never cycled.
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
       "#008300", "#4a3aa7", "#e34948"]
MARK = ["o", "s", "^", "D", "v", "P", "X", "*"]
DASH = ["-", "--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (1, 1)), "-"]
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#d9d8d3"

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9.5,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "axes.edgecolor": INK2, "axes.linewidth": 0.7,
    "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.labelcolor": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.axisbelow": True, "figure.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    #  embed TrueType outlines (Type 42) rather than Type 3 bitmaps, as publishers ask
    "pdf.fonttype": 42, "ps.fonttype": 42,
})

#  Names as they are drawn on the map.  The data keep the full name; a panel
#  260 km across cannot carry a two-line name for a node 20 km from the port
#  without putting it beside its neighbour, and the shorter form is the one a
#  reader of the map needs.
MAP_NAME = {
    "Uiwang ICD (Seoul)": "Uiwang (Seoul)",
    "Johannesburg City Deep": "Johannesburg",
    "Dubai Industrial City": "Dubai Ind. City",
    "Abu Dhabi Mussafah": "Abu Dhabi",
    "Commerce I-710/I-5": "Commerce",
    "Durban Container Terminal": "Durban",
    "Shanghai Waigaoqiao": "Waigaoqiao",
    "Port of Los Angeles": "Port of LA",
    "Gadeok (New Port)": "Gadeok",
}

FAMILY_LABEL = {
    "F0": "F0 no charge",
    "F1": "F1 flat per-km toll",
    "F2": "F2 toll waived when platooning",
    "F3": "F3 platoon-discounted, state-blind",
    "F4": "F4 platoon-discounted, state-contingent",
    "FB": "first best (centralised)",
    "centralized (first best)": "first best (centralised)",
}

#  gid markers that tell the audit a text is deliberately outside its axes
OUTSIDE_OK = "audit:outside-ok"
OVERLAP_OK = "audit:overlap-ok"

_AUDIT: List[str] = []          # one line per figure, filled by _save


class FigureDefect(RuntimeError):
    pass


def _read(name: str) -> List[dict]:
    path = os.path.join(TAB, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _f(v, default=math.nan) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# =========================================================================== #
#  measurement helpers                                                        #
# =========================================================================== #
def _renderer(fig):
    fig.canvas.draw()
    return fig.canvas.get_renderer()


def _inter_area(a: Bbox, b: Bbox) -> float:
    dx = min(a.x1, b.x1) - max(a.x0, b.x0)
    dy = min(a.y1, b.y1) - max(a.y0, b.y0)
    if dx <= 0 or dy <= 0:
        return 0.0
    return dx * dy


def _outside_area(inner: Bbox, outer: Bbox) -> float:
    return max(0.0, inner.width * inner.height - _inter_area(inner, outer))


def _ppu(ax) -> Tuple[float, float]:
    """Display pixels per data unit, in x and y."""
    p0 = ax.transData.transform((0.0, 0.0))
    p1 = ax.transData.transform((1.0, 1.0))
    return abs(p1[0] - p0[0]), abs(p1[1] - p0[1])


def _drawn_ticklabels(ax, which: str) -> List:
    """The tick labels that are actually drawn.

    A locator keeps tick objects for positions outside the current view and
    matplotlib simply does not draw them; their ``Text`` objects still report a
    position, and measuring those would make the audit complain about labels no
    reader will ever see.
    """
    axis = ax.xaxis if which == "x" else ax.yaxis
    lo, hi = ax.get_xlim() if which == "x" else ax.get_ylim()
    lo, hi = min(lo, hi), max(lo, hi)
    span = hi - lo
    out = []
    for tick in axis.get_major_ticks():
        lab = tick.label1
        if not lab.get_visible() or not str(lab.get_text()).strip():
            continue
        if lo - 1e-6 * span <= tick.get_loc() <= hi + 1e-6 * span:
            out.append(lab)
    return out


def _text_items(fig):
    """Every visible, non-empty text, paired with the axes that owns it."""
    items = []
    for t in fig.texts:
        items.append((None, t))
    for lg in getattr(fig, "legends", []):
        items.extend((None, t) for t in lg.get_texts())
    for ax in fig.axes:
        items.extend((ax, t) for t in ax.texts)
        items.append((ax, ax.title))
        if ax.axison:
            items.append((ax, ax.xaxis.label))
            items.append((ax, ax.yaxis.label))
            items.extend((ax, t) for t in _drawn_ticklabels(ax, "x"))
            items.extend((ax, t) for t in _drawn_ticklabels(ax, "y"))
        lg = ax.get_legend()
        if lg is not None:
            items.extend((ax, t) for t in lg.get_texts())
    return [(a, t) for a, t in items
            if t.get_visible() and str(t.get_text()).strip()]


def audit_figure(fig, name: str = "figure", overlap_frac: float = 0.02) -> List[str]:
    """Report overlapping labels, labels outside their axes, and legends on data.

    The tolerance is small on purpose: at this type size two labels that share
    even a few per cent of their area read as one, so anything past a couple of
    per cent is a finding.
    """
    r = _renderer(fig)
    problems: List[str] = []

    items = []
    for ax, t in _text_items(fig):
        try:
            bb = t.get_window_extent(r)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        items.append((ax, t, bb))

    #  1. text-text overlap
    for i in range(len(items)):
        ax_i, t_i, bb_i = items[i]
        for j in range(i + 1, len(items)):
            ax_j, t_j, bb_j = items[j]
            if OVERLAP_OK in (t_i.get_gid() or "", t_j.get_gid() or ""):
                continue
            inter = _inter_area(bb_i, bb_j)
            if inter <= 0:
                continue
            smaller = min(bb_i.width * bb_i.height, bb_j.width * bb_j.height)
            if smaller > 0 and inter / smaller > overlap_frac:
                problems.append(
                    f"{name}: labels overlap "
                    f"{_short(t_i)!r} / {_short(t_j)!r} "
                    f"({100 * inter / smaller:.0f}% of the smaller)")

    #  2. data-coordinate text outside its axes
    for ax, t, bb in items:
        if ax is None or t.get_gid() == OUTSIDE_OK:
            continue
        if t in (ax.title, ax.xaxis.label, ax.yaxis.label):
            continue
        if t in _drawn_ticklabels(ax, "x") or t in _drawn_ticklabels(ax, "y"):
            continue
        lg = ax.get_legend()
        if lg is not None and t in lg.get_texts():
            continue
        if not _uses_data(ax, t):
            continue
        out = _outside_area(bb, ax.get_window_extent(r))
        if out / max(1e-9, bb.width * bb.height) > 0.02:
            problems.append(f"{name}: label {_short(t)!r} falls outside its axes")

    #  3. anything the saved image will cut off
    #
    #     ``bbox_inches="tight"`` grows the saved image around figure-level
    #     artists but *clamps* an axis label to the figure, so a label longer
    #     than the figure comes out with its last characters shaved off.  That is
    #     invisible at render time and obvious in print, so the saved extent is
    #     computed here exactly as ``savefig`` computes it and every text is
    #     measured against it.
    try:
        tb = fig.get_tightbbox(r)
        saved = Bbox.from_extents(tb.x0 * fig.dpi, tb.y0 * fig.dpi,
                                  tb.x1 * fig.dpi, tb.y1 * fig.dpi)
    except Exception:
        saved = None
    if saved is not None:
        for ax, t, bb in items:
            if t.get_gid() == OUTSIDE_OK:
                continue
            if _outside_area(bb, saved) / max(1e-9, bb.width * bb.height) > 0.01:
                problems.append(f"{name}: {_short(t)!r} is outside the saved "
                                "image and will be cut off")

    #  4. legend over the data it labels
    for ax in fig.axes:
        lg = ax.get_legend()
        if lg is None:
            continue
        lbb = lg.get_window_extent(r).expanded(1.02, 1.08)
        hits = 0
        for ln in ax.lines:
            if not ln.get_visible() or ln.get_gid() == OVERLAP_OK:
                continue
            xy = ln.get_xydata()
            if len(xy) == 0:
                continue
            for px, py in ax.transData.transform(xy):
                if lbb.x0 <= px <= lbb.x1 and lbb.y0 <= py <= lbb.y1:
                    hits += 1
        for p in ax.patches:
            if not p.get_visible() or p.get_gid() == OVERLAP_OK:
                continue
            try:
                pbb = p.get_window_extent(r)
            except Exception:
                continue
            if _inter_area(pbb, lbb) / max(1e-9, pbb.width * pbb.height) > 0.02:
                hits += 1
        if hits:
            problems.append(f"{name}: legend sits on {hits} drawn element(s)")
    return problems


def _uses_data(ax, t) -> bool:
    tr = t.get_transform()
    return tr is ax.transData or getattr(t, "xycoords", None) == "data"


def _short(t, n: int = 34) -> str:
    s = " ".join(str(t.get_text()).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _save(fig, name: str, strict: bool = True) -> str:
    problems = audit_figure(fig, os.path.splitext(name)[0])
    _AUDIT.append(f"{name}: " + ("OK" if not problems
                                 else f"{len(problems)} PROBLEM(S)"))
    for p in problems:
        _AUDIT.append(f"    - {p}")
    if problems and strict:
        plt.close(fig)
        raise FigureDefect("; ".join(problems))
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.savefig(path)
    fig.savefig(path.replace(".pdf", ".png"))
    plt.close(fig)
    return path


# =========================================================================== #
#  text fitting and collision-avoiding placement                              #
# =========================================================================== #
def _fit_width(t, max_px: float, r, min_fs: float = 4.4) -> None:
    while t.get_window_extent(r).width > max_px and t.get_fontsize() > min_fs:
        t.set_fontsize(t.get_fontsize() * 0.96)


def _boxed(ax, rect, title, body, color, fs_title=8.8, fs_body=7.3,
           pad=0.16, gap=0.16, top_anchored=False):
    """Draw a rounded box and fit a bold title and a body block inside it.

    The text is measured with the renderer and both font sizes are reduced
    together until the block fits the box with room to spare, then the block is
    centred vertically, so nothing can run past an edge and no box carries dead
    space at the bottom.  Returns the two text objects.
    """
    x, y, w, h = rect
    fig = ax.figure
    r = _renderer(fig)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.10",
                                linewidth=1.1, edgecolor=color, facecolor="white",
                                zorder=1))
    cx = x + w / 2
    t = ax.text(cx, y + h, title, ha="center", va="top", fontsize=fs_title,
                color=color, fontweight="bold", linespacing=1.3, zorder=3)
    b = ax.text(cx, y + h, body, ha="center", va="top", fontsize=fs_body,
                color=INK2, linespacing=1.55, zorder=3) if body else None

    ppx, ppy = _ppu(ax)
    avail_w = (w - 2 * pad) * ppx
    avail_h = (h - 2 * pad) * ppy
    for _ in range(80):
        tb = t.get_window_extent(r)
        bb = b.get_window_extent(r) if b is not None else Bbox.from_bounds(0, 0, 0, 0)
        wide = max(tb.width, bb.width) > avail_w
        tall = tb.height + gap * ppy + bb.height > avail_h
        if not wide and not tall:
            break
        t.set_fontsize(t.get_fontsize() * 0.97)
        if b is not None:
            b.set_fontsize(b.get_fontsize() * 0.97)

    tb = t.get_window_extent(r)
    bb = b.get_window_extent(r) if b is not None else Bbox.from_bounds(0, 0, 0, 0)
    th, bh = tb.height / ppy, bb.height / ppy
    total = th + (gap if b is not None else 0.0) + bh
    y_top = (y + h - pad) if top_anchored else (y + h / 2 + total / 2)
    t.set_position((cx, y_top))
    if b is not None:
        b.set_position((cx, y_top - th - gap))
    return t, b


def _place_label(ax, anchor, text, obstacles, r, fontsize, color,
                 bbox=None, zorder=5, reach=(4.0, 8.0, 13.0), others=(),
                 leader=False, hard=(), require_owner=False,
                 max_overlap=None):
    """Place ``text`` near ``anchor`` where it collides least.

    Candidate positions are the eight compass directions at a few distances.
    Each candidate is measured and scored by how much it overlaps what is
    already on the panel and how far it strays outside the axes; the cheapest
    wins, and its box joins the obstacle list so the next label avoids it.

    ``others`` are the points the label must not appear to belong to --- on a map,
    every other node.  A placement is rejected outright unless its box is clearly
    closer to its own anchor than to any of them, because a name that sits beside
    the wrong dot is not untidy, it is wrong; where the panel is too tight for
    that, a leader line joins the name to its point.
    """
    x, y = anchor
    axbb = ax.get_window_extent(r)
    dirs = [(1, 1, "left", "bottom"), (-1, 1, "right", "bottom"),
            (1, -1, "left", "top"), (-1, -1, "right", "top"),
            (1, 0, "left", "center"), (-1, 0, "right", "center"),
            (0, 1, "center", "bottom"), (0, -1, "center", "top"),
            (1.7, 0.6, "left", "bottom"), (-1.7, 0.6, "right", "bottom"),
            (1.7, -0.6, "left", "top"), (-1.7, -0.6, "right", "top"),
            (0.6, 1.7, "center", "bottom"), (-0.6, 1.7, "center", "bottom"),
            (0.6, -1.7, "center", "top"), (-0.6, -1.7, "center", "top")]
    cands = []
    for k, d in enumerate(reach):
        for sx, sy, ha, va in dirs:
            cands.append((sx * d, sy * d, ha, va, k))

    t = ax.annotate(text, (x, y), textcoords="offset points", xytext=(4, 4),
                    fontsize=fontsize, color=color, bbox=bbox, zorder=zorder,
                    annotation_clip=False)
    own = ax.transData.transform(anchor)
    best, best_cost, best_amb = None, math.inf, False
    for dx, dy, ha, va, k in cands:
        t.set_position((dx, dy))
        t.set_ha(ha)
        t.set_va(va)
        bb = t.get_window_extent(r)
        #  a label far from its point is a defect of its own kind, so distance
        #  is priced against overlap rather than used only to break ties
        #  Hard obstacles are the map symbols themselves: a name may sit close
        #  to another town's dot, but it may not cover it.
        cost = 120.0 * sum(_inter_area(bb, o) for o in obstacles) \
            + 600.0 * sum(_inter_area(bb, o) for o in hard) \
            + 12.0 * _outside_area(bb, axbb) + 22.0 * k ** 1.5
        ambiguous = False
        if others:
            #  A reader assigns a name to the dot nearest the name's edge, not to
            #  the dot nearest its centre: a long name whose near edge touches its
            #  own dot reads correctly however far its centre is.
            def _gap(p):
                return math.hypot(min(max(p[0], bb.x0), bb.x1) - p[0],
                                  min(max(p[1], bb.y0), bb.y1) - p[1])
            d_own = _gap(own)
            d_other = min(_gap(p) for p in others)
            #  "closer to its own point" is not enough on a crowded panel: a name
            #  equidistant between two dots reads as belonging to the wrong one.
            #  Ambiguity is priced heavily, and whatever ambiguity survives is
            #  resolved by a leader line rather than left to the reader.
            ambiguous = d_own > 0.8 * d_other
            if ambiguous:
                if require_owner:
                    continue        # not a candidate at all
                cost += 900.0
        if cost < best_cost:
            best, best_cost, best_amb = (dx, dy, ha, va), cost, ambiguous
    if best is None:                # every placement would be ambiguous
        t.remove()
        return None
    if max_overlap is not None:
        t.set_position(best[:2])
        t.set_ha(best[2])
        t.set_va(best[3])
        bb = t.get_window_extent(r)
        area = max(1e-9, bb.width * bb.height)
        if sum(_inter_area(bb, o) for o in obstacles) / area > max_overlap:
            #  nowhere clean left: the label is dropped rather than crowded in
            t.remove()
            return None

    dx, dy, ha, va = best
    t.set_position((dx, dy))
    t.set_ha(ha)
    t.set_va(va)
    bb = t.get_window_extent(r)
    t._leader = None
    if leader and (best_amb or math.hypot(dx, dy) > 1.3 * reach[0]):
        #  A name that had to move far from its point is joined to it by a
        #  hairline, which is what a cartographer does and what lets the search
        #  use the empty space instead of crowding the middle of the panel.
        px, py = ax.transData.transform(anchor)
        tx = min(max(px, bb.x0), bb.x1)
        ty = min(max(py, bb.y0), bb.y1)
        inv = ax.transData.inverted()
        x0, y0 = anchor
        x1, y1 = inv.transform((tx, ty))
        t._leader = ax.plot([x0, x1], [y0, y1], "-", color=INK2, linewidth=0.45,
                            alpha=0.8, zorder=zorder - 1, gid=OVERLAP_OK)[0]
    #  the next label keeps a visible gap from this one rather than
    #  merely avoiding its box
    obstacles.append(bb.expanded(1.0 + 5.0 / max(bb.width, 1.0),
                                 1.0 + 5.0 / max(bb.height, 1.0)))
    return t


def _point_box(ax, x, y, rad=4.0) -> Bbox:
    px, py = ax.transData.transform((x, y))
    return Bbox.from_bounds(px - rad, py - rad, 2 * rad, 2 * rad)


# =========================================================================== #
def fig_instruments(network: str) -> str | None:
    rows = _read(f"instruments_{network}.csv")
    if not rows:
        return None
    fams = [r for r in rows
            if r["model"] in FAMILY_LABEL and r["model"] != "centralized (first best)"]
    labels = [FAMILY_LABEL[r["model"]] for r in fams]
    gaps = [_f(r["gap_pct"]) for r in fams]
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    bars = ax.barh(range(len(fams)), gaps, color=[CAT[i] for i in range(len(fams))],
                   height=0.62)
    ax.set_yticks(range(len(fams)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("coordination gap (% above the first-best social cost)")
    ax.grid(axis="y", visible=False)
    hi = max(gaps) if gaps and max(gaps) > 0 else 1.0
    for b, g in zip(bars, gaps):
        ax.text(b.get_width() + hi * 0.02, b.get_y() + b.get_height() / 2,
                f"{g:.4f}%" if g > 0 else "0 (first best attained)",
                va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(0, hi * 1.45)
    fig.tight_layout()
    return _save(fig, f"fig_instruments_{network}.pdf")


def fig_frontier(network: str) -> str | None:
    """Cost-emissions frontier per instrument family, anchored at each family's reach."""
    rows = _read(f"frontier_{network}.csv")
    reach = _read(f"reach_{network}.csv")
    if not rows:
        return None
    fams: Dict[str, List[dict]] = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    rv = {r["family"]: _f(r["min_attainable_emissions_kgco2"]) for r in reach}
    planner = _f(reach[0]["min_attainable_emissions_kgco2"]) if reach else math.nan

    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    handles: List[Line2D] = []
    for i, (fam, rs) in enumerate(sorted(fams.items())):
        pts = sorted((_f(r["exp_emissions_kgco2"]) / 1e6, _f(r["exp_cost_usd"]) / 1e6)
                     for r in rs if r["exp_cost_usd"])
        if not pts:
            continue
        ln, = ax.plot([p[0] for p in pts], [p[1] for p in pts], DASH[i], color=CAT[i],
                      marker=MARK[i], markersize=4.5, linewidth=1.6,
                      label=FAMILY_LABEL.get(fam, fam), markeredgecolor="white",
                      markeredgewidth=0.6)
        handles.append(ln)
        #  the family's emission reach, drawn attached to the curve: a faint
        #  connector from the curve's cleanest point out to the reach, ending in
        #  a tick.  Detached ticks read as stray data points.
        if fam in rv and not math.isnan(rv[fam]):
            xr, y0 = rv[fam] / 1e6, pts[0][1]
            if xr < pts[0][0] - 1e-9:
                ax.plot([xr, pts[0][0]], [y0, y0], ":", color=CAT[i], linewidth=1.0,
                        alpha=0.9, gid=OVERLAP_OK)
            ax.plot([xr], [y0], marker="|", markersize=11, color=CAT[i],
                    linewidth=1.4, gid=OVERLAP_OK)
    if not math.isnan(planner):
        ax.axvline(planner / 1e6, color=INK, linestyle="--", linewidth=1.1)
    ax.set_xlabel("expected annual corridor CO$_2$  (million kg)")
    ax.set_ylabel("expected social cost  (million USD)")
    extra = [Line2D([], [], color=INK, linestyle="--", linewidth=1.1,
                    label="least emissions a planner could dictate"),
             Line2D([], [], color=INK2, linestyle=":", marker="|", markersize=9,
                    linewidth=1.0, label="family's emission reach")]
    ax.legend(handles=handles + extra, frameon=False, fontsize=7.4, ncol=2,
              loc="upper center", bbox_to_anchor=(0.5, -0.17),
              handlelength=2.6, columnspacing=1.4)
    fig.tight_layout()
    return _save(fig, f"fig_frontier_{network}.pdf")


def fig_reach(network: str) -> str | None:
    """How close each instrument family gets to the planner's emission minimum.

    The bar is what the family demonstrably *attains*; the tick is the proved
    floor below which it cannot go.  Where a search finished the two coincide;
    where it did not, the gap between them is the part that is still open, and
    drawing both keeps the figure from asserting either half on the other's
    evidence.
    """
    reach = _read(f"reach_{network}.csv")
    if not reach:
        return None
    planner = _f(reach[0]["min_attainable_emissions_kgco2"])
    if math.isnan(planner) or planner <= 0:
        return None
    fams = list(reach[1:])
    labs = [FAMILY_LABEL.get(r["family"], r["family"]) for r in fams]
    vals = [100 * (_f(r["min_attainable_emissions_kgco2"]) / planner - 1) for r in fams]
    flo = [100 * (_f(r.get("proved_floor_kgco2")) / planner - 1) for r in fams]
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    ax.barh(range(len(fams)), vals, color=[CAT[i] for i in range(len(fams))], height=0.6)
    for i, v in enumerate(flo):
        if not math.isnan(v):
            ax.plot([v], [i], marker="|", markersize=15, color=INK, linewidth=1.6,
                    zorder=5, clip_on=False, gid=OVERLAP_OK)
    ax.set_yticks(range(len(fams)))
    ax.set_yticklabels(labs)
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, linewidth=0.9)
    ax.set_xlabel("least CO$_2$ the family can induce (% above the planner's minimum)")
    ax.grid(axis="y", visible=False)
    hi = max([v for v in vals if not math.isnan(v)] or [1.0])
    for i, v in enumerate(vals):
        if not math.isnan(v):
            ax.text(v + hi * 0.02, i, f"{v:.1f}%", va="center", fontsize=7.5, color=INK2)
    #  a little room on the left so a proved floor of zero is not hidden under
    #  the zero line, and on the right for the value labels
    ax.set_xlim(-hi * 0.035, hi * 1.28 if hi > 0 else 1)
    ax.legend(handles=[Line2D([], [], color=CAT[0], linewidth=7,
                              label="attainable (a solution achieves it)"),
                       Line2D([], [], color=INK, marker="|", markersize=11,
                              linestyle="none", label="proved floor (nothing below it)")],
              frameon=False, fontsize=7.5, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.26))
    fig.tight_layout()
    return _save(fig, f"fig_reach_{network}.pdf")


def fig_scalability() -> str | None:
    """Runtime and model size against the size of the leader's design space.

    Runs that hit the time limit are lower bounds on the time the method needs,
    not measurements of it, so they are drawn as open markers: the curve through
    them understates the true slope rather than overstating it.
    """
    rows = _read("scalability.csv")
    if not rows:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    xs = [_f(r["log10_design_space"]) for r in rows]

    ax = axes[0]
    series = [("sd_runtime_s", "sd_status", "strong duality (proposed)", 0),
              ("kkt_runtime_s", "kkt_status", "KKT / big-M", 1),
              ("enum_runtime_s", None, "enumeration of designs", 2)]
    ymax = 1.0
    for key, skey, lab, i in series:
        pts = sorted((x, _f(r[key]), (r.get(skey, "") or "") != "optimal" if skey else False)
                     for x, r in zip(xs, rows) if r.get(key))
        pts = [p for p in pts if not math.isnan(p[1])]
        if not pts:
            continue
        ymax = max(ymax, max(p[1] for p in pts))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], DASH[i], color=CAT[i],
                linewidth=1.6, label=lab, zorder=2)
        for x, y, censored in pts:
            ax.plot([x], [y], marker=MARK[i], markersize=4.6, color=CAT[i],
                    markerfacecolor="white" if censored else CAT[i],
                    markeredgecolor=CAT[i] if censored else "white",
                    markeredgewidth=0.9 if censored else 0.6, zorder=3,
                    gid=OVERLAP_OK)
    ax.set_yscale("log")
    ax.set_ylim(top=ymax * 4.0)
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
    ax.set_xlabel("leader's design space  ($\\log_{10}$)")
    ax.set_ylabel("solution time (s)")

    ax = axes[1]
    lo_b, hi_b = math.inf, 0.0
    for key, lab, i in [("sd_binaries", "strong duality (proposed)", 0),
                        ("kkt_binaries", "KKT / big-M", 1)]:
        pts = sorted((x, _f(r[key])) for x, r in zip(xs, rows) if r.get(key))
        pts = [(x, y) for x, y in pts if not math.isnan(y)]
        if not pts:
            continue
        lo_b = min([lo_b] + [p[1] for p in pts])
        hi_b = max([hi_b] + [p[1] for p in pts])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], DASH[i], color=CAT[i],
                marker=MARK[i], markersize=4.6, linewidth=1.6, label=lab,
                markeredgecolor="white", markeredgewidth=0.6)
    ax.set_yscale("log")
    #  the two curves span less than two decades, so decade ticks alone would
    #  leave the smaller model in an unlabelled band: tick the 1-2-5 series
    #  inside the range that is actually drawn and label it in plain numbers.
    if hi_b > 0:
        cand = [c * 10 ** k for k in range(0, 6) for c in (1, 2, 5)]
        ticks = [c for c in cand if lo_b * 0.75 <= c <= hi_b * 1.35]
        if len(ticks) >= 2:
            ax.set_yticks(ticks)
            ax.set_yticklabels([f"{t:,.0f}" for t in ticks])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
    ax.set_xlabel("leader's design space  ($\\log_{10}$)")
    ax.set_ylabel("binary variables")

    handles = [Line2D([], [], color=CAT[i], linestyle=DASH[i], marker=MARK[i],
                      markersize=4.6, markeredgecolor="white", markeredgewidth=0.6,
                      linewidth=1.6, label=lab)
               for i, lab in [(0, "strong duality (proposed)"), (1, "KKT / big-M"),
                              (2, "enumeration of designs")]]
    handles.append(Line2D([], [], color=INK2, linestyle="none", marker="o",
                          markerfacecolor="white", markeredgecolor=INK2,
                          markersize=4.6, label="hit the time limit (lower bound)"))
    fig.tight_layout(rect=(0, 0.10, 1, 1), w_pad=2.2)
    fig.legend(handles=handles, frameon=False, ncol=4, fontsize=7.4,
               loc="lower center", bbox_to_anchor=(0.5, -0.01),
               columnspacing=1.3, handlelength=2.4)
    return _save(fig, "fig_scalability.pdf")


SHORT_COUNTRY = {"Netherlands": "Netherl.", "South Korea": "S. Korea",
                 "South Africa": "S. Africa"}


ISO2 = {"India": "IN", "Mexico": "MX", "Netherlands": "NL", "USA": "US", "China": "CN",
        "UAE": "AE", "South Korea": "KR", "South Africa": "ZA"}


def fig_reversal() -> str | None:
    """Every published grid factor against the emission-neutral threshold.

    Plotted in kg CO2 per kWh rather than per truck-kilometre, because that is the
    axis on which the threshold lives: ef0 = phi*gamma_d/e_elec is a property of
    the two vehicles alone, and every grid factor in the study can be placed above
    or below it by eye.  The shaded band is the threshold carried through the
    published measurement ranges of the two consumption figures, so a bar ending
    inside it is a factor whose sign the data do not determine.
    """
    rows = _read("reversal_thresholds.csv")
    if not rows:
        return None
    seen, order = {}, []
    for r in rows:
        k = (r["country"], r["scenario"].split("-")[-1])
        if k not in seen:
            seen[k] = r
            order.append(k)
    countries, states = [], []
    for c, st in order:
        if c not in countries:
            countries.append(c)
        if st not in states:
            states.append(st)
    label = {"CL": "cleanest", "AV": "weighted average", "MA": "marginal"}
    ef0 = _f(rows[0]["ef_neutral"])
    lo, hi = _f(rows[0]["ef_neutral_low"]), _f(rows[0]["ef_neutral_high"])

    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    n = max(1, len(states))
    width = 0.8 / n
    xs = list(range(len(countries)))
    ax.axhspan(lo, hi, color=INK, alpha=0.10, zorder=0,
               label="threshold over published vehicle ranges")
    ax.axhline(ef0, color=INK, linewidth=1.3, linestyle="--", zorder=1,
               label=f"threshold ef$^0$ = {ef0:.3f}")
    vmax = ef0
    for j, st in enumerate(states):
        vals = [_f(seen[(c, st)]["ef_grid_kgco2_kwh"]) if (c, st) in seen else math.nan
                for c in countries]
        vmax = max([vmax] + [v for v in vals if not math.isnan(v)])
        off = (j - (n - 1) / 2) * width
        ax.bar([x + off for x in xs], vals, width, color=CAT[j % len(CAT)],
               label=label.get(st, st), zorder=2)
        for x, v in zip(xs, vals):
            if math.isnan(v):
                continue
            tag = "above" if v > hi else ("undet." if v > lo else None)
            if tag:
                ax.text(x + off, v, tag, ha="center", va="bottom", rotation=90,
                        fontsize=6.4, color=CAT[j % len(CAT)])
    ax.set_ylim(0, vmax * 1.30)
    ax.set_xticks(xs)
    ax.set_xticklabels([SHORT_COUNTRY.get(c, c) for c in countries], fontsize=7.6)
    ax.set_ylabel("grid intensity (kg CO$_2$/kWh)")
    ax.legend(frameon=False, fontsize=7.2, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, 1.01), columnspacing=1.2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, "fig_reversal.pdf")


def fig_regime_matrix() -> str | None:
    """Corridor x regime, one panel per swap.

    The left panel swaps the whole national regime (grid carbon, both fuel prices
    and the non-fuel haulage cost); the right swaps only the grid emission
    factors.  Drawing both is the point: the full swap moves a cost that is not a
    property of any power system, so only the right panel licenses a statement
    about grids.
    """
    rows = _read("regime_matrix.csv")
    if not rows:
        return None
    from .data_io import load_ports
    ports = load_ports()
    swaps = [w for w in ("full", "grid") if any(r.get("swap") == w for r in rows)]
    if not swaps:
        swaps = [rows[0].get("swap", "full")]
    nets, regs = [], []
    for r in rows:
        if r["network"] not in nets:
            nets.append(r["network"])
        if r["regime_country"] not in regs:
            regs.append(r["regime_country"])
    net_lab = [ports.get(n, {}).get("port", n) for n in nets]
    title = {"full": "full regime swap\n(grid, fuel prices, haulage cost)",
             "grid": "grid-only swap\n(prices and haulage held fixed)"}
    fig, axes = plt.subplots(1, len(swaps), figsize=(3.55 * len(swaps), 3.9),
                             squeeze=False)
    for k, swap in enumerate(swaps):
        ax = axes[0][k]
        grid = [[math.nan] * len(regs) for _ in nets]
        for r in rows:
            if r.get("swap", "full") != swap:
                continue
            grid[nets.index(r["network"])][regs.index(r["regime_country"])] = \
                _f(r["pct_truck_movements_electric"])
        im = ax.imshow(grid, cmap="Blues", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(regs)))
        ax.set_xticklabels([ISO2.get(c, c) for c in regs], fontsize=7)
        ax.set_xlabel("national regime", fontsize=7.5)
        ax.set_yticks(range(len(nets)))
        ax.set_yticklabels(net_lab if k == 0 else [""] * len(nets), fontsize=7)
        ax.set_title(title.get(swap, swap), fontsize=8.5)
        ax.grid(visible=False)
        for i in range(len(nets)):
            for j in range(len(regs)):
                v = grid[i][j]
                if not math.isnan(v):
                    ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.3,
                            color="white" if v > 55 else INK)
    cb = fig.colorbar(im, ax=axes[0].tolist(), fraction=0.035, pad=0.02)
    cb.set_label("truck movements served electrically (%)", fontsize=8)
    return _save(fig, "fig_regime_matrix.pdf")


def fig_collaboration(network: str) -> str | None:
    rows = _read(f"collaboration_heterogeneity_{network}.csv")
    if not rows:
        return None
    xs = [_f(r["heterogeneity"]) for r in rows]
    pool = [_f(r["pooling_gain_usd"]) / 1e3 for r in rows]
    plat = [_f(r["platooning_gain_usd"]) / 1e3 for r in rows]
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    ax.bar(xs, pool, width=0.12, color=CAT[0], label="empty-container pooling")
    ax.bar(xs, plat, width=0.12, bottom=pool, color=CAT[1], label="platoon consolidation")
    ax.set_xlabel("dispersion of the carriers' destination portfolios")
    ax.set_ylabel("grand-coalition gain (thousand USD)")
    tot = [p + q for p, q in zip(pool, plat)]
    ax.set_ylim(0, (max(tot) if tot else 1) * 1.26)
    ax.legend(frameon=False, fontsize=7.8, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, 1.0), columnspacing=1.4)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, f"fig_collaboration_{network}.pdf")


def fig_sensitivity_carbon(network: str) -> str | None:
    rows = [r for r in _read(f"sensitivity_{network}.csv")
            if r["parameter"] == "social_cost_of_carbon_usd_per_kg"]
    if not rows:
        return None
    xs = [_f(r["value"]) * 1000 for r in rows]
    em = [_f(r["exp_emissions_kgco2"]) / 1e6 for r in rows]
    ne = [_f(r["n_electrified"]) for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    axes[0].plot(xs, em, "-", color=CAT[0], marker="o", markersize=4.5, linewidth=1.6,
                 markeredgecolor="white", markeredgewidth=0.6)
    axes[0].set_xlabel("social cost of carbon (USD per tonne CO$_2$)")
    axes[0].set_ylabel("expected annual CO$_2$ (million kg)")
    axes[1].step(xs, ne, where="post", color=CAT[1], linewidth=1.8)
    axes[1].plot(xs, ne, "o", color=CAT[1], markersize=4.5, markeredgecolor="white",
                 markeredgewidth=0.6)
    axes[1].set_xlabel("social cost of carbon (USD per tonne CO$_2$)")
    axes[1].set_ylabel("corridors electrified")
    axes[1].set_ylim(-0.4, max(ne) + 0.6 if ne else 1)
    for a in axes:
        a.set_xlim(0, max(xs) * 1.02 if xs else 1)
        a.xaxis.set_major_locator(MaxNLocator(nbins=5, prune="upper"))
    axes[1].yaxis.set_major_locator(MaxNLocator(integer=True))
    fig.tight_layout(w_pad=2.2)
    return _save(fig, f"fig_sensitivity_carbon_{network}.pdf")


def fig_stochastic(network: str) -> str | None:
    """The value of the stochastic programme, on an honest scale.

    The three cost levels are within a few per cent of one another, so a single
    panel either starts the bars above zero -- which exaggerates the differences
    -- or hides them.  Both panels are therefore drawn: the levels from zero, and
    the two differences that the levels exist to produce.
    """
    rows = _read(f"stochastic_value_{network}.csv")
    if not rows:
        return None
    want = {"WS": None, "RP": None, "EEV": None, "VSS": None, "EVPI": None}
    for r in rows:
        key = r["quantity"].split(" ")[0]
        if key in want and want[key] is None:
            want[key] = _f(r["value_usd"])
    levels = [(k, want[k]) for k in ("WS", "RP", "EEV") if want[k] is not None]
    diffs = [(k, want[k]) for k in ("EVPI", "VSS") if want[k] is not None]
    if not levels:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0),
                             gridspec_kw={"width_ratios": [1.25, 1.0]})
    ax = axes[0]
    vals = [v / 1e6 for _, v in levels]
    ax.bar([k for k, _ in levels], vals, color=[CAT[2], CAT[0], CAT[1]], width=0.56)
    ax.set_ylim(0, max(vals) * 1.22)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,.2f}", ha="center", va="bottom", fontsize=7.6, color=INK2)
    ax.set_ylabel("expected cost (million USD)")
    ax.set_title("cost levels", fontsize=8.5)
    ax.grid(axis="x", visible=False)

    ax = axes[1]
    if diffs:
        dv = [v / 1e3 for _, v in diffs]
        ax.bar([k for k, _ in diffs], dv, color=[CAT[6], CAT[3]], width=0.48)
        ax.set_ylim(0, max(dv) * 1.28 if max(dv) > 0 else 1)
        for i, v in enumerate(dv):
            ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=7.6, color=INK2)
    ax.set_ylabel("value (thousand USD)")
    ax.set_title("EVPI = RP $-$ WS,   VSS = EEV $-$ RP", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, f"fig_stochastic_{network}.pdf")



def _scale_bar(m, ax, lon0, lat0, length_km, fontsize=5.6, color=INK2):
    """A scale bar whose length is ``length_km`` on the ground, not in projection.

    Basemap's own ``drawmapscale`` lays out a bar of ``length`` \emph{projected}
    units.  On a Mercator panel a projected kilometre is a ground kilometre only
    at the equator: at Rotterdam's latitude it is 0.62 of one, so the bar
    overstates distance by more than half.  This draws the bar from the ground
    distance at its own latitude instead, which is what a reader measures with.
    """
    x0, y0 = m(lon0, lat0)
    scale = 1.0 / math.cos(math.radians(lat0))      # Mercator point scale factor
    bar = length_km * 1000.0 * scale
    h = (m.urcrnry - m.llcrnry) * 0.008
    n_seg = 4 if length_km % 4 == 0 else 2
    for i in range(n_seg):
        ax.add_patch(plt.Rectangle((x0 + i * bar / n_seg, y0), bar / n_seg, h,
                                   facecolor="white" if i % 2 else color,
                                   edgecolor=color, linewidth=0.5, zorder=8))
    for i in (0, n_seg // 2, n_seg):
        ax.text(x0 + i * bar / n_seg, y0 - h * 1.4,
                f"{int(length_km * i / n_seg)}", ha="center", va="top",
                fontsize=fontsize, color=color, zorder=8, gid=OVERLAP_OK)
    ax.text(x0 + bar / 2, y0 + h * 1.6, "km", ha="center", va="bottom",
            fontsize=fontsize, color=color, zorder=8, gid=OVERLAP_OK)
    return Bbox.from_extents(*ax.transData.transform((x0 - bar * 0.12, y0 - h * 5)),
                             *ax.transData.transform((x0 + bar * 1.12, y0 + h * 5)))


def _panel_bbox(lons, lats, pad=0.18, aspect=1.05, min_margin=0.11):
    """A panel window around the corridor, padded and shaped to a common aspect.

    Three things are wanted at once.  The window must clear the corridor, it must
    leave every node at least ``min_margin`` of the span from the frame so that
    its name has somewhere to go --- a node hard against the edge is what forces a
    name to sit beside its neighbour instead --- and the four panels must have the
    same proportions, since a window fitted to each corridor alone would give four
    differently shaped panels.  The aspect is equalised in Mercator units, which
    is what the projection will actually show.
    """
    import math

    def merc(lat):
        lat = max(min(lat, 84.0), -84.0)
        return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))

    def inv(y):
        return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)

    w, e = min(lons), max(lons)
    s_, n = min(lats), max(lats)
    w, e = w - (e - w) * pad, e + (e - w) * pad
    s_, n = s_ - (n - s_) * pad, n + (n - s_) * pad

    #  room for the names: no node closer to a frame than min_margin of the span
    for _ in range(8):
        dx, dy = e - w, n - s_
        left = min((x - w) / dx for x in lons)
        right = min((e - x) / dx for x in lons)
        down = min((y - s_) / dy for y in lats)
        up = min((n - y) / dy for y in lats)
        if min(left, right, down, up) >= min_margin - 1e-9:
            break
        if left < min_margin:
            w -= (min_margin - left) * dx
        if right < min_margin:
            e += (min_margin - right) * dx
        if down < min_margin:
            s_ -= (min_margin - down) * dy
        if up < min_margin:
            n += (min_margin - up) * dy

    dx, dy = e - w, merc(n) - merc(s_)
    if dx / dy < aspect:                       # too narrow: widen
        grow = (aspect * dy - dx) / 2
        w, e = w - grow, e + grow
    else:                                      # too short: heighten
        grow_m = (dx / aspect - dy) / 2
        s_, n = inv(merc(s_) - grow_m), inv(merc(n) + grow_m)
    return w, e, s_, n


def fig_study_areas(networks=NETWORKS,
                    resolution: str = "h") -> str:
    """The four corridors on a coastline-and-border base map.

    The base is drawn from the GSHHS shoreline and the WDB political and river
    lines that ship with Basemap, so the figure is reproducible offline and needs
    no tile server.  ``src/figures_osm.py`` draws the same figure on an
    OpenStreetMap or CartoDB raster base for anyone who wants one and has network
    access to those tiles.

    Place names are placed by the same collision search as before, with the
    coastline, the graticule labels and the scale bar all treated as obstacles.
    """
    from mpl_toolkits.basemap import Basemap
    from .data_io import load_network, load_ports

    LAND, WATER, COAST = "#f4f1e9", "#d8e8f3", "#7d8d99"
    BORDER, RIVER = "#a6b0b8", "#9cc4de"

    ports = load_ports()
    #  The figure is drawn at the size it is printed --- a hair under the text
    #  block --- so that the place names are the size they were designed to be
    #  rather than whatever a scale factor makes of them.
    nrow = (len(networks) + 1) // 2
    fig, axes = plt.subplots(nrow, 2, figsize=(6.3, 3.0 * nrow))
    fig.subplots_adjust(left=0.055, right=0.985, top=1 - 0.048 * 2 / nrow,
                        bottom=0.112 * 2 / nrow, wspace=0.17, hspace=0.25)

    for ax, nm in zip(axes.ravel(), networks):
        net = load_network(nm, ports[nm]["circuity"])
        lons = [i["lon"] for i in net.node_info.values()]
        lats = [i["lat"] for i in net.node_info.values()]
        w, e, s_, n = _panel_bbox(lons, lats)

        m = Basemap(projection="merc", llcrnrlon=w, urcrnrlon=e, llcrnrlat=s_,
                    urcrnrlat=n, resolution=resolution, ax=ax)
        m.drawmapboundary(fill_color=WATER, linewidth=0.6, color=INK2)
        m.fillcontinents(color=LAND, lake_color=WATER)
        m.drawcoastlines(linewidth=0.45, color=COAST)
        m.drawcountries(linewidth=0.45, color=BORDER)
        try:
            m.drawrivers(linewidth=0.3, color=RIVER)
        except Exception:      # the river database is optional
            pass
        #  a sparse graticule: enough to read a coordinate off, not enough to
        #  compete with the corridor
        import numpy as _np
        par = _np.round(_np.linspace(s_, n, 4)[1:-1], 1)
        mer = _np.round(_np.linspace(w, e, 4)[1:-1], 1)
        grat = []
        d = m.drawparallels(par, labels=[1, 0, 0, 0], fontsize=6, color=BORDER,
                            linewidth=0.25, dashes=[2, 3], fmt="%.1f")
        grat += [t for v in d.values() for t in v[1]]
        d = m.drawmeridians(mer, labels=[0, 0, 0, 1], fontsize=6, color=BORDER,
                            linewidth=0.25, dashes=[2, 3], fmt="%.1f")
        grat += [t for v in d.values() for t in v[1]]
        #  Basemap draws graticule labels just outside the frame, which is where
        #  they belong; the layout audit is told so rather than being loosened.
        for t in grat:
            t.set_gid(OUTSIDE_OK)

        xy = {k: m(i["lon"], i["lat"]) for k, i in net.node_info.items()}
        for edge in net.edges:
            a, b = xy[edge[0]], xy[edge[1]]
            ax.plot([a[0], b[0]], [a[1], b[1]], "-",
                    color=CAT[0] if net.edge_info[edge]["electrifiable"] else "#9b9b9b",
                    linewidth=1.7, zorder=4, solid_capstyle="round", gid=OVERLAP_OK)
        for k, info in net.node_info.items():
            role = info["role"]
            ax.scatter(*xy[k], s=42 if role == "port" else 22,
                       marker="s" if role == "port" else ("^" if role == "junction" else "o"),
                       color=CAT[1] if role == "port" else (INK2 if role == "junction" else CAT[2]),
                       zorder=6, edgecolor="white", linewidth=0.7)

        ax.set_title(f"{ports[nm]['port']} ({ports[nm]['country']})", fontsize=9)
        ax.grid(visible=False)

        #  Scale bar, in the emptiest corner of the panel so that it neither
        #  covers a link nor forces a place name somewhere worse.
        ground_w_km = (m.urcrnrx - m.llcrnrx) * math.cos(
            math.radians((s_ + n) / 2)) / 1000.0
        step = max([v for v in (10, 25, 50, 100, 200, 400, 800)
                    if v <= ground_w_km / 3.6] or [10])
        pts = list(xy.values()) + [((xy[a][0] + xy[b][0]) / 2, (xy[a][1] + xy[b][1]) / 2)
                                   for a, b in net.edges]
        best, best_load = (0.10, 0.10), None
        #  bottom left everywhere unless the corridor is there: a reader should
        #  find the bar in the same place on every panel
        for pref, (fx, fy) in enumerate(((0.10, 0.10), (0.55, 0.10),
                                         (0.10, 0.86), (0.55, 0.86))):
            cx = m.llcrnrx + (fx + 0.17) * (m.urcrnrx - m.llcrnrx)
            cy = m.llcrnry + fy * (m.urcrnry - m.llcrnry)
            load = sum(1 for px, py in pts
                       if abs(px - cx) < 0.30 * (m.urcrnrx - m.llcrnrx)
                       and abs(py - cy) < 0.16 * (m.urcrnry - m.llcrnry)) + 0.25 * pref
            if best_load is None or load < best_load:
                best, best_load = (fx, fy), load
        fx, fy = best
        lon0, lat0 = m(m.llcrnrx + fx * (m.urcrnrx - m.llcrnrx),
                       m.llcrnry + fy * (m.urcrnry - m.llcrnry), inverse=True)
        scale_box = _scale_bar(m, ax, lon0, lat0, step)

        r = _renderer(fig)
        obstacles = [scale_box]
        obstacles += [t.get_window_extent(r) for t in grat if t.get_text().strip()]
        obstacles += [t.get_window_extent(r) for t in ax.texts if t.get_text().strip()]
        marks = [_point_box(ax, *xy[k], 5.5) for k in net.node_info]
        obstacles += marks

        #  Place names first: they carry the identity of the panel, and a name
        #  that has to move is worse than a distance that has to move.  The
        #  distances follow, into whatever room is left, and may slide along
        #  their own link to find it.
        rank = {"port": 0, "demand": 1, "junction": 2}
        for k, info in sorted(net.node_info.items(),
                              key=lambda kv: rank.get(kv[1]["role"], 1)):
            name = MAP_NAME.get(info["name"], info["name"])
            #  Redundancy is what crowds a panel this size.  The title already
            #  names the port and the legend already says what a square and a
            #  triangle are, so the port's own name is dropped where the title
            #  carries it, and the words "Port" and "junction" are dropped from
            #  the rest.  What is left is the part a reader cannot get anywhere
            #  else: "Maasvlakte", "Waalhaven", "Melipilla".
            port_name = ports[nm]["port"]
            name = re.sub(r"\s+junction$", "", name, flags=re.I)
            name = re.sub(r"\s+Port$", "", name, flags=re.I)
            short = re.sub(re.escape(port_name), "", name, flags=re.I).strip(" -/,")
            if info["role"] == "port" and not short:
                continue                      # the panel title is its label
            name = short or name
            txt = textwrap.fill(name, 15) if len(name) > 17 else name
            fs = {"port": 5.9, "demand": 5.5}.get(info["role"], 5.0)
            #  The port's name is the longest on the panel and its point is the
            #  most crowded, so it is sent further out from the start and joined
            #  by a leader: that leaves the near slots to the shorter names
            #  around it instead of taking the only good one.
            rch = ((14.0, 20.0, 28.0, 36.0, 45.0) if info["role"] == "port"
                   else (5.0, 9.0, 14.0, 20.0, 27.0, 35.0, 45.0))
            _place_label(ax, xy[k], txt, obstacles, r, fs,
                         INK if info["role"] != "junction" else INK2,
                         bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none",
                                   alpha=0.82),
                         zorder=9, reach=rch, leader=True, hard=marks,
                         require_owner=(info["role"] == "junction"),
                         max_overlap=0.02 if info["role"] == "junction" else None,
                         others=[ax.transData.transform(xy[o]) for o in net.node_info
                                 if o != k])
        for edge in net.edges:
            a, b = xy[edge[0]], xy[edge[1]]
            placed = False
            for f in (0.5, 0.38, 0.62, 0.28, 0.72):
                mid = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
                before = len(obstacles)
                t = _place_label(ax, mid, f"{net.edge_info[edge]['km']:.0f}",
                                 obstacles, r, 5.4, INK2,
                                 bbox=dict(boxstyle="round,pad=0.10", fc="white",
                                           ec="none", alpha=0.85),
                                 zorder=8, reach=(0.0, 5.0, 9.0))
                bb = obstacles[-1]
                clash = any(_inter_area(bb, o) / max(1e-9, bb.width * bb.height) > 0.05
                            for o in obstacles[:before])
                if not clash:
                    placed = True
                    break
                t.remove()
                obstacles.pop()
            if not placed:      # keep the last try rather than drop the number
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                _place_label(ax, mid, f"{net.edge_info[edge]['km']:.0f}", obstacles,
                             r, 5.4, INK2,
                             bbox=dict(boxstyle="round,pad=0.10", fc="white",
                                       ec="none", alpha=0.85),
                             zorder=8, reach=(0.0, 5.0, 9.0, 13.0))

    handles = [Line2D([], [], marker="s", color="none", markerfacecolor=CAT[1],
                      markersize=7, label="port"),
               Line2D([], [], marker="^", color="none", markerfacecolor=INK2,
                      markersize=7, label="junction"),
               Line2D([], [], marker="o", color="none", markerfacecolor=CAT[2],
                      markersize=7, label="hinterland demand node"),
               Line2D([], [], color=CAT[0], linewidth=1.8,
                      label="electrifiable corridor link")]
    if any(not net_.edge_info[e]["electrifiable"]
           for net_ in (load_network(x, ports[x]["circuity"]) for x in networks)
           for e in net_.edges):
        #  only claimed in the legend if some link on some panel is drawn that way
        handles.append(Line2D([], [], color="#9b9b9b", linewidth=1.8,
                              label="link not electrifiable"))
    fig.legend(handles=handles, frameon=False, ncol=5, loc="lower center",
               bbox_to_anchor=(0.5, 0.028), fontsize=7.4, columnspacing=1.2)
    fig.text(0.5, 0.004, "Numbers on the links are road kilometres. Shoreline, "
             "national borders and rivers from the GSHHS and WDB databases "
             "distributed with Basemap.",
             ha="center", va="bottom", fontsize=6.4, color=INK2)
    return _save(fig, "fig_study_areas.pdf")


def fig_framework() -> str:
    """Schematic of the model and of the exact reformulation.

    Every block of text in this figure is fitted to its box by measurement, so a
    longer caption shrinks the type rather than running over an edge.
    """
    fig = plt.figure(figsize=(7.2, 4.0))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    ax.grid(visible=False)

    _boxed(ax, (0.25, 4.25, 4.0, 1.90),
           "Leader: corridor authority\n(here and now)",
           "electrify edge  $y_e \\in \\{0,1\\}$\n"
           "charging bays  $g_e$  (350 kW each)\n"
           "corridor charge  $\\theta_s$  per diesel truck-km\n"
           "charging surcharge  $\\sigma_s$  per kWh", CAT[0])
    _boxed(ax, (5.75, 4.25, 4.0, 1.90),
           "Followers: carrier coalition\n(one programme per scenario)",
           "loaded flows, pooled empty repositioning\n"
           "traction mode: electric or diesel\n"
           "platoon formation and charging\n"
           "linear programme $\\Rightarrow$ exact duality", CAT[1])

    #  the reformulation box: title, three ingredient chips, two closing notes
    bx, by, bw, bh = 0.25, 0.68, 9.5, 2.17
    ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.10",
                                linewidth=1.1, edgecolor=CAT[6], facecolor="white",
                                zorder=1))
    r = _renderer(fig)
    ppx, ppy = _ppu(ax)
    t = ax.text(bx + bw / 2, by + bh - 0.18, "Exact single-level reformulation",
                ha="center", va="top", fontsize=9.0, color=CAT[6],
                fontweight="bold", zorder=3)
    _fit_width(t, (bw - 0.4) * ppx, r)

    chips = [("primal feasibility", "$A x \\geq b(w)$"),
             ("dual feasibility", "$A^{\\top}\\lambda \\leq c(w)$"),
             ("strong duality", "$c(w)^{\\top} x = b(w)^{\\top}\\lambda$")]
    cw, gap = 2.8, 0.30
    x0 = bx + (bw - (len(chips) * cw + (len(chips) - 1) * gap)) / 2
    for i, (cap, math_) in enumerate(chips):
        cx0 = x0 + i * (cw + gap)
        _boxed(ax, (cx0, 1.35, cw, 0.92), cap, math_, INK2,
               fs_title=7.6, fs_body=8.6, pad=0.12, gap=0.10)
        if i:
            ax.text(cx0 - gap / 2, 1.35 + 0.92 / 2, "$+$", ha="center", va="center",
                    fontsize=9, color=CAT[6], zorder=3)

    notes = ("every leader$\\times$follower product is binary $\\times$ bounded-continuous "
             "and linearises exactly\n"
             "no complementarity binaries; the one dual bound the model needs is proved "
             "by an exchange argument, not chosen")
    nt = ax.text(bx + bw / 2, 1.20, notes, ha="center", va="top", fontsize=7.2,
                 color=INK2, linespacing=1.6, zorder=3)
    _fit_width(nt, (bw - 0.5) * ppx, r)

    #  couplings
    ax.add_patch(FancyArrowPatch((4.3, 5.50), (5.7, 5.50), arrowstyle="->",
                                 mutation_scale=11, color=INK2, linewidth=1.1))
    ax.text(5.0, 5.61, "$y,g,\\theta,\\sigma$", ha="center", va="bottom",
            fontsize=7.4, color=INK2)
    ax.add_patch(FancyArrowPatch((5.7, 4.72), (4.3, 4.72), arrowstyle="->",
                                 mutation_scale=11, color=INK2, linewidth=1.1))
    ax.text(5.0, 4.61, "best response", ha="center", va="top", fontsize=7.4,
            color=INK2)
    ax.add_patch(FancyArrowPatch((5.0, 4.20), (5.0, 2.95), arrowstyle="->",
                                 mutation_scale=11, color=INK2, linewidth=1.1))
    ax.text(5.18, 3.57, "solved as one MILP", ha="left", va="center", fontsize=7.2,
            color=INK2)
    return _save(fig, "fig_framework.pdf")


def fig_policy_framework() -> str:
    """Policy framing of the study: who decides what, under which uncertainty,
    and the three policy questions the model answers.

    Drawn with the same measured text fitting as the other schematics, so no
    label can run past its box.
    """
    fig = plt.figure(figsize=(7.2, 4.0))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0, 10)
    ax.set_ylim(0.35, 6.9)
    ax.axis("off")
    ax.grid(visible=False)

    #  row 1: the two actors and the uncertainty between them
    _boxed(ax, (0.25, 4.55, 3.55, 2.05),
           "Corridor authority",
           "which links to electrify\n"
           "how much charging capacity\n"
           "corridor charge per diesel truck-km\n"
           "charging surcharge per kWh", CAT[0])
    _boxed(ax, (6.20, 4.55, 3.55, 2.05),
           "Carrier coalition",
           "routes and empty-container pooling\n"
           "electric or diesel traction\n"
           "platoon formation\n"
           "responds to its own costs", CAT[1])
    _boxed(ax, (4.10, 5.00, 1.80, 0.95),
           "Uncertainty", "freight demand\ngrid carbon intensity", INK2,
           fs_title=7.6, fs_body=6.8, pad=0.10, gap=0.08)

    ax.add_patch(FancyArrowPatch((3.85, 6.25), (6.15, 6.25), arrowstyle="->",
                                 mutation_scale=11, color=INK2, linewidth=1.1))
    ax.text(5.0, 6.33, "infrastructure and prices", ha="center", va="bottom",
            fontsize=7.0, color=INK2)
    ax.add_patch(FancyArrowPatch((6.15, 4.80), (3.85, 4.80), arrowstyle="->",
                                 mutation_scale=11, color=INK2, linewidth=1.1))
    ax.text(5.0, 4.70, "operating response", ha="center", va="top",
            fontsize=7.0, color=INK2)

    #  row 2: what the authority is judged on
    _boxed(ax, (1.40, 2.95, 7.20, 0.85),
           "Social cost the authority minimises",
           "investment + operating cost + CO$_2$ at the social cost of carbon "
           "+ grid stress", CAT[6], fs_title=7.8, fs_body=7.0, pad=0.10, gap=0.08)
    ax.add_patch(FancyArrowPatch((5.0, 4.30), (5.0, 3.85), arrowstyle="->",
                                 mutation_scale=10, color=INK2, linewidth=1.0))

    #  row 3: the three policy questions
    qs = [("Q1  Does electrifying\ncut CO$_2$?",
           "only below a grid intensity\nset by the two drivetrains;\n"
           "the emission-factor choice\ncan decide the verdict", CAT[2]),
          ("Q2  How should the\ncorridor be priced?",
           "charge diesel truck-km,\ndiscount platoons by their\n"
           "energy saving, index the\ncharging surcharge to the grid", CAT[0]),
          ("Q3  What should\ncarriers share?",
           "information to pool empty\ncontainers: it carries most\n"
           "of the collaboration gain,\nplatooning little", CAT[1])]
    qw, qg = 3.00, 0.25
    for i, (title, body, col) in enumerate(qs):
        _boxed(ax, (0.25 + i * (qw + qg), 0.55, qw, 1.85), title, body, col,
               fs_title=7.8, fs_body=6.9, pad=0.12, gap=0.12)
    ax.add_patch(FancyArrowPatch((5.0, 2.90), (5.0, 2.50), arrowstyle="->",
                                 mutation_scale=10, color=INK2, linewidth=1.0))
    return _save(fig, "fig_policy_framework.pdf")


def make_all(network: str = FOCAL, strict: bool = True) -> List[str]:
    """Render every manuscript figure and write the layout audit.

    A figure that *raises* is a defect and is re-raised by default: either its
    data is missing in a way that matters or its layout failed the audit.  A
    figure that returns ``None`` because its result file does not exist yet is a
    different matter and is simply skipped.
    """
    del _AUDIT[:]
    jobs = [("framework", lambda: fig_framework()),
            ("policy framework", lambda: fig_policy_framework()),
            ("study areas", lambda: fig_study_areas()),
            ("instruments", lambda: fig_instruments(network)),
            ("frontier", lambda: fig_frontier(network)),
            ("reach", lambda: fig_reach(network)),
            ("scalability", lambda: fig_scalability()),
            ("reversal", lambda: fig_reversal()),
            ("regime matrix", lambda: fig_regime_matrix()),
            ("collaboration", lambda: fig_collaboration(network)),
            ("carbon sensitivity", lambda: fig_sensitivity_carbon(network)),
            ("stochastic", lambda: fig_stochastic(network))]
    out, failed = [], []
    for name, fn in jobs:
        try:
            p = fn()
            if p:
                out.append(p)
            else:
                print(f"   figure skipped (no result file yet): {name}", flush=True)
        except Exception as exc:
            failed.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"   FIGURE FAILED {name}: {exc}", flush=True)
    os.makedirs(FIG, exist_ok=True)
    with open(os.path.join(FIG, "FIGURE_AUDIT.txt"), "w") as fh:
        fh.write("Layout audit: overlapping labels, labels outside their axes,\n"
                 "legends drawn over data.  Checked by measurement at render time.\n\n")
        fh.write("\n".join(_AUDIT) + "\n")
        if failed:
            fh.write("\nFAILED TO RENDER\n" + "\n".join(f"    - {x}" for x in failed) + "\n")
    if failed and strict:
        raise RuntimeError("figures failed to render: " + "; ".join(failed))
    return out
