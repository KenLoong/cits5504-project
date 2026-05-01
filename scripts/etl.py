"""
ETL Script for CITS5504 Project 2 - Graph Database Design
==========================================================
Reads the raw flight routes dataset, performs data cleaning,
and outputs normalised CSV files ready for Neo4j import:
  - airports.csv   : unique Airport nodes
  - airlines.csv   : unique Airline nodes
  - routes.csv     : ROUTE relationships between airports

Author: see student ID
"""

import pandas as pd
import os

# ── paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV   = os.path.join(BASE_DIR, "dataset", "Project2_dataset.csv")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output", "cleaned")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 1. Load raw data ─────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 – Loading raw dataset …")
df = pd.read_csv(INPUT_CSV, dtype=str)
df.columns = df.columns.str.strip()
print(f"  Loaded {len(df):,} rows × {len(df.columns)} columns")
print(f"  Columns: {list(df.columns)}")

# Strip leading/trailing whitespace from every cell
df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

# ── 2. Audit dirty data ──────────────────────────────────────────────────────
print("\nSTEP 2 – Auditing dirty data …")

# Build a combined "all airports" view from BOTH departure and arrival sides
dep = df[["Departure Airport Name",
          "Departure Airport City",
          "Departure Airport Country/Region"]].rename(columns={
    "Departure Airport Name":           "airport_name",
    "Departure Airport City":           "city",
    "Departure Airport Country/Region": "country",
})
arr = df[["Arrival Airport Name",
          "Arrival Airport City",
          "Arrival Airport Country/Region"]].rename(columns={
    "Arrival Airport Name":           "airport_name",
    "Arrival Airport City":           "city",
    "Arrival Airport Country/Region": "country",
})
all_airports_raw = pd.concat([dep, arr], ignore_index=True).drop_duplicates()

# Find airports with more than one (city, country) combination
duplicates = (
    all_airports_raw
    .groupby("airport_name")
    .filter(lambda g: g[["city", "country"]].drop_duplicates().shape[0] > 1)
    .sort_values("airport_name")
)
if duplicates.empty:
    print("  No airport inconsistencies found.")
else:
    print(f"  Found {duplicates['airport_name'].nunique()} airport(s) with "
          f"inconsistent City/Country:")
    print(duplicates.to_string(index=False))

# ── 3. Known data-cleaning corrections ──────────────────────────────────────
print("\nSTEP 3 – Applying data-cleaning corrections …")

