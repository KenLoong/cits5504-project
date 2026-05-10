// ============================================================
// CITS5504 Project 2 — Cypher Queries (Q1–Q6 + Custom)
// ============================================================
// Run each query block independently in the AuraDB Query tab.
// ============================================================


// ------------------------------------------------------------
// PRE-CHECK: Find exact airport names for Q5
// (Run this first to confirm spelling before writing Q5)
// ------------------------------------------------------------
MATCH (a:Airport)
WHERE a.city IN ['Beijing', 'Perth'] AND a.country IN ['China', 'Australia']
RETURN a.airport_id, a.name, a.city, a.country
ORDER BY a.country;


// ============================================================
// Q1 (a) — List all distinct airline names from Australia
// Uses [:OPERATES] to ensure only active airlines are returned
// ============================================================
MATCH (al:Airline {country: 'Australia'})-[:OPERATES]->()
RETURN DISTINCT al.name AS airline_name
ORDER BY al.name;


// ============================================================
// Q2 (b) — Count domestic vs international routes
// Domestic  = departure and arrival airports in the same country
// International = different countries
// ============================================================
MATCH (dep:Airport)-[r:ROUTE]->(arr:Airport)
WITH
  CASE WHEN dep.country = arr.country
       THEN 'Domestic'
       ELSE 'International'
  END AS route_type
RETURN route_type, count(*) AS record_count
ORDER BY route_type;


// ============================================================
// Q3 (c) — Airport pair with the greatest number of route records
// Treat A→B and B→A as the same pair.  Must use WITH.
// ============================================================
MATCH (a:Airport)-[r:ROUTE]->(b:Airport)
WITH
  CASE WHEN a.name < b.name THEN a.name ELSE b.name END AS airport1,
  CASE WHEN a.name < b.name THEN b.name ELSE a.name END AS airport2
WITH airport1, airport2, count(*) AS total_records
RETURN airport1, airport2, total_records
ORDER BY total_records DESC
LIMIT 1;


// ============================================================
// Q4 (d) — Top 5 airport pairs by number of distinct aircraft types
// Equipment stored as semicolon-separated string; split then UNWIND.
// Treat A→B and B→A as the same pair.
// Count distinct types across ALL rows and ALL airlines for that pair.
// ============================================================
MATCH (a:Airport)-[r:ROUTE]->(b:Airport)
WITH
  CASE WHEN a.name < b.name THEN a.name ELSE b.name END AS airport1,
  CASE WHEN a.name < b.name THEN b.name ELSE a.name END AS airport2,
  r.equipment AS equipment_str
WITH airport1, airport2, split(equipment_str, ';') AS equipment_list
UNWIND equipment_list AS raw_type
WITH airport1, airport2, trim(raw_type) AS equipment_type
WHERE equipment_type <> ''
WITH airport1, airport2, count(DISTINCT equipment_type) AS distinct_types
RETURN airport1, airport2, distinct_types
ORDER BY distinct_types DESC
LIMIT 5;


// ============================================================
// Q5 (e) — All routes Beijing → Perth with at most 3 hops
//
// NOTE: Run the PRE-CHECK above first to confirm exact names.
//       Replace the names below if they differ in your dataset.
//
// "Distinct route" = unique ordered sequence of airport names visited.
// ============================================================

// Step 1 — Confirm exact airport names (adjust if PRE-CHECK differs)
MATCH (a:Airport)
WHERE (a.name CONTAINS 'Beijing Capital' OR a.name CONTAINS 'Perth')
  AND a.country IN ['China', 'Australia']
RETURN a.name, a.city, a.country;

// Step 2 — Count distinct routes (1–3 hops)
MATCH path = (start:Airport {name: 'Beijing Capital International Airport'})
             -[:ROUTE*1..3]->
             (end:Airport {name: 'Perth International Airport'})
WITH [n IN nodes(path) | n.name] AS route_sequence
RETURN count(DISTINCT route_sequence) AS distinct_routes;


// ============================================================
// Q6 (f) — Top 5 airline pairs competing on the most shared routes
// [CITS5504 students only]
//
// Two airlines compete if they both serve the same airport pair
// (A→B and B→A treated as the same route).
// Return: airline pair names + number of shared routes.
// ============================================================
MATCH (dep:Airport)-[r:ROUTE]->(arr:Airport)
WITH
  CASE WHEN dep.airport_id < arr.airport_id
       THEN dep.airport_id ELSE arr.airport_id END AS ap1,
  CASE WHEN dep.airport_id < arr.airport_id
       THEN arr.airport_id ELSE dep.airport_id END AS ap2,
  r.airline_id AS al_id
WITH ap1, ap2, collect(DISTINCT al_id) AS airline_ids
WHERE size(airline_ids) >= 2
UNWIND airline_ids AS al1_id
UNWIND airline_ids AS al2_id
WITH ap1, ap2, al1_id, al2_id
WHERE al1_id < al2_id
WITH al1_id, al2_id, count(*) AS shared_routes
MATCH (al1:Airline {airline_id: al1_id}),
      (al2:Airline {airline_id: al2_id})
RETURN al1.name AS airline1, al2.name AS airline2, shared_routes
ORDER BY shared_routes DESC
LIMIT 5;


// ============================================================
// CUSTOM QUERY 1 — Top 10 busiest hub airports by total routes
// (both departing and arriving)
// ============================================================
MATCH (a:Airport)-[:ROUTE]-()
WITH a, count(*) AS total_connections
RETURN a.name AS airport, a.city AS city, a.country AS country,
       total_connections
ORDER BY total_connections DESC
LIMIT 10;


// ============================================================
// CUSTOM QUERY 2 (APOC) — Graph metadata schema inspection
//
// Reveals all node labels, relationship types, and property keys
// in the database.  Useful for understanding the schema structure
// without needing prior knowledge of the graph.
// ============================================================
CALL apoc.meta.schema()
YIELD value
RETURN value;


// ============================================================
// CUSTOM QUERY 3 (APOC) — Airport network degree distribution
//
// Uses apoc.coll.avg / apoc.coll.max / apoc.coll.min to compute
// descriptive statistics on the number of routes per airport,
// characterising the connectivity distribution of the network.
// ============================================================
MATCH (a:Airport)
WITH a, count { (a)-[:ROUTE]-() } AS degree
WITH collect(degree) AS all_degrees
RETURN
  size(all_degrees)                              AS total_airports,
  apoc.coll.avg(all_degrees)                    AS mean_connections,
  apoc.coll.max(all_degrees)                    AS max_connections,
  apoc.coll.min(all_degrees)                    AS min_connections,
  size([d IN all_degrees WHERE d >= 100])        AS major_hubs;
