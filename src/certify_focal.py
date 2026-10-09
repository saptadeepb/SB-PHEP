"""Re-solve the focal corridor's restricted instruments with a longer time limit.

The instrument comparison runs every family under one time limit.  On the focal
corridor F1--F3 can stop on that limit; this script re-solves them with a longer
one and, where a family now certifies (or improves), updates its row of
``instruments_<focal>.csv`` and records the run in ``instruments_<focal>_certify.csv``.
Usage: python3 -m src.certify_focal [time_limit_seconds]
"""
from __future__ import annotations

import csv
import os
import sys

from . import models as M
from .corridors import FOCAL
from .experiments import TAB, _fmt, _log
from .instance import build_instance


def main(tl: float) -> None:
    inst = build_instance(FOCAL, n_carriers=3)
    path = os.path.join(TAB, f"instruments_{FOCAL}.csv")
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    head, body = rows[0], rows[1:]
    cen = float(body[0][1])
    log = []
    for fam in ("F1", "F2", "F3"):
        row = next(r for r in body if r[0] == fam)
        if row[-1] == "optimal":
            continue
        r = M.bilevel_sd(inst, fam, time_limit=tl)
        _log(f"   certify {fam}: {r.get('obj')} ({r.get('status')}, gap {r.get('mip_gap')})")
        log.append([fam, tl, r.get("obj"), r.get("mip_gap"), r.get("status"), r.get("runtime")])
        if r.get("obj") is not None and (r.get("status") == "optimal"
                                          or r["obj"] < float(row[1]) - 1e-6
                                          or (r.get("mip_gap") or 1.0) < float(row[11] or 1.0)):
            gap = r["obj"] - cen
            if abs(gap) <= 1e-7 * max(1.0, abs(cen)):
                gap = 0.0
            new = [fam, r["obj"], gap, 100.0 * gap / cen, r["exp_emis"], r["exp_grid"],
                   r["n_electrified"], sum(r["bays"].values()), _fmt(r["theta"]),
                   _fmt(r["sigma"]), r["runtime"], r.get("mip_gap"), r.get("status")]
            body[body.index(row)] = new
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(body)
    with open(os.path.join(TAB, f"instruments_{FOCAL}_certify.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "time_limit_s", "obj", "certified_mip_gap", "status", "runtime_s"])
        w.writerows(log)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 3600.0)
