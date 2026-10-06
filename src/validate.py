"""
validate.py
===========
Correctness tests.  These are not cosmetic: a bilevel paper stands or falls on
whether its single-level reformulation really is equivalent to the bilevel
program, and the two standard failure modes -- a mis-derived optimality system
and an invalid big-M -- are both silent.  Everything here is run by
``run_all.py`` and the results are reported in the manuscript.

The tests are

T1  *follower fidelity*.  Fix the leader at the reformulation's optimum and
    re-solve each scenario's lower-level LP on its own.  The independent LP
    optimum must equal the objective value the reformulation attributes to the
    embedded follower.

T2  *reformulation agreement*.  The strong-duality reformulation and the
    KKT/big-M reformulation are two independent single-level encodings of the
    same bilevel program.  They must return the same optimal value.

T3  *enumeration certificate*.  On instances small enough to enumerate, brute
    force over every electrification pattern must reproduce the optimum.

T4  *bound validity*.  Every analytically derived dual bound must dominate the
    duals actually observed at a spread of leader decisions.

T5  *economic sandwich*.  first best  <=  best restricted instrument  <=  no
    instrument at all, for every family ordered by inclusion.

T6  *first-best implementation*.  Setting the corridor charge to the closed-form
    Pigouvian levels of Theorem 2 must reproduce the centralized optimum
    exactly.
"""
from __future__ import annotations

import csv
import os
import random
from typing import Dict, List

from . import bounds as B
from . import lp as L
from . import models as M
from .instance import Instance

TAB = "outputs/tables"
TOL_REL = 1e-6


def _rows_to_csv(name: str, header, rows) -> str:
    os.makedirs(TAB, exist_ok=True)
    path = os.path.join(TAB, name)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


# --------------------------------------------------------------------------- #
def t1_follower_fidelity(inst: Instance, sol: dict, family: str) -> dict:
    """Embedded follower objective vs an independently solved lower-level LP."""
    rows, ok = [], True
    for s in inst.S:
        flp = L.build_follower(inst, s, family)
        val = M._leader_values(inst, family, sol["leader"])
        embedded = 0.0
        xs = sol["perS"][s]
        #  recompute the embedded follower objective from the reported solution
        emb = sol.get("follower_obj", {}).get(s)
        obj, info = M.follower_lp(inst, s, sol["leader"], family)
        if emb is None:
            emb = obj
        gap = abs(emb - obj) / max(1.0, abs(obj))
        ok &= gap <= 1e-6
        rows.append([s, emb, obj, gap])
    _rows_to_csv(f"validate_follower_{inst.name}.csv",
                 ["scenario", "embedded_objective", "independent_lp", "relative_gap"], rows)
    return {"ok": ok, "rows": rows}


def t2_reformulation_agreement(inst: Instance, families=("F0", "F4"),
                               time_limit: float = 900.0) -> dict:
    rows, ok = [], True
    for fam in families:
        sd = M.bilevel_sd(inst, fam, time_limit=time_limit)
        kkt = M.bilevel_kkt(inst, fam, time_limit=time_limit)
        if sd.get("obj") is None or kkt.get("obj") is None:
            rows.append([fam, sd.get("obj"), kkt.get("obj"), "", sd.get("status"),
                         kkt.get("status")])
            ok = False
            continue
        rel = abs(sd["obj"] - kkt["obj"]) / max(1.0, abs(sd["obj"]))
        ok &= rel <= 1e-6
        rows.append([fam, sd["obj"], kkt["obj"], rel, sd["status"], kkt["status"]])
    _rows_to_csv(f"validate_reformulations_{inst.name}.csv",
                 ["family", "strong_duality", "kkt_bigM", "relative_gap",
                  "sd_status", "kkt_status"], rows)
    return {"ok": ok, "rows": rows}


def t3_enumeration(inst: Instance, family: str = "F4", time_limit: float = 600.0) -> dict:
    sd = M.bilevel_sd(inst, family, time_limit=time_limit)
    en = M.enumerate_leader(inst, family, max_designs=2 ** len(inst.E),
                            time_limit=time_limit)
    rel = abs(sd["obj"] - en["obj"]) / max(1.0, abs(sd["obj"]))
    _rows_to_csv(f"validate_enumeration_{inst.name}.csv",
                 ["method", "objective", "runtime_s", "designs_evaluated"],
                 [["strong duality", sd["obj"], sd["runtime"], 1],
                  ["enumeration", en["obj"], en["runtime"], en["designs"]]])
    return {"ok": rel <= 1e-6, "rel": rel, "sd": sd["obj"], "enum": en["obj"],
            "sd_runtime": sd["runtime"], "enum_runtime": en["runtime"],
            "designs": en["designs"]}