# ------------------------------------------------------------------ #
# CORRECTIONS dictionary                                               #
# Each entry: airport_name → {"country": correct_country,            #
#                              "city": correct_city}                  #
# Sources: IATA airport database, Wikipedia                           #
# ------------------------------------------------------------------ #
CORRECTIONS = {
    # ── Primary correction flagged by unit coordinator ──────────────
    "Sydney Kingsford Smith International Airport": {
        "country": "Australia", "city": "Sydney",
        # IATA: SYD. Australia's busiest airport.
        # https://en.wikipedia.org/wiki/Sydney_Airport
    },
    # ── Venezuelan airports misattributed to Spain / Mexico ─────────
    "Arturo Michelena International Airport": {
        "country": "Venezuela", "city": "Valencia",
        # IATA: VLN. Valencia, Carabobo, Venezuela (not Spain).
    },
    "Alberto Carnevalli Airport": {
        "country": "Venezuela", "city": "Merida",
        # IATA: MRD. Mérida, Venezuela (not Mexico).
    },
    "General Jose Antonio Anzoategui International Airport": {
        "country": "Venezuela", "city": "Barcelona",
        # IATA: BLA. Barcelona, Anzoátegui, Venezuela (not Spain).
    },
    "Mayor Buenaventura Vivas International Airport": {
        "country": "Venezuela", "city": "Santo Domingo",
        # IATA: STD. Santo Domingo, Táchira, Venezuela (not Dominican Republic).
    },
    # ── Santiago, Chile airport misattributed to Spain ──────────────
    "Comodoro Arturo Merino Benitez International Airport": {
        "country": "Chile", "city": "Santiago",
        # IATA: SCL. Santiago, Chile (not Spain).
    },
    # ── Dominican Republic airport misattributed to Spain ───────────
    "Cibao International Airport": {
        "country": "Dominican Republic", "city": "Santiago",
        # IATA: STI. Santiago de los Caballeros, DR (not Spain).
    },
    # ── London airports misattributed to Canada ─────────────────────
    "London Heathrow Airport": {
        "country": "United Kingdom", "city": "London",
        # IATA: LHR. London, England.
    },
    "London Gatwick Airport": {
        "country": "United Kingdom", "city": "London",
        # IATA: LGW. London, England.
    },
    "London Stansted Airport": {
        "country": "United Kingdom", "city": "London",
        # IATA: STN. London, England.
    },
    "London Luton Airport": {
        "country": "United Kingdom", "city": "London",
        # IATA: LTN. London, England.
    },
    "London City Airport": {
        "country": "United Kingdom", "city": "London",
        # IATA: LCY. London, England.
    },
    # ── US airports misattributed to other countries ─────────────────
    "Birmingham-Shuttlesworth International Airport": {
        "country": "United States", "city": "Birmingham",
        # IATA: BHM. Birmingham, Alabama, USA (not UK).
    },
    "Norman Y. Mineta San Jose International Airport": {
        "country": "United States", "city": "San Jose",
        # IATA: SJC. San Jose, California, USA (not Costa Rica).
    },
    "Northwest Florida Beaches International Airport": {
        "country": "United States", "city": "Panama City",
        # IATA: ECP. Panama City Beach, Florida, USA (not Panama).
    },
    "St Petersburg Clearwater International Airport": {
        "country": "United States", "city": "St. Petersburg",
        # IATA: PIE. St. Petersburg, Florida, USA (not Russia).
    },
    "Fort Smith Regional Airport": {
        "country": "United States", "city": "Fort Smith",
        # IATA: FSM. Fort Smith, Arkansas, USA (not Canada).
    },
    "Florence Regional Airport": {
        "country": "United States", "city": "Florence",
        # IATA: FLO. Florence, South Carolina, USA (not Italy).
    },
    "Tri-Cities Regional TN/VA Airport": {
        "country": "United States", "city": "Bristol",
        # IATA: TRI. Bristol/Kingsport/Johnson City, TN/VA, USA (not UK).
    },
    "Charles M. Schulz Sonoma County Airport": {
        "country": "United States", "city": "Santa Rosa",
        # IATA: STS. Santa Rosa, California, USA (not Argentina).
    },
    # ── South American airports with misattributed countries ─────────
    "Atlas Brasil Cantanhede Airport": {
        "country": "Brazil", "city": "Boa Vista",
        # IATA: BVH. Boa Vista, Roraima, Brazil (not Cape Verde).
    },
    "Presidente Joao Batista Figueiredo Airport": {
        "country": "Brazil", "city": "Sinop",
        # IATA: OPS. Sinop, Mato Grosso, Brazil (not Turkey).
    },
    # ── Caribbean / Guyana airports with misattributed countries ─────
    "Cheddi Jagan International Airport": {
        "country": "Guyana", "city": "Georgetown",
        # IATA: GEO. Georgetown, Guyana (not Cayman Islands).
    },
    "Eugene F. Correira International Airport": {
        "country": "Guyana", "city": "Georgetown",
        # IATA: OGL. Ogle, Guyana – Georgetown area (not Cayman Islands).
    },
    "Norman Manley International Airport": {
        "country": "Jamaica", "city": "Kingston",
        # IATA: KIN. Kingston, Jamaica (not Canada).
    },
    "Luis Munoz Marin International Airport": {
        "country": "Puerto Rico", "city": "San Juan",
        # IATA: SJU. San Juan, Puerto Rico (not Argentina).
    },
    "JAGS McCartney International Airport": {
        "country": "Turks and Caicos Islands", "city": "Cockburn Town",
        # IATA: GDT. Grand Turk, Turks and Caicos Islands (not Bahamas).
    },
    # ── Bolivia / Vanuatu ────────────────────────────────────────────
    "El Alto International Airport": {
        "country": "Bolivia", "city": "La Paz",
        # IATA: LPB. La Paz / El Alto, Bolivia (not Mexico).
    },
    "Futuna Airport": {
        "country": "Vanuatu", "city": "Futuna Island",
        # IATA: FTA. Futuna Island, Tafea Province, Vanuatu.
        # (Wallis and Futuna is a separate French territory.)
    },
    # ── India airport misattributed to Japan ─────────────────────────
    "Cochin International Airport": {
        "country": "India", "city": "Kochi",
        # IATA: COK. Kochi (Cochin), Kerala, India (not Japan).
    },
    # ── Saint Pierre and Miquelon vs Reunion ─────────────────────────
    "St Pierre Airport": {
        "country": "Saint Pierre and Miquelon", "city": "St.-pierre",
        # IATA: FSP. Saint-Pierre, Saint Pierre and Miquelon (French territory
        # near Newfoundland, Canada — not Réunion).
    },
}

