"""Fixed-seed demo data. Everything here is fictional: brand, stores, cities and buyers.

    python -m backend.seed            # full size
    python -m backend.seed --small    # quick version for tests

Writes the brand, paypal_side and platform Postgres databases (tables are dropped and recreated).

History: weeks 1..WEEKS (week 1 starts 4 Jan 2026; WEEKS = CURRENT_WEEK, mid-October). Batches restock every
store all year; each store sells most of a batch in the weeks after it arrives, so unsold stock is recent.

Planted scenarios (all recent, relative to WEEKS):
  * Demo serial X123: in the latest Distributor 1 -> Store A batch, not yet sold.
  * Diversion: Distributor 1 stock (from batches 6-12 weeks old) sold at Store C, which Distributor 1 never
    supplied, during the last 6 weeks.
  * Clone attempts: serials from Distributor 1 batches tried at Store B in the last 4 weeks.
  * A normal demand spike at Store D four weeks ago (should NOT be flagged).
"""
import argparse
import hashlib
import random
import psycopg

from backend import config, db

BRAND = "nimbus"
PRODUCTS = [
    ("NMB-P8-128", "Nimbus P8 128GB", "phone", 899.0),
    ("NMB-P8-256", "Nimbus P8 256GB", "phone", 999.0),
    ("NMB-A5-64", "Nimbus A5 64GB", "phone", 399.0),
]
PARTNERS = [
    ("dist_1", "distributor", "Northline Distribution", "West", "Riverton"),
    ("dist_2", "distributor", "Crestway Supply", "Central", "Lakeside"),
    ("store_a", "store", "Store A", "West", "Riverton"),
    ("store_b", "store", "Store B", "Central", "Lakeside"),
    ("store_c", "store", "Store C", "Central", "Maple Falls"),
    ("store_d", "store", "Store D", "East", "Hillview"),
    ("store_e", "store", "Store E", "East", "Port Ardent"),
    ("store_f", "store", "Store F", "West", "Cedar Bay"),
]
# Which distributor supplies which stores.
SUPPLY = {"dist_1": ["store_a", "store_d", "store_f"], "dist_2": ["store_b", "store_c", "store_e"]}
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["female", "male", "other"]
DEMO_SERIAL = "X123"

BRAND_SCHEMA = """
DROP TABLE IF EXISTS products, partners, batches, channel_shipments, serials, verification_log;
CREATE TABLE products (sku TEXT PRIMARY KEY, model TEXT, category TEXT, msrp DOUBLE PRECISION);
CREATE TABLE partners (partner_id TEXT PRIMARY KEY, type TEXT, name TEXT, region TEXT, city TEXT);
CREATE TABLE batches (batch_id TEXT PRIMARY KEY, sku TEXT, distributor_id TEXT, shipped_week INT);
CREATE TABLE channel_shipments (batch_id TEXT, distributor_id TEXT, store_id TEXT, week INT);
CREATE INDEX ON channel_shipments (batch_id);
CREATE TABLE serials (serial TEXT PRIMARY KEY, sku TEXT, batch_id TEXT,
                      sold_store_id TEXT, sold_week INT, sold_order_id TEXT);
CREATE TABLE verification_log (verification_id TEXT PRIMARY KEY, serial TEXT, sku TEXT, store_id TEXT,
                      result TEXT, reason_code TEXT, week INT, at TIMESTAMPTZ NOT NULL DEFAULT now());
"""

PAYPAL_SCHEMA = """
DROP TABLE IF EXISTS catalog_stores, catalog_skus, transactions;
CREATE TABLE catalog_stores (store_id TEXT PRIMARY KEY, brand_id TEXT, region TEXT, city TEXT);
CREATE TABLE catalog_skus (sku TEXT PRIMARY KEY, brand_id TEXT);
CREATE TABLE transactions (txn_id TEXT PRIMARY KEY, order_id TEXT, brand_id TEXT, store_id TEXT,
    sku TEXT, amount DOUBLE PRECISION, region TEXT, city TEXT, week INT, payer_key TEXT,
    age_band TEXT, gender TEXT, source TEXT);
CREATE INDEX ON transactions (brand_id, week);
DROP TABLE IF EXISTS privacy_ledger, query_cache, meta;
-- Budget per brand for this dataset. Reseeding is a labelled "dataset reset"; nothing resets it by date.
CREATE TABLE privacy_ledger (brand_id TEXT PRIMARY KEY, rho_spent DOUBLE PRECISION NOT NULL DEFAULT 0);
-- Identical queries on unchanged data return the stored release at no cost (defeats averaging).
CREATE TABLE query_cache (cache_key TEXT PRIMARY KEY, response JSONB NOT NULL,
                          created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO meta VALUES ('data_version', '1');
"""