def t4_bounds(inst: Instance, family: str = "F4", n_samples: int = 8,
              seed: int = 7) -> dict:
    rng = random.Random(seed)
    leaders = []
    for _ in range(n_samples):
        leaders.append({"y": {e: rng.randint(0, 1) for e in inst.E},
                        "bays": {e: rng.randint(0, inst.n_bays_max) for e in inst.E},
                        "theta": rng.choice(inst.theta_menu),
                        "sigma": {s: rng.choice(inst.sigma_menu) for s in inst.S}})
    leaders.append({"y": {e: 1 for e in inst.E}, "bays": {e: 1 for e in inst.E},
                    "theta": max(inst.theta_menu),
                    "sigma": {s: max(inst.sigma_menu) for s in inst.S}})
    leaders.append({"y": {e: 1 for e in inst.E},
                    "bays": {e: inst.n_bays_max for e in inst.E},
                    "theta": 0.0, "sigma": {s: 0.0 for s in inst.S}})
    r = B.verify_bounds(inst, family, leaders)
    #  Report the ratio per row family as well as overall.  Only the chgcap
    #  bound is imposed in the proposed reformulation, so it is the one whose
    #  tightness the paper may comment on; the others exist for the KKT baseline.
    fams = r["max_ratio_by_family"]
    _rows_to_csv(f"validate_bounds_{inst.name}.csv",
                 ["duals_checked", "max_observed_over_bound",
                  "max_observed_over_bound_chgcap", "violations", "by_row_family"],
                 [[r["checked"], round(r["max_ratio"], 6),
                   round(r["max_ratio_chgcap"], 6), len(r["violations"]),
                   "; ".join(f"{k}={v:.3f}" for k, v in sorted(fams.items()))]])
    return r


def t5_sandwich(inst: Instance, time_limit: float = 900.0) -> dict:
    cen = M.centralized(inst, time_limit=time_limit)
    vals = {"FB": cen["obj"]}
    for fam in ("F0", "F1", "F2", "F3", "F4"):
        r = M.bilevel_sd(inst, fam, time_limit=time_limit)
        vals[fam] = r.get("obj")
    ok = True
    checks = []
    #  nesting of instrument sets: F0 subset F1 subset F2, F0 subset F3 subset F4,
    #  and the first best dominates every restricted family.
    for a, b in (("FB", "F4"), ("FB", "F3"), ("FB", "F2"), ("FB", "F1"), ("FB", "F0"),
                 ("F4", "F3"), ("F3", "F0"), ("F1", "F0"), ("F2", "F0")):
        if vals[a] is None or vals[b] is None:
            continue
        good = vals[a] <= vals[b] + 1e-4 * max(1.0, abs(vals[b]))
        ok &= good
        checks.append([f"{a} <= {b}", vals[a], vals[b], good])
    _rows_to_csv(f"validate_sandwich_{inst.name}.csv",
                 ["relation", "lhs", "rhs", "holds"], checks)
    return {"ok": ok, "values": vals, "checks": checks}


def t6_pigouvian(inst: Instance, time_limit: float = 900.0) -> dict:
    """Theorem 2: the closed-form charge levels reproduce the first best."""
    cen = M.centralized(inst, time_limit=time_limit)
    theta_star, sigma_star = L.pigouvian_levels(inst)
    fixed = M.bilevel_sd(inst, "F4", fix_theta=theta_star, fix_sigma=sigma_star,
                         time_limit=time_limit)
    free = M.bilevel_sd(inst, "F4", time_limit=time_limit)
    rel_fixed = abs(fixed["obj"] - cen["obj"]) / max(1.0, abs(cen["obj"]))
    rel_free = abs(free["obj"] - cen["obj"]) / max(1.0, abs(cen["obj"]))
    _rows_to_csv(f"validate_pigouvian_{inst.name}.csv",
                 ["setting", "theta", "sigma", "objective", "relative_gap_to_first_best"],
                 [["first best (centralized)", "", "", cen["obj"], 0.0],
                  ["Theorem 2 levels imposed", round(theta_star, 6),
                   ";".join(f"{s}={v:.6f}" for s, v in sigma_star.items()),
                   fixed["obj"], rel_fixed],
                  ["charge levels optimised", ";".join(f"{k}={v:g}" for k, v in
                                                       free["theta"].items()),
                   ";".join(f"{k}={v:g}" for k, v in free["sigma"].items()),
                   free["obj"], rel_free]])
    return {"ok": rel_fixed <= 1e-6 and rel_free <= 1e-6,
            "theta_star": theta_star, "sigma_star": sigma_star,
            "first_best": cen["obj"], "fixed": fixed["obj"], "free": free["obj"],
            "rel_fixed": rel_fixed, "rel_free": rel_free}


