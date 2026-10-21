"""Planted supply-chain scenarios with known ground truth.

Each scenario seeds dedicated trustledger_eval_<tag>_* databases via harness.py,
inserts a trigger case into platform.cases with status='open', and declares
its ground truth for attribution scoring.
"""
from dataclasses import dataclass, field
import hashlib
import random
from typing import Callable

import psycopg

from backend import db
from backend.seed import (
    BRAND,
    PRODUCTS,
    PARTNERS,
    SUPPLY,
    AGE_BANDS,
    GENDERS,
    BRAND_SCHEMA,
    PAYPAL_SCHEMA,
    PLATFORM_SCHEMA,
)

from evals import harness

# Scenarios use their own compact 12-week world (planted problems in weeks 7-12); harness.configure pins
# CURRENT_WEEK to match, independent of the demo seed's history length.
WEEKS = 12


@dataclass
class GroundTruth:
    is_problem: bool
    expected_store: str | None = None
    expected_distributor: str | None = None
    expected_reason: str | None = None
    week_range: tuple[int, int] | None = None


@dataclass
class Scenario:
    name: str
    title: str
    description: str
    trigger_case: dict
    ground_truth: GroundTruth
    builder: Callable[[str, int], None] = field(repr=False)

    def build(self, tag: str, seed: int = 42) -> None:
        self.builder(tag, seed)


def _store(pid: str) -> tuple:
    return next(p for p in PARTNERS if p[0] == pid)