PLATFORM_SCHEMA = """
DROP TABLE IF EXISTS stores, checkouts, cases, case_steps, case_failures;
CREATE TABLE stores (store_id TEXT PRIMARY KEY, name TEXT, region TEXT, city TEXT, brand_id TEXT);
CREATE TABLE checkouts (checkout_id TEXT PRIMARY KEY, store_id TEXT, serial TEXT, sku TEXT,
    amount DOUBLE PRECISION, verification_id TEXT, paypal_order_id TEXT, status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE cases (case_id TEXT PRIMARY KEY, brand_id TEXT, verification_id TEXT, store_id TEXT,
    sku TEXT, serial TEXT, reason_code TEXT, status TEXT, summary TEXT, confidence TEXT,
    failure_count INT NOT NULL DEFAULT 1, skus TEXT[] NOT NULL DEFAULT '{}',
    run_count INT NOT NULL DEFAULT 0, run_failure_count INT NOT NULL DEFAULT 0, run_skus TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE case_failures (verification_id TEXT PRIMARY KEY, case_id TEXT, serial TEXT, sku TEXT,
    at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE case_steps (step_id TEXT PRIMARY KEY, case_id TEXT, n INT, kind TEXT, payload JSONB,
    at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (case_id, n));
"""


def _store(pid: str) -> tuple:
    return next(p for p in PARTNERS if p[0] == pid)