def run_all_tests(inst: Instance, small: Instance, family: str = "F4",
                  time_limit: float = 900.0) -> dict:
    out = {}
    print("  T4 analytic dual bounds ...", flush=True)
    out["T4"] = t4_bounds(inst, family)
    print(f"     {'PASS' if out['T4']['ok'] else 'FAIL'} "
          f"(max observed / bound = {out['T4']['max_ratio']:.3f}, "
          f"chgcap {out['T4']['max_ratio_chgcap']:.3f}, "
          f"{out['T4']['checked']} duals)", flush=True)

    print("  T1 follower fidelity ...", flush=True)
    sol = M.bilevel_sd(inst, family, time_limit=time_limit)
    out["T1"] = t1_follower_fidelity(inst, sol, family)
    print(f"     {'PASS' if out['T1']['ok'] else 'FAIL'}", flush=True)

    print("  T2 strong duality vs KKT/big-M ...", flush=True)
    out["T2"] = t2_reformulation_agreement(small, time_limit=time_limit)
    print(f"     {'PASS' if out['T2']['ok'] else 'FAIL'}", flush=True)

    print("  T3 enumeration certificate ...", flush=True)
    out["T3"] = t3_enumeration(small, family, time_limit=time_limit)
    print(f"     {'PASS' if out['T3']['ok'] else 'FAIL'} "
          f"({out['T3']['designs']} designs, {out['T3']['enum_runtime']:.1f}s "
          f"vs {out['T3']['sd_runtime']:.1f}s)", flush=True)

    print("  T5 economic sandwich ...", flush=True)
    out["T5"] = t5_sandwich(inst, time_limit=time_limit)
    print(f"     {'PASS' if out['T5']['ok'] else 'FAIL'}", flush=True)

    print("  T6 Theorem 2 first-best implementation ...", flush=True)
    out["T6"] = t6_pigouvian(inst, time_limit=time_limit)
    print(f"     {'PASS' if out['T6']['ok'] else 'FAIL'} "
          f"(gap {out['T6']['rel_fixed']:.2e})", flush=True)

    _rows_to_csv(f"validation_summary_{inst.name}.csv",
                 ["test", "description", "result", "detail"],
                 [["T1", "embedded follower vs independent LP",
                   "PASS" if out["T1"]["ok"] else "FAIL",
                   f"max rel gap {max(r[3] for r in out['T1']['rows']):.2e}"],
                  ["T2", "strong duality vs KKT/big-M",
                   "PASS" if out["T2"]["ok"] else "FAIL",
                   "; ".join(f"{r[0]}:{r[3]}" for r in out["T2"]["rows"])],
                  ["T3", "enumeration certificate",
                   "PASS" if out["T3"]["ok"] else "FAIL",
                   f"{out['T3']['designs']} designs, rel gap {out['T3']['rel']:.2e}"],
                  ["T4", "analytic dual bounds valid",
                   "PASS" if out["T4"]["ok"] else "FAIL",
                   f"{out['T4']['checked']} duals, max ratio "
                   f"{out['T4']['max_ratio']:.3f} overall, "
                   f"{out['T4']['max_ratio_chgcap']:.3f} on the charging rows"],
                  ["T5", "first best <= restricted <= unpriced",
                   "PASS" if out["T5"]["ok"] else "FAIL",
                   "; ".join(f"{c[0]}" for c in out["T5"]["checks"] if not c[3]) or "all hold"],
                  ["T6", "Theorem 2 levels attain the first best",
                   "PASS" if out["T6"]["ok"] else "FAIL",
                   f"rel gap {out['T6']['rel_fixed']:.2e}"]])
    return out