def _seed_base_data(rng: random.Random, n_batches: int = 12, batch_size: int = 50, n_buyers: int = 200):
    """Seed clean baseline tables across brand, paypal_side, and platform."""
    for name in ("brand", "paypal_side", "platform"):
        db.ensure_database(name)

    # Brand DB
    brand_conn = psycopg.connect(db.url("brand"), autocommit=True)
    b = brand_conn.cursor()
    b.execute(BRAND_SCHEMA)
    b.executemany("INSERT INTO products VALUES (%s,%s,%s,%s)", PRODUCTS)
    b.executemany("INSERT INTO partners VALUES (%s,%s,%s,%s,%s)", PARTNERS)

    serials_by_store: dict[str, list[tuple[str, str, str]]] = {s: [] for v in SUPPLY.values() for s in v}
    d1_serials: list[tuple[str, str, str]] = []
    d2_serials: list[tuple[str, str, str]] = []
    counter = 100000

    for i in range(n_batches):
        dist = "dist_1" if i % 2 == 0 else "dist_2"
        sku = PRODUCTS[i % len(PRODUCTS)][0]
        store = SUPPLY[dist][(i // 2) % len(SUPPLY[dist])]
        week = rng.randint(1, 3)
        batch_id = f"B{i:03d}"
        b.execute("INSERT INTO batches VALUES (%s,%s,%s,%s)", (batch_id, sku, dist, week))
        b.execute("INSERT INTO channel_shipments VALUES (%s,%s,%s,%s)", (batch_id, dist, store, week + 1))

        rows = []
        for _ in range(batch_size):
            counter += 1
            serial = f"NMB{counter}"
            rows.append((serial, sku, batch_id))
            serials_by_store[store].append((serial, sku, batch_id))
            if dist == "dist_1":
                d1_serials.append((serial, sku, batch_id))
            else:
                d2_serials.append((serial, sku, batch_id))
        b.executemany("INSERT INTO serials (serial, sku, batch_id) VALUES (%s,%s,%s)", rows)

    # PayPal DB
    paypal_conn = psycopg.connect(db.url("paypal_side"), autocommit=True)
    p = paypal_conn.cursor()
    p.execute(PAYPAL_SCHEMA)
    stores = [x for x in PARTNERS if x[1] == "store"]
    p.executemany("INSERT INTO catalog_stores VALUES (%s,%s,%s,%s)", [(s[0], BRAND, s[3], s[4]) for s in stores])
    p.executemany("INSERT INTO catalog_skus VALUES (%s,%s)", [(x[0], BRAND) for x in PRODUCTS])

    buyers = []
    for i in range(n_buyers):
        key = hashlib.sha256(f"buyer-{i}".encode()).hexdigest()[:16]
        buyers.append((key, rng.choice(AGE_BANDS), rng.choice(GENDERS)))
    price = {x[0]: x[3] for x in PRODUCTS}

    txns, sold = [], []

    def sell(store_id: str, serial: str, sku: str, week: int) -> None:
        tid = f"T{len(txns):06d}"
        key, age, gender = rng.choice(buyers)
        s = _store(store_id)
        txns.append((tid, f"SIM-{tid}", BRAND, store_id, sku, price[sku], s[3], s[4], week, key, age, gender, "simulated"))
        sold.append((store_id, week, f"SIM-{tid}", serial))

    # Clean in-channel sales
    for store_id, pool in serials_by_store.items():
        n_sell = min(len(pool), rng.randint(20, 35))
        for _ in range(n_sell):
            serial, sku, _ = pool.pop(0)
            week = rng.randint(4, 9)
            sell(store_id, serial, sku, week)

    with p.copy("COPY transactions (txn_id, order_id, brand_id, store_id, sku, amount, region, city, week, "
                "payer_key, age_band, gender, source) FROM STDIN") as cp:
        for t in txns:
            cp.write_row(t)

    b.execute("CREATE TEMP TABLE sold_tmp (store_id TEXT, week INT, order_id TEXT, serial TEXT)")
    with b.copy("COPY sold_tmp FROM STDIN") as cp:
        for row in sold:
            cp.write_row(row)
    b.execute("UPDATE serials s SET sold_store_id=t.store_id, sold_week=t.week, sold_order_id=t.order_id "
              "FROM sold_tmp t WHERE s.serial=t.serial")

    # Platform DB
    with db.connect("platform") as pl:
        pl.execute(PLATFORM_SCHEMA)
        pl.cursor().executemany("INSERT INTO stores VALUES (%s,%s,%s,%s,%s)",
                                [(s[0], s[2], s[3], s[4], BRAND) for s in stores])

    return brand_conn, paypal_conn, d1_serials, d2_serials, serials_by_store, sell


def _insert_trigger_case(case_id: str, store_id: str, sku: str, serial: str, reason_code: str):
    """Insert open case into platform DB for the worker to claim."""
    vid = f"ver_{case_id}"
    with db.connect("platform") as pl:
        pl.execute(
            "INSERT INTO cases (case_id, brand_id, verification_id, store_id, sku, serial, reason_code, status, failure_count, skus) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'open', 1, %s)",
            (case_id, BRAND, vid, store_id, sku, serial, reason_code, [sku]),
        )
        pl.execute(
            "INSERT INTO case_failures (verification_id, case_id, serial, sku) VALUES (%s, %s, %s, %s)",
            (vid, case_id, serial, sku),
        )



# ---------------------------------------------------------------- Scenario Builders

def build_leaky_distributor(tag: str, seed: int = 42):
    """Distributor 1 serials leak to Store C (normally supplied by Dist 2) from week 8 onward."""
    harness.configure(tag, mock=True)
    rng = random.Random(seed)
    brand_conn, paypal_conn, d1_serials, d2_serials, serials_by_store, sell = _seed_base_data(rng)
    b = brand_conn.cursor()

    # Leak dist_1 serials to store_c
    target_store = "store_c"
    trigger_serial, trigger_sku, _ = d1_serials[0]
    failures = []
    for i, (serial, sku, _) in enumerate(d1_serials[:15]):
        week = rng.randint(8, 12)
        failures.append((f"ver_leak_{i}", serial, sku, target_store, "NOT_VERIFIED", "NOT_IN_CHANNEL", week))

    b.executemany(
        "INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        failures,
    )
    brand_conn.close()
    paypal_conn.close()

    _insert_trigger_case("case_leaky_dist", target_store, trigger_sku, trigger_serial, "NOT_IN_CHANNEL")


def build_cloned_serial(tag: str, seed: int = 42):
    """Genuine serials from Store A (Dist 1) are re-scanned as clones at Store B in weeks 9-12."""
    harness.configure(tag, mock=True)
    rng = random.Random(seed)
    brand_conn, paypal_conn, d1_serials, d2_serials, serials_by_store, sell = _seed_base_data(rng)
    b = brand_conn.cursor()

    target_store = "store_b"
    # Take serials that were sold at store_a in week 5
    with db.connect("brand") as bc:
        sold_store_a = bc.execute(
            "SELECT serial, sku FROM serials WHERE sold_store_id='store_a' LIMIT 10"
        ).fetchall()

    failures = []
    trigger_serial = sold_store_a[0]["serial"]
    trigger_sku = sold_store_a[0]["sku"]

    for i, row in enumerate(sold_store_a):
        for rep in range(2):
            week = rng.randint(9, 12)
            failures.append((f"ver_clone_{i}_{rep}", row["serial"], row["sku"], target_store,
                             "NOT_VERIFIED", "ALREADY_SOLD", week))

    b.executemany(
        "INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        failures,
    )
    brand_conn.close()
    paypal_conn.close()

    _insert_trigger_case("case_cloned_serial", target_store, trigger_sku, trigger_serial, "ALREADY_SOLD")


def build_rogue_store(tag: str, seed: int = 42):
    """Store B has an influx of counterfeit serials unknown to the brand."""
    harness.configure(tag, mock=True)
    rng = random.Random(seed)
    brand_conn, paypal_conn, d1_serials, d2_serials, serials_by_store, sell = _seed_base_data(rng)
    b = brand_conn.cursor()

    target_store = "store_b"
    trigger_sku = PRODUCTS[0][0]
    trigger_serial = "FAKE-SERIAL-001"

    failures = []
    for i in range(25):
        serial = f"FAKE-SERIAL-{i:03d}"
        week = rng.randint(7, 12)
        failures.append((f"ver_rogue_{i}", serial, trigger_sku, target_store,
                         "NOT_VERIFIED", "UNKNOWN", week))

    b.executemany(
        "INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        failures,
    )
    brand_conn.close()
    paypal_conn.close()

    _insert_trigger_case("case_rogue_store", target_store, trigger_sku, trigger_serial, "UNKNOWN")


def build_clean(tag: str, seed: int = 42):
    """Clean control baseline: normal noise with one isolated typo, no supply-chain failure."""
    harness.configure(tag, mock=True)
    rng = random.Random(seed)
    brand_conn, paypal_conn, d1_serials, d2_serials, serials_by_store, sell = _seed_base_data(rng)
    b = brand_conn.cursor()

    # Just 1 isolated typo failure at store_a
    trigger_sku = PRODUCTS[0][0]
    trigger_serial = "NMB-TYPO-999"
    b.execute(
        "INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        ("ver_clean_single", trigger_serial, trigger_sku, "store_a", "NOT_VERIFIED", "UNKNOWN", 8),
    )
    brand_conn.close()
    paypal_conn.close()

    _insert_trigger_case("case_clean_control", "store_a", trigger_sku, trigger_serial, "UNKNOWN")


# ---------------------------------------------------------------- Registry

SCENARIOS: dict[str, Scenario] = {
    "leaky_distributor": Scenario(
        name="leaky_distributor",
        title="Leaky Distributor Diversion",
        description="Distributor 1 serials appear at Store C (normally supplied by Dist 2) starting week 8.",
        trigger_case={"case_id": "case_leaky_dist", "store_id": "store_c", "reason_code": "NOT_IN_CHANNEL"},
        ground_truth=GroundTruth(
            is_problem=True,
            expected_store="store_c",
            expected_distributor="dist_1",
            expected_reason="NOT_IN_CHANNEL",
            week_range=(8, 12),
        ),
        builder=build_leaky_distributor,
    ),
    "cloned_serial": Scenario(
        name="cloned_serial",
        title="Cloned / Resold Genuine Serials",
        description="Genuine serials sold at Store A reappear as clone verification attempts at Store B.",
        trigger_case={"case_id": "case_cloned_serial", "store_id": "store_b", "reason_code": "ALREADY_SOLD"},
        ground_truth=GroundTruth(
            is_problem=True,
            expected_store="store_b",
            expected_distributor=None,  # a clone copies a genuine serial; its original distributor isn't the leak
            expected_reason="ALREADY_SOLD",
            week_range=(9, 12),
        ),
        builder=build_cloned_serial,
    ),
    "rogue_store": Scenario(
        name="rogue_store",
        title="Rogue Store Counterfeiting",
        description="Store B has a cluster of counterfeit serials unrecognised by the brand.",
        trigger_case={"case_id": "case_rogue_store", "store_id": "store_b", "reason_code": "UNKNOWN"},
        ground_truth=GroundTruth(
            is_problem=True,
            expected_store="store_b",
            expected_distributor=None,
            expected_reason="UNKNOWN",
            week_range=(7, 12),
        ),
        builder=build_rogue_store,
    ),
    "clean": Scenario(
        name="clean",
        title="Clean Control Baseline",
        description="Normal noise with one isolated unverified scan. The agent should NOT blame anyone confidently.",
        trigger_case={"case_id": "case_clean_control", "store_id": "store_a", "reason_code": "UNKNOWN"},
        ground_truth=GroundTruth(
            is_problem=False,
            expected_store=None,
            expected_distributor=None,
            expected_reason=None,
            week_range=None,
        ),
        builder=build_clean,
    ),
}