def build(small: bool = False, seed: int = 42) -> None:
    rng = random.Random(seed)
    weeks = config.current_week()  # the demo's "now"; history covers weeks 1..weeks
    n_batches = 12 if small else 84
    batch_size = 70 if small else 250
    n_diverted = 60 if small else 800   # dist_1 units sold at store_c
    n_buyers = 600 if small else 6000

    for name in ("brand", "paypal_side", "platform"):
        db.ensure_database(name)

    # ---------------- brand side ----------------
    brand_conn = psycopg.connect(db.url("brand"), autocommit=True)
    b = brand_conn.cursor()
    b.execute(BRAND_SCHEMA)
    b.executemany("INSERT INTO products VALUES (%s,%s,%s,%s)", PRODUCTS)
    b.executemany("INSERT INTO partners VALUES (%s,%s,%s,%s,%s)", PARTNERS)

    # Stock delivered to each store: (serial, sku, arrival_week).
    stock: dict[str, list] = {s: [] for v in SUPPLY.values() for s in v}
    diverted: list[tuple[str, str]] = []   # dist_1 serials that end up at store_c
    d1_serials: list[tuple[str, str]] = []
    demo_batch = None
    counter = 100000
    for i in range(n_batches):
        dist = "dist_1" if i % 2 == 0 else "dist_2"
        sku = PRODUCTS[i % len(PRODUCTS)][0]
        store = SUPPLY[dist][(i // 2) % len(SUPPLY[dist])]
        week = 1 + (i * (weeks - 4)) // n_batches          # restocks spread over the year
        arrival = week + 1
        batch_id = f"B{i:03d}"
        b.execute("INSERT INTO batches VALUES (%s,%s,%s,%s)", (batch_id, sku, dist, week))
        b.execute("INSERT INTO channel_shipments VALUES (%s,%s,%s,%s)", (batch_id, dist, store, arrival))
        # Part of some dist_1 batches leaks to store_c (diversion), but only from batches 6-12 weeks old.
        leak = dist == "dist_1" and weeks - 12 <= arrival <= weeks - 6
        rows = []
        for _ in range(batch_size):
            counter += 1
            serial = f"NMB{counter}"
            rows.append((serial, sku, batch_id))
            if dist == "dist_1":
                d1_serials.append((serial, sku))
            if leak and rng.random() < 0.35:
                diverted.append((serial, sku))
            else:
                stock[store].append((serial, sku, arrival))
        b.executemany("INSERT INTO serials (serial, sku, batch_id) VALUES (%s,%s,%s)", rows)
        if dist == "dist_1" and store == "store_a" and sku == "NMB-P8-128":
            demo_batch = batch_id

    # Demo serial: the latest Distributor 1 -> Store A batch of the P8 128GB.
    b.execute("INSERT INTO serials (serial, sku, batch_id) VALUES (%s,%s,%s)", (DEMO_SERIAL, "NMB-P8-128", demo_batch))

    # ---------------- PayPal side ----------------
    paypal_conn = psycopg.connect(db.url("paypal_side"), autocommit=True)
    p = paypal_conn.cursor()
    p.execute(PAYPAL_SCHEMA)
    stores = [x for x in PARTNERS if x[1] == "store"]
    p.executemany("INSERT INTO catalog_stores VALUES (%s,%s,%s,%s)", [(s[0], BRAND, s[3], s[4]) for s in stores])
    p.executemany("INSERT INTO catalog_skus VALUES (%s,%s)", [(x[0], BRAND) for x in PRODUCTS])

    buyers = []
    for i in range(n_buyers):
        key = hashlib.sha256(f"buyer-{seed}-{i}".encode()).hexdigest()[:16]
        buyers.append((key, rng.choice(AGE_BANDS), rng.choice(GENDERS)))
    price = {x[0]: x[3] for x in PRODUCTS}

    txns, sold = [], []

    def sell(store_id: str, serial: str, sku: str, week: int) -> None:
        tid = f"T{len(txns):06d}"
        key, age, gender = rng.choice(buyers)
        s = _store(store_id)
        txns.append((tid, f"SIM-{tid}", BRAND, store_id, sku, price[sku], s[3], s[4], week, key, age, gender, "simulated"))
        sold.append((store_id, week, f"SIM-{tid}", serial))

    # Normal sales: each store sells ~85% of every batch it receives, over the 0-5 weeks after it arrives,
    # so weekly sales follow deliveries right up to "now" (units that would sell after now are still on the shelf).
    spike = weeks - 4
    for store_id, pool in stock.items():
        for serial, sku, arrival in pool:
            if rng.random() > 0.85:
                continue
            week = arrival + rng.randint(0, 5)
            if store_id == "store_d" and arrival <= spike <= arrival + 5 and rng.random() < 0.25:
                week = spike  # normal seasonal spike
            if week <= weeks:
                sell(store_id, serial, sku, week)

    # Diversion: dist_1 stock appears at store_c (supplied only by dist_2) in the last six weeks.
    for serial, sku in diverted[:n_diverted]:
        sell("store_c", serial, sku, rng.randint(weeks - 5, weeks))

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

    # Clone attempts at store_b using dist_1 serials (already-sold or out-of-channel).
    clone_rows = []
    for i, (serial, sku) in enumerate(rng.sample(d1_serials, min(40, len(d1_serials)))):
        reason = "ALREADY_SOLD" if i % 3 == 0 else "NOT_IN_CHANNEL"
        clone_rows.append((f"ver_seed_{i:03d}", serial, sku, "store_b", "NOT_VERIFIED", reason,
                           rng.randint(weeks - 3, weeks)))
    b.executemany("INSERT INTO verification_log (verification_id, serial, sku, store_id, result, reason_code, week) "
                  "VALUES (%s,%s,%s,%s,%s,%s,%s)", clone_rows)
    brand_conn.close()
    paypal_conn.close()

    # ---------------- platform ----------------
    with db.connect("platform") as pl:
        pl.execute(PLATFORM_SCHEMA)
        pl.cursor().executemany("INSERT INTO stores VALUES (%s,%s,%s,%s,%s)",
                                [(s[0], s[2], s[3], s[4], BRAND) for s in stores])

    print(f"seeded {weeks} weeks: {len(txns)} transactions, {counter - 100000 + 1} serials, "
          f"{len(clone_rows)} clone attempts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    build(small=args.small, seed=args.seed)
