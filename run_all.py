"""
run_all.py
==========
End-to-end reproduction driver.

    python3 -m src.run_all                 # everything
    python3 -m src.run_all validate        # correctness tests only
    python3 -m src.run_all main            # focal-case results
    python3 -m src.run_all cross           # cross-country and regime matrix
    python3 -m src.run_all frontier        # reach and the cost-emission frontier
    python3 -m src.run_all extras          # contingency, seed robustness, stability
    python3 -m src.run_all scale           # scalability study
    python3 -m src.run_all figures         # rebuild figures from existing CSVs

``extras`` also splits into ``contingency``, ``seeds`` and ``stability`` so that
independent stages can be run concurrently; ``summary.json`` is written under a
lock and merged, so concurrent stages do not overwrite each other's keys.

Results are written to ``outputs/tables`` (CSV) and ``outputs/figures`` (PDF and
PNG).  A machine-readable summary of every headline number the manuscript quotes
is written to ``outputs/summary.json`` and is what ``check_manuscript.py`` reads
when it verifies the text against the computations.
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from typing import Any, Dict

from . import cooperative_game as CG
from . import experiments as X
from . import figures as F
from . import models as M
from . import scale as SC
from . import validate as V
from .instance import build_instance

OUT = "outputs"
FOCAL = "vizag"


def _t(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def _stringify(obj):
    """JSON object keys must be strings; edges and arcs are tuples, so convert."""
    if isinstance(obj, dict):
        return {(k if isinstance(k, (str, int, float, bool, type(None))) else str(k)):
                _stringify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify(v) for v in obj]
    return obj


def _dump(summary: Dict[str, Any]) -> None:
    """Merge this process's keys into ``summary.json`` under an exclusive lock.

    Stages may be run concurrently -- two solves on two cores finish sooner than
    one after the other -- so a write must not discard the keys another stage
    has added since this process last read the file.  The lock serialises the
    read-modify-write and the rename makes the replacement atomic, so a reader
    never sees a half-written file.
    """
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "summary.json")
    lock = open(os.path.join(OUT, ".summary.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        disk: Dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    disk = json.load(fh)
            except json.JSONDecodeError:
                disk = {}
        disk.update(_stringify(summary))
        tmp = path + f".{os.getpid()}.tmp"
        with open(tmp, "w") as fh:
            json.dump(disk, fh, indent=2, default=str)
        os.replace(tmp, path)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _load() -> Dict[str, Any]:
    p = os.path.join(OUT, "summary.json")
    if os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {}


def run_validation(summary: Dict[str, Any], time_limit: float = 900.0) -> None:
    _t("validation")
    inst = build_instance(FOCAL, n_carriers=3)
    small = SC.sub_network(inst, 3)
    res = V.run_all_tests(inst, small, "F4", time_limit=time_limit)
    summary["validation"] = {
        k: {kk: vv for kk, vv in v.items() if kk in
            ("ok", "rel", "max_ratio", "checked", "designs", "sd_runtime",
             "enum_runtime", "rel_fixed", "rel_free", "theta_star", "first_best",
             "fixed", "free", "values")}
        for k, v in res.items()}
    summary["validation"]["all_pass"] = all(v.get("ok") for v in res.values())
    _dump(summary)


def run_main(summary: Dict[str, Any], time_limit: float = 900.0) -> None:
    _t("focal case: Visakhapatnam corridor")
    inst = build_instance(FOCAL, n_carriers=3)
    summary["instance"] = {"size": inst.size(), "meta": inst.meta,
                           "price": inst.price, "ef": inst.ef,
                           "Gavail": inst.Gavail, "wage": inst.wage,
                           "p_diesel": inst.p_diesel, "e_elec": inst.e_elec,
                           "f_diesel": inst.f_diesel, "psave": inst.psave,
                           "w_emis": inst.w_emis, "w_grid": inst.w_grid,
                           "theta_menu": inst.theta_menu, "sigma_menu": inst.sigma_menu,
                           "edges_km": {str(e): inst.dist[inst.arcs_of_edge[e][0]]
                                        for e in inst.edges}}

    instr = X.instrument_comparison(inst, time_limit=time_limit)
    summary["instruments"] = {k: {kk: vv for kk, vv in v.items()
                                  if kk in ("obj", "exp_emis", "exp_grid", "invest",
                                            "n_electrified", "theta", "sigma",
                                            "runtime", "y", "bays")}
                              for k, v in instr.items()}
    _dump(summary)

    summary["stochastic"] = X.stochastic_value(inst, "F4", time_limit=time_limit)
    _dump(summary)

    coll = X.collaboration(inst, "F4", time_limit=time_limit)
    summary["collaboration"] = {
        "gain": coll["main"]["gain"], "gain_pct": coll["main"]["gain_pct"],
        "standalone_total": coll["main"]["standalone_total"],
        "grand": coll["main"]["grand"], "shapley": coll["main"]["shapley"],
        "shapley_in_core": coll["main"]["shapley_in_core"],
        "least_core_eps": coll["main"]["least_core_eps"],
        "core_nonempty": coll["main"]["core_nonempty"],
        "decomposition": coll["main"]["decomposition"],
        "cost": {str(k): v for k, v in coll["main"]["cost"].items()},
    }
    _dump(summary)

    X.sensitivity(inst, "F4", time_limit=min(time_limit, 120.0))
    _dump(summary)


def run_frontier(summary: Dict[str, Any], time_limit: float = 300.0) -> None:
    _t("emissions frontier by instrument family")
    inst = build_instance(FOCAL, n_carriers=3)
    summary["frontier"] = {k: v for k, v in
                           X.emissions_frontier(inst, ("F0", "F2", "F4"),
                                                time_limit=time_limit).items()}
    _dump(summary)


def run_contingency(summary: Dict[str, Any], time_limit: float = 900.0) -> None:
    _t("value of state contingency")
    inst = build_instance(FOCAL, n_carriers=3)
    summary["contingency"] = X.state_contingency_value(inst, time_limit=time_limit)["rows"]
    _dump(summary)


def run_seeds(summary: Dict[str, Any], time_limit: float = 600.0) -> None:
    _t("carrier-split seed robustness")
    summary["collab_seeds"] = X.collaboration_seeds(FOCAL, time_limit=time_limit)
    _dump(summary)


def run_stability(summary: Dict[str, Any], time_limit: float = 600.0) -> None:
    _t("scenario stability")
    summary["scenario_stability"] = X.scenario_stability(FOCAL, time_limit=time_limit)["rows"]
    _dump(summary)


def run_extras(summary: Dict[str, Any], time_limit: float = 600.0) -> None:
    run_contingency(summary, time_limit)
    run_seeds(summary, time_limit)
    run_stability(summary, time_limit)


def run_cross(summary: Dict[str, Any], time_limit: float = 900.0) -> None:
    _t("cross-country study")
    summary["reversal"] = X.reversal_analysis()
    _dump(summary)
    cc = X.cross_country(time_limit=time_limit)
    summary["cross_country"] = {
        nm: {"country": d["instance"].country, "port": d["instance"].port,
             "first_best": d["centralized"]["obj"], "F0": d["F0"]["obj"],
             "F4": d["F4"]["obj"],
             "n_elec_F4": d["F4"]["n_electrified"], "n_edges": len(d["instance"].E),
             "emis_F0": d["F0"]["exp_emis"], "emis_F4": d["F4"]["exp_emis"]}
        for nm, d in cc.items()}
    _dump(summary)
    X.regime_matrix(time_limit=time_limit)
    _dump(summary)


def run_scale(summary: Dict[str, Any], time_limit: float = 600.0) -> None:
    _t("scalability study")
    r = X.scalability(time_limit=time_limit)
    summary["scalability"] = r["rows"]
    _dump(summary)


def run_figures(summary: Dict[str, Any]) -> None:
    _t("figures")
    paths = F.make_all(FOCAL)
    for p in paths:
        print("   wrote", p, flush=True)
    summary["figures"] = paths
    _dump(summary)


def main(argv) -> None:
    t0 = time.time()
    what = argv[1] if len(argv) > 1 else "all"
    tl = float(argv[2]) if len(argv) > 2 else 900.0
    summary = _load()
    summary.setdefault("generated", time.strftime("%Y-%m-%d %H:%M:%S"))
    if what in ("all", "validate"):
        run_validation(summary, tl)
    if what in ("all", "main"):
        run_main(summary, tl)
    if what in ("all", "frontier"):
        run_frontier(summary, min(tl, 900.0))
    if what in ("all", "extras"):
        run_extras(summary, min(tl, 900.0))
    if what == "contingency":
        run_contingency(summary, min(tl, 900.0))
    if what == "seeds":
        run_seeds(summary, min(tl, 600.0))
    if what == "stability":
        run_stability(summary, min(tl, 600.0))
    if what in ("all", "cross"):
        run_cross(summary, tl)
    if what in ("all", "scale"):
        run_scale(summary, min(tl, 600.0))
    if what in ("all", "figures"):
        run_figures(summary)
    summary["runtime_s"] = round(time.time() - t0, 1)
    _dump(summary)
    print(f"\ndone in {summary['runtime_s']:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv)
