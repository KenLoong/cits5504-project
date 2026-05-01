// ============================================================
// CITS5504 Project 2 — Neo4j AuraDB Import Script
// ============================================================
// HOW TO USE (AuraDB Cloud Free):
//
//   The AuraDB cloud instance cannot access your local filesystem,
//   so the CSV files must be hosted at a public HTTPS URL first.
//
//   ── RECOMMENDED: GitHub Gist ──────────────────────────────
//   1. Go to https://gist.github.com (login with GitHub account)
//   2. Create a new secret gist; drag-and-drop these 3 files:
//        output/cleaned/airports.csv   (132 KB)
//        output/cleaned/airlines.csv   ( 16 KB)
//        output/cleaned/routes.csv     (  3 MB)
//   3. Click "Create secret gist"
//   4. For each file, click the "Raw" button → copy that URL
//      Raw URLs look like:
//      https://gist.githubusercontent.com/<user>/<gist_id>/raw/<hash>/airports.csv
//   5. Paste those 3 URLs into the placeholders below.
//
//   ── ALTERNATIVE: Public GitHub Repository ─────────────────
//   Push the output/cleaned/ folder to a public GitHub repo,
//   then use raw.githubusercontent.com URLs.
//
//   ── HOW TO RUN IN AURADB ──────────────────────────────────
//   Open AuraDB Console → "Query" tab (Neo4j Browser or Workspace).
//   Run each numbered BLOCK separately in sequence.
//   Wait for the previous block to finish before starting the next.
//
// ============================================================

// ------------------------------------------------------------
// BLOCK 1 — Uniqueness Constraints (run this first)
//            Constraints act as indexes → crucial for import speed.
// ------------------------------------------------------------

CREATE CONSTRAINT airport_id_unique IF NOT EXISTS
  FOR (a:Airport) REQUIRE a.airport_id IS UNIQUE;

CREATE CONSTRAINT airline_id_unique IF NOT EXISTS
  FOR (al:Airline) REQUIRE al.airline_id IS UNIQUE;

// ------------------------------------------------------------
// BLOCK 2 — Import Airport nodes
// ------------------------------------------------------------
// airports.csv columns: airport_id, name, city, country
//
// Replace the URL below with your public raw CSV URL.
// Example GitHub Gist raw URL:
//   https://gist.githubusercontent.com/<user>/<gist_id>/raw/airports.csv

// ↓ Replace with your actual Gist/GitHub raw URL ↓
LOAD CSV WITH HEADERS FROM
  'https://gist.githubusercontent.com/KenLoong/6cd2b595efba2fbb938da95595b95693/raw/71d9d16aaab461e4d24390a5937c86a4fa47e177/airports.csv'
AS row
CREATE (a:Airport {
  airport_id : toInteger(row.airport_id),
  name       : row.name,
  city       : row.city,
  country    : row.country
});

// Verify: should return 2795
MATCH (a:Airport) RETURN count(a) AS airport_count;

// ------------------------------------------------------------
// BLOCK 3 — Import Airline nodes
// ------------------------------------------------------------
// airlines.csv columns: airline_id, name, country
//
// Replace the URL below with your public raw CSV URL.

// ↓ Replace with your actual Gist/GitHub raw URL ↓
LOAD CSV WITH HEADERS FROM
  'https://gist.githubusercontent.com/KenLoong/6cd2b595efba2fbb938da95595b95693/raw/71d9d16aaab461e4d24390a5937c86a4fa47e177/airlines.csv'
AS row
CREATE (al:Airline {
  airline_id : toInteger(row.airline_id),
  name       : row.name,
  country    : row.country
});

// Verify: should return 488
MATCH (al:Airline) RETURN count(al) AS airline_count;

// ------------------------------------------------------------
// BLOCK 4 — Import ROUTE relationships  (batched, ~57 K rows)
// ------------------------------------------------------------
// routes.csv columns:
//   route_id, airline_id, dep_airport_id, arr_airport_id, equipment
//
// The equipment field contains semicolon-separated aircraft names,
// e.g. "Boeing 737;Airbus A320". It is stored as-is on the
// relationship; Cypher's split() function is used in queries
// (Q4) to count distinct types.
//
// Replace the URL below with your public raw CSV URL.
//
// NOTE: :auto and CALL { } IN TRANSACTIONS require the Neo4j
//       browser to be in "auto-commit" mode (the default in
//       AuraDB Query tab). If you get a syntax error try
//       removing ":auto" from the first line.

// ↓ Replace with your actual Gist/GitHub raw URL ↓
:auto
LOAD CSV WITH HEADERS FROM
  'https://gist.githubusercontent.com/KenLoong/6cd2b595efba2fbb938da95595b95693/raw/71d9d16aaab461e4d24390a5937c86a4fa47e177/routes.csv'
AS row
CALL {
  WITH row
  MATCH (dep:Airport {airport_id: toInteger(row.dep_airport_id)})
  MATCH (arr:Airport {airport_id: toInteger(row.arr_airport_id)})
  CREATE (dep)-[:ROUTE {
    route_id   : toInteger(row.route_id),
    airline_id : toInteger(row.airline_id),
    equipment  : row.equipment
  }]->(arr)
} IN TRANSACTIONS OF 1000 ROWS;

// Verify: should return 57301
MATCH ()-[r:ROUTE]->() RETURN count(r) AS route_count;

// ------------------------------------------------------------
// BLOCK 5 — Import OPERATES relationships
// ------------------------------------------------------------
// operates.csv columns: airline_id, dep_airport_id
//
// Semantics: (Airline)-[:OPERATES]->(Airport)
//   "This airline has at least one route departing from this airport."
// 16,768 unique (airline, departure-airport) pairs.
// This connects Airline nodes into the graph so they are not isolated.
//
// Upload operates.csv to the same Gist and replace the URL below.

:auto
LOAD CSV WITH HEADERS FROM
  'https://gist.githubusercontent.com/KenLoong/6cd2b595efba2fbb938da95595b95693/raw/d5795664807a666891fb32a11c84940ce2146e6c/operates.csv'
AS row
CALL {
  WITH row
  MATCH (al:Airline  {airline_id:  toInteger(row.airline_id)})
  MATCH (ap:Airport  {airport_id:  toInteger(row.dep_airport_id)})
  CREATE (al)-[:OPERATES]->(ap)
} IN TRANSACTIONS OF 1000 ROWS;

// Verify: should return 16768
MATCH ()-[r:OPERATES]->() RETURN count(r) AS operates_count;

// ------------------------------------------------------------
// BLOCK 6 — Schema / metadata confirmation
// ------------------------------------------------------------
// View the property graph schema in the browser:
CALL db.schema.visualization();

// Node and relationship counts summary:
MATCH (n) RETURN labels(n) AS label, count(n) AS count
UNION ALL
MATCH ()-[r]->() RETURN [type(r)] AS label, count(r) AS count;
