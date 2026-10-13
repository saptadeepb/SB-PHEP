"""Graphical abstract: symbols and schematics only, no numerical values.

    python3 -m src.graphical_abstract   ->  outputs/figures/graphical_abstract.png

Elsevier asks for at least 1328 x 531 pixels (width x height); the figure is drawn
at twice that size.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Circle, FancyArrowPatch, FancyBboxPatch, Polygon,
                                Rectangle, Wedge)

INK, INK2 = "#1f2a33", "#5b6770"
BLUE, ORANGE, GREEN, GREY, RED = "#2a6fdb", "#e8692f", "#1aa37a", "#9aa4ab", "#c0392b"
PANEL = ["#eaf2fd", "#fdf0e8", "#e7f6f0"]


def truck(ax, x, y, s=1.0, body=BLUE, electric=False, z=5):
    """A side-on tractor and trailer; a bolt marks the electric truck."""
    ax.add_patch(FancyBboxPatch((x, y + 0.10 * s), 0.62 * s, 0.30 * s,
                                boxstyle="round,pad=0.005,rounding_size=0.02",
                                fc=body, ec=INK, lw=0.8, zorder=z))
    ax.add_patch(FancyBboxPatch((x + 0.64 * s, y + 0.10 * s), 0.22 * s, 0.24 * s,
                                boxstyle="round,pad=0.005,rounding_size=0.03",
                                fc="white", ec=INK, lw=0.8, zorder=z))
    ax.add_patch(Rectangle((x + 0.70 * s, y + 0.22 * s), 0.10 * s, 0.08 * s,
                           fc="#cfe3f7", ec=INK, lw=0.5, zorder=z + 1))
    for cx in (0.10, 0.24, 0.52, 0.76):
        ax.add_patch(Circle((x + cx * s, y + 0.09 * s), 0.055 * s, fc=INK, ec="white",
                            lw=0.6, zorder=z + 1))
    if electric:
        bx, by = x + 0.26 * s, y + 0.25 * s
        ax.add_patch(Polygon([(bx, by + 0.12 * s), (bx + 0.07 * s, by + 0.12 * s),
                              (bx + 0.02 * s, by + 0.03 * s), (bx + 0.10 * s, by + 0.03 * s),
                              (bx - 0.01 * s, by - 0.12 * s), (bx + 0.03 * s, by - 0.01 * s),
                              (bx - 0.04 * s, by - 0.01 * s)],
                             closed=True, fc="#ffd84d", ec=INK, lw=0.6, zorder=z + 2))
    else:
        for k in range(3):
            ax.add_patch(Circle((x + 0.90 * s + 0.05 * k * s, y + 0.40 * s + 0.06 * k * s),
                                (0.025 + 0.012 * k) * s, fc=GREY, ec="none", alpha=0.7,
                                zorder=z))


def container(ax, x, y, w, h, c, z=5):
    ax.add_patch(Rectangle((x, y), w, h, fc=c, ec=INK, lw=0.7, zorder=z))
    for k in range(1, 5):
        ax.plot([x + k * w / 5] * 2, [y + 0.12 * h, y + 0.88 * h], color="white",
                lw=0.6, zorder=z + 1)


def plug(ax, x, y, s=1.0, z=6):
    ax.add_patch(FancyBboxPatch((x, y), 0.16 * s, 0.20 * s,
                                boxstyle="round,pad=0.005,rounding_size=0.03",
                                fc="white", ec=INK, lw=0.8, zorder=z))
    for dx in (0.04, 0.10):
        ax.add_patch(Rectangle((x + dx * s, y + 0.20 * s), 0.025 * s, 0.07 * s,
                               fc=INK, ec="none", zorder=z))
    ax.plot([x + 0.08 * s, x + 0.08 * s], [y, y - 0.10 * s], color=INK, lw=1.2, zorder=z)


def star(ax, x, y, r, c="#f5b700", z=9):
    import math
    pts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    ax.add_patch(Polygon(pts, closed=True, fc=c, ec=INK, lw=0.6, zorder=z))


def arrow(ax, a, b, c=INK2, lw=1.6, style="-|>", rad=0.0, z=4):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12, color=c,
                                 lw=lw, connectionstyle=f"arc3,rad={rad}", zorder=z))


def main() -> str:
    fig = plt.figure(figsize=(13.28, 5.31), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13.28)
    ax.set_ylim(0, 5.31)
    ax.axis("off")

    # title band
    ax.text(6.64, 5.02, "When does electrifying port-hinterland trucking cut emissions?",
            ha="center", va="center", fontsize=17, weight="bold", color=INK)

    xs = [0.18, 4.58, 8.98]
    w, h, y0 = 4.12, 3.95, 0.62
    titles = ["Which grid decides", "How to price the corridor", "What carriers should share"]
    for k, x in enumerate(xs):
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=PANEL[k], ec="none", zorder=1))
        ax.text(x + w / 2, y0 + h - 0.25, titles[k], ha="center", va="center",
                fontsize=13.5, weight="bold", color=[BLUE, ORANGE, GREEN][k])
        star(ax, x + w - 0.25, y0 + h - 0.25, 0.14)

    # ---- panel 1: threshold set by the two vehicles; load-weighted grid factor
    x = xs[0]
    truck(ax, x + 0.30, 3.25, 0.95, body=GREY)
    truck(ax, x + 2.55, 3.25, 0.95, body=BLUE, electric=True)
    ax.text(x + 2.05, 3.47, "vs", ha="center", va="center", fontsize=12, color=INK2,
            style="italic")
    # grid-intensity scale: clean to dirty, with the threshold marker
    gx, gy, gw, gh = x + 0.35, 2.30, 3.40, 0.32
    n = 60
    for i in range(n):
        f = i / (n - 1)
        col = (0.10 + 0.55 * f, 0.64 - 0.40 * f, 0.48 - 0.36 * f)
        ax.add_patch(Rectangle((gx + gw * i / n, gy), gw / n + 0.002, gh, fc=col, ec="none",
                               zorder=3))
    ax.add_patch(Rectangle((gx, gy), gw, gh, fc="none", ec=INK, lw=0.8, zorder=4))
    tx = gx + 0.58 * gw
    ax.add_patch(Rectangle((tx - 0.30, gy - 0.04), 0.60, gh + 0.08, fc="white", ec=INK,
                           lw=0.6, alpha=0.35, zorder=4, hatch="////"))
    ax.plot([tx, tx], [gy - 0.12, gy + gh + 0.16], color=INK, lw=2.2, zorder=5)
    ax.text(gx, gy - 0.22, "clean grid", ha="left", va="center", fontsize=9.5, color=INK2)
    ax.text(gx + gw, gy - 0.22, "carbon-heavy grid", ha="right", va="center",
            fontsize=9.5, color=INK2)
    ax.text(tx, gy + gh + 0.30, "threshold set by the two vehicles alone",
            ha="center", va="center", fontsize=10, color=INK, weight="bold")
    arrow(ax, (x + 0.75, 3.18), (tx - 0.25, gy + gh + 0.48), rad=-0.15)
    arrow(ax, (x + 3.00, 3.18), (tx + 0.25, gy + gh + 0.48), rad=0.15)
    # grid states weighted by charging
    bx, by = x + 0.55, 0.95
    hs = [0.32, 0.62, 0.95]
    cols = [GREEN, "#c9a227", "#6b3f2a"]
    labs = ["cleanest", "average", "marginal"]
    for i in range(3):
        ax.add_patch(Rectangle((bx + i * 0.55, by), 0.38, hs[i], fc=cols[i], ec=INK, lw=0.6,
                               zorder=3))
        ax.text(bx + i * 0.55 + 0.19, by - 0.13, labs[i], ha="center", va="center",
                fontsize=8.2, color=INK2)
    plug(ax, bx + 1.80, by + 0.30, 1.2)
    arrow(ax, (bx + 2.15, by + 0.55), (bx + 1.45, by + 0.80), c=BLUE, rad=0.3)
    ax.text(bx + 2.20, by + 0.40, "weight grid\nstates by when\ntrucks charge",
            ha="left", va="center", fontsize=9.5, color=INK, linespacing=1.2)

    # ---- panel 2: the unique carbon-aligned charge
    x = xs[1]
    # toll gantry
    ax.add_patch(Rectangle((x + 0.30, 1.05), 0.10, 2.55, fc=INK2, ec="none", zorder=3))
    ax.add_patch(Rectangle((x + 3.72, 1.05), 0.10, 2.55, fc=INK2, ec="none", zorder=3))
    ax.add_patch(Rectangle((x + 0.30, 3.50), 3.52, 0.20, fc=INK2, ec="none", zorder=3))
    rows = [(3.00, "charge diesel truck-kilometers", GREY, False),
            (2.15, "discount platoons by their energy saving", BLUE, True),
            (1.30, "surcharge on charging that follows the grid", BLUE, True)]
    for yy, lab, col, el in rows:
        ax.add_patch(FancyBboxPatch((x + 0.55, yy - 0.22), 3.02, 0.58,
                                    boxstyle="round,pad=0.01,rounding_size=0.08",
                                    fc="white", ec=ORANGE, lw=1.2, zorder=4))
        ax.text(x + 2.06, yy + 0.20, lab, ha="center", va="center", fontsize=9.6,
                color=INK, zorder=6)
    truck(ax, x + 0.75, 2.78, 0.42, body=GREY, z=6)
    truck(ax, x + 0.75, 1.93, 0.36, body=BLUE, electric=True, z=6)
    truck(ax, x + 1.12, 1.93, 0.36, body=BLUE, electric=True, z=6)
    plug(ax, x + 0.80, 1.10, 0.75)
    ax.plot([x + 1.08, x + 1.20, x + 1.32, x + 1.44, x + 1.56, x + 1.68],
            [1.22, 1.32, 1.18, 1.34, 1.16, 1.28], color=ORANGE, lw=1.3, zorder=6)
    ax.text(x + 2.06, 0.82, "the only linear charge that aligns carriers\nwith the public interest",
            ha="center", va="center", fontsize=10, weight="bold", color=INK, linespacing=1.15)


    # ---- panel 3: pooling empty containers versus platooning
    x = xs[2]
    # two carriers' depots exchanging empty containers at an inland node
    ax.add_patch(Circle((x + 2.06, 2.55), 0.62, fc="white", ec=GREEN, lw=1.4, zorder=3))
    ax.text(x + 2.06, 2.55, "inland\nnode", ha="center", va="center", fontsize=9.5,
            color=INK, linespacing=1.1, zorder=4)
    container(ax, x + 0.35, 3.15, 0.85, 0.30, "#d1495b")
    container(ax, x + 0.35, 1.70, 0.85, 0.30, "#d1495b")
    container(ax, x + 2.95, 3.15, 0.85, 0.30, "#2e86ab")
    container(ax, x + 2.95, 1.70, 0.85, 0.30, "#2e86ab")
    ax.text(x + 0.78, 3.60, "carrier A", ha="center", va="center", fontsize=9, color=INK2)
    ax.text(x + 3.38, 3.60, "carrier B", ha="center", va="center", fontsize=9, color=INK2)
    arrow(ax, (x + 1.22, 3.15), (x + 1.55, 2.85), c=GREEN, lw=2.0)
    arrow(ax, (x + 2.56, 2.25), (x + 2.95, 1.98), c=GREEN, lw=2.0)
    arrow(ax, (x + 2.95, 3.15), (x + 2.60, 2.85), c=GREEN, lw=2.0)
    arrow(ax, (x + 1.55, 2.25), (x + 1.22, 1.98), c=GREEN, lw=2.0)
    ax.text(x + 2.06, 1.30, "pool empty containers", ha="center", va="center",
            fontsize=11.5, weight="bold", color=GREEN)
    # platooning, drawn small with a cap
    truck(ax, x + 0.85, 0.78, 0.34, body=GREY, z=6)
    truck(ax, x + 1.20, 0.78, 0.34, body=GREY, z=6)
    ax.plot([x + 0.80, x + 1.58], [1.06, 1.06], color=RED, lw=2.2, zorder=7)
    ax.text(x + 1.72, 0.92, "platooning gain is capped", ha="left", va="center",
            fontsize=9.5, color=INK2)


    # arrows between panels
    arrow(ax, (xs[0] + w + 0.02, 2.6), (xs[1] - 0.02, 2.6), c=INK2, lw=2.0)
    arrow(ax, (xs[1] + w + 0.02, 2.6), (xs[2] - 0.02, 2.6), c=INK2, lw=2.0)

    # evidence band
    ax.add_patch(Circle((0.55, 0.30), 0.17, fc="#cfe3f7", ec=INK, lw=0.8, zorder=3))
    ax.plot([0.38, 0.72], [0.30, 0.30], color=INK, lw=0.6, zorder=4)
    ax.add_patch(Wedge((0.55, 0.30), 0.17, 90, 270, width=0.06, fc="none", ec=INK, lw=0.5,
                       zorder=4))
    ax.text(0.85, 0.30, "Tested on the grids of the world's busiest container ports and on "
            "gateway corridors in Europe, China, North America, the Gulf and South Asia",
            ha="left", va="center", fontsize=10.5, color=INK)
    star(ax, 11.95, 0.30, 0.11)
    ax.text(12.12, 0.30, "new result", ha="left", va="center", fontsize=9.5, color=INK2)

    out = os.path.join("outputs", "figures", "graphical_abstract.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(main())