total_fixed = 0
for airport_name, fix in CORRECTIONS.items():
    correct_country = fix["country"]
    correct_city    = fix["city"]

    mask_dep = (df["Departure Airport Name"] == airport_name) & (
        (df["Departure Airport Country/Region"] != correct_country) |
        (df["Departure Airport City"] != correct_city)
    )
    mask_arr = (df["Arrival Airport Name"] == airport_name) & (
        (df["Arrival Airport Country/Region"] != correct_country) |
        (df["Arrival Airport City"] != correct_city)
    )
    bad = mask_dep.sum() + mask_arr.sum()
    if bad > 0:
        df.loc[mask_dep, "Departure Airport Country/Region"] = correct_country
        df.loc[mask_dep, "Departure Airport City"]           = correct_city
        df.loc[mask_arr, "Arrival Airport Country/Region"]   = correct_country
        df.loc[mask_arr, "Arrival Airport City"]             = correct_city
        print(f"  [FIXED] {airport_name}: {bad} row(s) → {correct_city}, {correct_country}")
        total_fixed += bad

print(f"\n  Total rows corrected: {total_fixed}")

# ------------------------------------------------------------------ #
# Re-audit after corrections                                           #
# ------------------------------------------------------------------ #
dep2 = df[["Departure Airport Name",
           "Departure Airport City",
           "Departure Airport Country/Region"]].rename(columns={
    "Departure Airport Name":           "airport_name",
    "Departure Airport City":           "city",
    "Departure Airport Country/Region": "country",
})
arr2 = df[["Arrival Airport Name",
           "Arrival Airport City",
           "Arrival Airport Country/Region"]].rename(columns={
    "Arrival Airport Name":           "airport_name",
    "Arrival Airport City":           "city",
    "Arrival Airport Country/Region": "country",
})
all_airports_clean = pd.concat([dep2, arr2], ignore_index=True).drop_duplicates()

remaining = (
    all_airports_clean
    .groupby("airport_name")
    .filter(lambda g: g[["city", "country"]].drop_duplicates().shape[0] > 1)
)
if remaining.empty:
    print("  Post-correction audit: no remaining inconsistencies. ✓")
else:
    print(f"\n  Post-correction – {remaining['airport_name'].nunique()} airport(s) "
          f"still have multiple records (genuine name conflicts or "
          f"homonymous airports in different countries):")
    still_issues = (
        remaining
        .groupby("airport_name")[["city","country"]]
        .apply(lambda g: g.drop_duplicates())
        .reset_index(level=0)
    )
    print(still_issues.to_string(index=False))
    print("  NOTE: These are resolved by taking the most-common value per name.")


# ── 4. Build airports table ──────────────────────────────────────────────────
print("\nSTEP 4 – Building airports table …")

# Deduplicate: one canonical record per airport name
# If a name still has multiple (city, country), keep the most common combo
def most_common(series):
    return series.value_counts().index[0]

airports_df = (
    all_airports_clean
    .groupby("airport_name", as_index=False)
    .agg(city=("city", most_common), country=("country", most_common))
    .reset_index(drop=True)
)
airports_df.insert(0, "airport_id", range(1, len(airports_df) + 1))
airports_df.rename(columns={"airport_name": "name"}, inplace=True)

print(f"  {len(airports_df):,} unique airports")

# ── 5. Build airlines table ──────────────────────────────────────────────────
print("\nSTEP 5 – Building airlines table …")

airlines_raw = df[["Airline Name", "Airline Country"]].rename(columns={
    "Airline Name":    "name",
    "Airline Country": "country",
}).drop_duplicates()

# Same dedup logic for airlines
airlines_df = (
    airlines_raw
    .groupby("name", as_index=False)
    .agg(country=("country", most_common))
    .reset_index(drop=True)
)
airlines_df.insert(0, "airline_id", range(1, len(airlines_df) + 1))

print(f"  {len(airlines_df):,} unique airlines")

# ── 6. Build routes table ─────────────────────────────────────────────────────
print("\nSTEP 6 – Building routes table …")

# Build lookup dicts for fast ID resolution
airport_id_map = dict(zip(airports_df["name"], airports_df["airport_id"]))
airline_id_map = dict(zip(airlines_df["name"], airlines_df["airline_id"]))

routes_df = df.copy()
routes_df["dep_airport_id"] = routes_df["Departure Airport Name"].map(airport_id_map)
routes_df["arr_airport_id"] = routes_df["Arrival Airport Name"].map(airport_id_map)
routes_df["airline_id"]     = routes_df["Airline Name"].map(airline_id_map)
routes_df.insert(0, "route_id", range(1, len(routes_df) + 1))

routes_out = routes_df[[
    "route_id",
    "airline_id",
    "dep_airport_id",
    "arr_airport_id",
    "Plane Name",
]].rename(columns={"Plane Name": "equipment"})

# Sanity check: any unresolved IDs?
missing_dep = routes_out["dep_airport_id"].isna().sum()
missing_arr = routes_out["arr_airport_id"].isna().sum()
missing_al  = routes_out["airline_id"].isna().sum()
if missing_dep + missing_arr + missing_al > 0:
    print(f"  WARNING – unresolved IDs: dep={missing_dep}, "
          f"arr={missing_arr}, airline={missing_al}")
else:
    print(f"  All IDs resolved successfully.")

print(f"  {len(routes_out):,} route records")

# ── 7. Build OPERATES table ───────────────────────────────────────────────────
# Semantics: (Airline)-[:OPERATES]->(Airport)
#   "This airline has at least one route departing from this airport."
# Generated from unique (airline_id, dep_airport_id) pairs in routes.
# This makes Airline nodes proper graph citizens connected via edges,
# rather than isolated lookup nodes linked only by a property value.
print("\nSTEP 7 – Building OPERATES table …")

operates_df = (
    routes_out[["airline_id", "dep_airport_id"]]
    .drop_duplicates()
    .reset_index(drop=True)
)
print(f"  {len(operates_df):,} unique (airline, departure-airport) pairs")

# ── 8. Write output CSVs ─────────────────────────────────────────────────────
print("\nSTEP 8 – Writing output CSVs …")

airports_path  = os.path.join(OUTPUT_DIR, "airports.csv")
airlines_path  = os.path.join(OUTPUT_DIR, "airlines.csv")
routes_path    = os.path.join(OUTPUT_DIR, "routes.csv")
operates_path  = os.path.join(OUTPUT_DIR, "operates.csv")

airports_df.to_csv(airports_path,  index=False)
airlines_df.to_csv(airlines_path,  index=False)
routes_out.to_csv(routes_path,     index=False)
operates_df.to_csv(operates_path,  index=False)

print(f"  airports.csv  → {airports_path}")
print(f"  airlines.csv  → {airlines_path}")
print(f"  routes.csv    → {routes_path}")
print(f"  operates.csv  → {operates_path}")

# ── 9. Summary report ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ETL SUMMARY")
print("=" * 60)
print(f"  Input rows (routes)  : {len(df):,}")
print(f"  Unique airports      : {len(airports_df):,}")
print(f"  Unique airlines      : {len(airlines_df):,}")
print(f"  Route records        : {len(routes_out):,}")
print(f"  OPERATES records     : {len(operates_df):,}")
print(f"\n  Sample airports.csv:")
print(airports_df.head(5).to_string(index=False))
print(f"\n  Sample airlines.csv:")
print(airlines_df.head(5).to_string(index=False))
print(f"\n  Sample routes.csv:")
print(routes_out.head(5).to_string(index=False))
print(f"\n  Sample operates.csv:")
print(operates_df.head(5).to_string(index=False))
print("=" * 60)
print("ETL completed successfully.")
