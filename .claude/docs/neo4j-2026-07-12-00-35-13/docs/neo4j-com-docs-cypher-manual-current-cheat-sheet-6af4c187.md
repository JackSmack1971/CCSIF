---
title: "Cypher Cheat Sheet"
source_url: "https://neo4j.com/docs/cypher-manual/current/cheat-sheet/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.002Z"
---
[](https://neo4j.com/docs/cypher-manual/current/introduction/)

[Edit this page](https://github.com/neo4j/docs-cypher/tree/cypher-25/modules/cheat-sheet/pages/index.adoc)

# Cypher Cheat Sheet

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_read_query)Read Query

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_read_query_structure)Read Query Structure

```none
[USE]
[MATCH [SEARCH] [WHERE]]
[OPTIONAL MATCH [SEARCH] [WHERE]]
[WITH [ORDER BY] [SKIP] [LIMIT] [WHERE]]
RETURN [ORDER BY] [SKIP] [LIMIT]
```

Baseline for pattern search operations.

-   [`USE`](https://neo4j.com/docs/cypher-manual/25/clauses/use/) clause.

-   [`MATCH`](https://neo4j.com/docs/cypher-manual/25/clauses/match/) clause.

-   [`OPTIONAL MATCH`](https://neo4j.com/docs/cypher-manual/25/clauses/optional-match/) clause.

-   [`WITH`](https://neo4j.com/docs/cypher-manual/25/clauses/with/) clause.

-   [`RETURN`](https://neo4j.com/docs/cypher-manual/25/clauses/return/) clause.

-   Cypher® keywords are not case-sensitive.

-   Cypher is case-sensitive for variables.


### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_match)[MATCH](https://neo4j.com/docs/cypher-manual/25/clauses/match/)

```cypher
MATCH (n)
RETURN n
```

Match all nodes and return all nodes.

```cypher
MATCH (movie:Movie)
RETURN movie.title
```

Find all nodes with the `Movie` label.

```cypher
MATCH (:Person {name: 'Oliver Stone'})-[r]->()
RETURN type(r) AS relType
```

Find the types of an aliased relationship.

```cypher
MATCH (:Movie {title: 'Wall Street'})<-[:ACTED_IN]-(actor:Person)
RETURN actor.name AS actor
```

Relationship pattern filtering on the `ACTED_IN` relationship type.

```cypher
MATCH path = ()-[:ACTED_IN]->(movie:Movie)
RETURN path
```

Bind a path pattern to a path variable, and return the path pattern.

```cypher
MATCH (movie:$($label))
RETURN movie.title AS movieTitle
```

Node labels and relationship types can be referenced dynamically in expressions, parameters, and variables. The expression must evaluate to a `STRING NOT NULL | LIST<STRING NOT NULL> NOT NULL` value.

```cypher
CALL db.relationshipTypes()
YIELD relationshipType
MATCH ()-[r:$(relationshipType)]->()
RETURN relationshipType, count(r) AS relationshipCount
```

Match nodes dynamically using a variable.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_optional_match)[OPTIONAL MATCH](https://neo4j.com/docs/cypher-manual/25/clauses/optional-match/)

```cypher
MATCH (p:Person {name: 'Martin Sheen'})
OPTIONAL MATCH (p)-[r:DIRECTED]->()
RETURN p.name, r
```

Use `MATCH` to find entities that must be present in the pattern. Use `OPTIONAL MATCH` to find entities that may not be present in the pattern. `OPTIONAL MATCH` returns `null` for empty rows.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_where)[WHERE](https://neo4j.com/docs/cypher-manual/25/clauses/where/)

```cypher
MATCH (n)
WHERE n:Swedish
RETURN n.name AS name
```

`WHERE` used to filter on node labels.

```cypher
MATCH (n:Person)
WHERE n.age < 35
RETURN n.name AS name, n.age AS age
```

`WHERE` used to filter on node properties.

```cypher
MATCH (:Person {name:'Andy'})-[k:KNOWS]->(f)
WHERE k.since < 2000
RETURN f.name AS oldFriend
```

`WHERE` used to filter on relationship properties.

```cypher
MATCH (n)
WHERE n:$($label)
RETURN labels(n) AS labels
```

```cypher
MATCH (n:Person)
WHERE n[$propname] > 40
RETURN n.name AS name, n.age AS age
```

To filter on a property using a dynamically computed name, use square brackets `[]`.

```cypher
WITH 35 AS minAge
MATCH (a:Person WHERE a.name = 'Andy')-[:KNOWS]->(b:Person WHERE b.age > minAge)
RETURN b.name AS name
```

`WHERE` used inside a fixed-length pattern.

```cypher
MATCH (a:Person {name: 'Andy'})
RETURN [(a)-->(b WHERE b:Person) | b.name] AS friends
```

`WHERE` can appear inside a pattern comprehension.

```cypher
MATCH p = (a:Person {name: "Andy"})-[r:KNOWS WHERE r.since < 2011]->{1,4}(:Person)
RETURN [n IN nodes(p) | n.name] AS paths
```

`WHERE` can be used to filter variable-length patterns.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_search)[SEARCH](https://neo4j.com/docs/cypher-manual/25/clauses/search/)

```cypher
MATCH (movie:Movie)
  SEARCH movie IN (
    VECTOR INDEX moviePlots
    FOR vector([1, 2, 3], 3, INTEGER)
    LIMIT 4
  )
RETURN movie.title AS title
```

`SEARCH` is used to query vector indexes, and filters the result based on approximate nearest neighbor (ANN) vector search. It can can appear in a `MATCH` or `OPTIONAL MATCH` clause.

```cypher
MATCH ()-[r]->()
SEARCH r IN (
  VECTOR INDEX `relVectorIndexName`
  FOR [1, 2, 3]
  WHERE r.additionalProp > 10
  LIMIT 5
) SCORE AS myScore
RETURN r, myScore
```

`SEARCH` can also be used for relationships. `SEARCH` can include an optional `WHERE` subclause for in-index filtering and an optional `SCORE` subcluase to return similarity scores.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_filter)[FILTER](https://neo4j.com/docs/cypher-manual/25/clauses/filter/)

```cypher
MATCH (n:Person)
FILTER n.age < 35
RETURN n.name AS name, n.age AS age
```

`FILTER` is used to add filters to queries, similar to Cypher’s `WHERE`. Unlike `WHERE`, `FILTER` is not a subclause, which means it can be used independently of the `MATCH`, `OPTIONAL MATCH`, and `WITH` clauses, but not within them.

```cypher
MATCH (n:Person)
FILTER n[$propname] > 40
RETURN n.name AS name, n.age AS age
```

`FILTER` on dynamic properties.

```cypher
LOAD CSV WITH HEADERS FROM 'file:///companies.csv' AS row
FILTER row.Id IS NOT NULL
MERGE (c:Company {id: row.Id})
```

`FILTER` can be used as a substitute for the `WITH * WHERE <predicate>` constructs in Cypher.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_return)[RETURN](https://neo4j.com/docs/cypher-manual/25/clauses/return/)

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})
RETURN p
```

Return a node.

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})-[r:ACTED_IN]->(m)
RETURN type(r)
```

Return relationship types.

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})
RETURN p.bornIn
```

Return a specific property.

```cypher
MATCH p = (keanu:Person {name: 'Keanu Reeves'})-[r]->(m)
RETURN *
```

To return all nodes, relationships and paths found in a query, use the `*` symbol.

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})
RETURN p.nationality AS citizenship
```

Names of returned columns can be aliased using the `AS` operator.

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})-->(m)
RETURN DISTINCT m
```

`DISTINCT` retrieves unique rows for the returned columns.

The `RETURN` clause can use:

-   [`ORDER BY`](https://neo4j.com/docs/cypher-manual/25/clauses/order-by)

-   [`SKIP`](https://neo4j.com/docs/cypher-manual/25/clauses/skip)

-   [`LIMIT`](https://neo4j.com/docs/cypher-manual/25/clauses/limit)

-   [`WHERE`](https://neo4j.com/docs/cypher-manual/25/clauses/where)


### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_with)[WITH](https://neo4j.com/docs/cypher-manual/25/clauses/with/)

```cypher
MATCH (c:Customer)-[:BUYS]->(:Product {name: 'Chocolate'})
WITH c AS customers
RETURN customers.firstName AS chocolateCustomers
```

`WITH` can be used in combination with the `AS` keyword to bind new variables which can then be passed to subsequent clauses. Any variables not explicitly referenced by `WITH` (or carried over by `WITH *`) are dropped from the scope of the query.

```cypher
MATCH (supplier:Supplier)-[r]->(product:Product)
WITH *
RETURN supplier.name AS company,
       type(r) AS relType,
       product.name AS product
```

Use the wildcard `*` to carry over all variables that are in scope.

```cypher
WITH 11 AS x
CALL (x) {
  UNWIND [2, 3] AS y
  WITH y
  RETURN x*y AS a
}
RETURN x, a
```

`WITH` cannot de-scope variables imported to a `CALL` subquery, because variables imported to a subquery are considered global to its inner scope.

```cypher
MATCH (customer:Customer)-[:BUYS]->(chocolate:Product {name: 'Chocolate'})
WITH customer.firstName || ' ' || customer.lastName AS customerFullName,
     chocolate.price * (1 - customer.discount) AS chocolateNetPrice
RETURN customerFullName,
       chocolateNetPrice
```

`WITH` can be used to assign the values of expressions to variables.

```cypher
MATCH (p:Product)
WITH p, p.price >= 500 AS isExpensive
WITH p, isExpensive, NOT isExpensive AS isAffordable
WITH p, isExpensive, isAffordable,
     CASE
         WHEN isExpensive THEN 'High-end'
         ELSE 'Budget'
     END AS discountCategory
RETURN p.name AS product,
       p.price AS price,
       isAffordable,
       discountCategory
ORDER BY price
```

`WITH` can be used to chain expressions.

```cypher
MATCH (c:Customer)-[:BUYS]->(p:Product)
WITH c.firstName AS customer,
     sum(p.price) AS totalSpent,
     collect(p.name) AS productsBought
RETURN customer,
       totalSpent,
       productsBought
ORDER BY totalSpent DESC
```

`WITH` can be used to perform aggregations and bind the results to new variables.

```cypher
MATCH (c:Customer)
WITH DISTINCT c.discount AS discountRates
RETURN discountRates
ORDER BY discountRates
```

`WITH` can be used to remove duplicate values from the result set if appended with the modifier `DISTINCT`.

```cypher
MATCH (c:Customer)-[:BUYS]->(p:Product)
WITH c,
     sum(p.price) AS totalSpent
  ORDER BY totalSpent DESC
  LIMIT 3
SET c.topSpender = true
RETURN c.firstName AS customer,
       totalSpent,
       c.topSpender AS topSpender
```

`WITH` can order and paginate results if used together with the `ORDER BY`, `LIMIT`, and `SKIP` subclauses.

```cypher
MATCH (s:Supplier)-[:SUPPLIES]->(p:Product)<-[:BUYS]-(c:Customer)
WITH s,
     sum(p.price) AS totalSales,
     count(DISTINCT c) AS uniqueCustomers
  WHERE totalSales > 1000
RETURN s.name AS supplier,
       totalSales,
       uniqueCustomers
```

`WITH` can be followed by the `WHERE` subclause to filter results.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_let)[LET](https://neo4j.com/docs/cypher-manual/25/clauses/let/)

```cypher
MATCH (s:Supplier)-[:SUPPLIES]->(p:Product)
LET supplier = s.name, product = p.name
RETURN supplier, product
```

`LET` is used to bind variables to the results of expressions.

```cypher
MATCH (p:Product)
LET isExpensive = p.price >= 500
LET isAffordable = NOT isExpensive
LET discountCategory = CASE
    WHEN isExpensive THEN 'High-end'
    ELSE 'Budget'
END
RETURN p.name AS product, p.price AS price, isAffordable, discountCategory
ORDER BY price
```

`LET` can be used to chain expressions.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_write_query)Write query

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_write_only_query_structure)Write-Only Query Structure

```none
[USE]
[CREATE]
[MERGE [ON CREATE ...] [ON MATCH ...]]
[WITH [ORDER BY] [SKIP] [LIMIT] [WHERE]]
[SET]
[DELETE]
[REMOVE]
[RETURN [ORDER BY] [SKIP] [LIMIT]]
```

Baseline for write operations.

-   [`CREATE`](https://neo4j.com/docs/cypher-manual/25/clauses/create/) clause.

-   [`MERGE`](https://neo4j.com/docs/cypher-manual/25/clauses/merge/) clause.

-   [`WITH`](https://neo4j.com/docs/cypher-manual/25/clauses/with/) clause.

-   [`SET`](https://neo4j.com/docs/cypher-manual/25/clauses/set/) clause.

-   [`DELETE`](https://neo4j.com/docs/cypher-manual/25/clauses/delete/) clause.

-   [`REMOVE`](https://neo4j.com/docs/cypher-manual/25/clauses/remove/) clause.

-   [`RETURN`](https://neo4j.com/docs/cypher-manual/25/clauses/return/) clause.


### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_read_write_query_structure)Read-Write Query Structure

```none
[USE]
[MATCH [WHERE]]
[OPTIONAL MATCH [WHERE]]
[WITH [ORDER BY] [SKIP] [LIMIT] [WHERE]]
[CREATE]
[MERGE [ON CREATE ...] [ON MATCH ...]]
[WITH [ORDER BY] [SKIP] [LIMIT] [WHERE]]
[SET]
[DELETE]
[REMOVE]
[RETURN [ORDER BY] [SKIP] [LIMIT]]
```

Baseline for pattern search and write operations.

-   [`USE`](https://neo4j.com/docs/cypher-manual/25/clauses/use/) clause.

-   [`MATCH`](https://neo4j.com/docs/cypher-manual/25/clauses/match/) clause

-   [`OPTIONAL MATCH`](https://neo4j.com/docs/cypher-manual/25/clauses/optional-match/) clause.

-   [`CREATE`](https://neo4j.com/docs/cypher-manual/25/clauses/create/) clause

-   [`MERGE`](https://neo4j.com/docs/cypher-manual/25/clauses/merge/) clause.

-   [`WITH`](https://neo4j.com/docs/cypher-manual/25/clauses/with/) clause.

-   [`SET`](https://neo4j.com/docs/cypher-manual/25/clauses/set/) clause.

-   [`DELETE`](https://neo4j.com/docs/cypher-manual/25/clauses/delete/) clause.

-   [`REMOVE`](https://neo4j.com/docs/cypher-manual/25/clauses/remove/) clause.

-   [`RETURN`](https://neo4j.com/docs/cypher-manual/25/clauses/return/) clause.


### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_create)[CREATE](https://neo4j.com/docs/cypher-manual/25/clauses/create/)

```cypher
CREATE (charlie:Person:Actor {name: 'Charlie Sheen'}), (oliver:Person:Director {name: 'Oliver Stone'})
```

Create nodes. Multiple labels can be separated by colons or ampersands.

```cypher
MATCH (charlie:Person {name: 'Charlie Sheen'}), (oliver:Person {name: 'Oliver Stone'})
CREATE (charlie)-[:ACTED_IN {role: 'Bud Fox'}]->(wallStreet:Movie {title: 'Wall Street'})<-[:DIRECTED]-(oliver)
```

Create relationships. Unlike nodes, relationships always need exactly one relationship type and a direction.

```cypher
CREATE (n:Person $props)
RETURN n
```

`CREATE` can utilize parameters.

```cypher
CREATE (greta:$($nodeLabels) {name: 'Greta Gerwig'})
WITH greta
UNWIND $movies AS movieTitle
CREATE (greta)-[rel:$($relType)]->(m:Movie {title: movieTitle})
RETURN greta.name AS name, labels(greta) AS labels, type(rel) AS relType, collect(m.title) AS movies
```

Node labels and relationship types can be referenced dynamically in expressions, parameters, and variables when merging nodes and relationships. The expression must evaluate to a `STRING NOT NULL | LIST<STRING NOT NULL> NOT NULL` value.

```cypher
INSERT (tom:Person&Actor&Director {name: 'Tom Hanks'})
```

`INSERT` can be used as a synonym to `CREATE` for creating nodes and relationships. Unlike `CREATE`, `INSERT` requires that multiple labels are separated by an ampersand `&` and not by colon `:`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_set)[SET](https://neo4j.com/docs/cypher-manual/25/clauses/set/)

```cypher
MATCH (n {name: 'Andy'})
SET n.surname = 'Taylor'
RETURN n.name, n.surname
```

Update a node property with `SET`.

```cypher
MATCH (n {name: 'Andy'})
SET (CASE WHEN n.age = 36 THEN n END).worksIn = 'Malmo'
RETURN n.name, n.worksIn
```

`SET` a property on a node or relationship using more complex expressions.

```cypher
MATCH (n {name: 'Andy'})
SET n.age = toString(n.age)
RETURN n.name, n.age
```

`SET` can be used to update a property on a node or relationship.

```cypher
MATCH (n)
FOREACH (k IN keys(n) | SET n[k + "Copy"] = n[k])
RETURN n.name, keys(n);
```

`SET` can be used to set or update a property dynamically.

```cypher
MATCH (p {name: 'Peter'})
SET p = {name: 'Peter Smith', position: 'Entrepreneur'}
RETURN p.name, p.age, p.position
```

The property replacement operator `=` can be used with `SET` to replace all existing properties on a node or relationship with properties provided by a map.

```cypher
MATCH (p {name: 'Peter'})
SET p = {}
RETURN p.name, p.age
```

All existing properties can be removed from a node or relationship by using `SET` with `=` and an empty map as the right operand.

```cypher
MATCH (p {name: 'Peter'})
SET p += {age: 38, hungry: true, position: 'Entrepreneur'}
RETURN p.name, p.age, p.hungry, p.position
```

The property mutation operator `+=` can be used with `SET` to update existing properties and add new properties from a map with fine-grained control.

```cypher
MATCH (n {name: 'Andy'})
SET n.surname = $surname
RETURN n.name, n.surname
```

Use a parameter to `SET` the value of a property.

```cypher
MATCH (n {name: 'Andy'})
SET n = $props
RETURN n.name, n.position, n.age, n.hungry
```

Update all existing properties on a node using a parameter.

```cypher
MATCH (n {name: 'Stefan'})
SET n:German
RETURN n.name, labels(n) AS labels
```

`SET` a node label.

```cypher
MATCH (n:Swedish)
SET n:$(n.name)
RETURN n.name, labels(n) AS labels
```

`SET` a node label dynamically.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_merge)[MERGE](https://neo4j.com/docs/cypher-manual/25/clauses/merge/)

```cypher
MERGE (robert:Critic:Viewer {name: 'Robert Smith', occupation: 'Journalist'})
RETURN labels(robert) AS labels,
       properties(robert) AS properties
```

The `MERGE` clause either matches existing node patterns in the graph and binds them or, if not present, creates new data and binds that. In this way, it acts as a combination of `MATCH` and `CREATE` that allows for specific actions depending on whether the specified data was matched or created.

```cypher
MERGE (keanu:Person {name: 'Keanu Reeves', bornIn: 'Beirut', chauffeurName: 'Eric Brown'})
ON CREATE
  SET keanu.created = timestamp()
RETURN keanu.name AS name,
       keanu.created AS creationTimestamp
```

Merge a node and set properties if the node needs to be created.

```cypher
MERGE (person:Person)
ON MATCH
  SET person.updatedAt = date()
RETURN person.name AS name,
       person.updatedAt AS updatedAt
ORDER BY name
```

Merge a node and set properties if an existing node is matched.

```cypher
MERGE (keanu:Person {name: 'Keanu Reeves'})
ON CREATE
  SET keanu.created = timestamp()
ON MATCH
  SET keanu.lastSeen = timestamp()
RETURN keanu.name AS name,
       keanu.created AS createdAt,
       keanu.lastSeen AS lastSeen
```

`ON CREATE` and `ON MATCH` can be combined in the same `MERGE` statement.

```cypher
MATCH (charlie:Person {name: 'Charlie Sheen'}),
      (wallStreet:Movie {title: 'Wall Street'})
MERGE (charlie)-[r:ACTED_IN]->(wallStreet)
RETURN charlie.name AS name,
       type(r) AS newRel,
       wallStreet.title AS title
```

Merge a relationship.

```cypher
MERGE (person:Person {name: $param.name, bornIn: $param.bornIn, chauffeurName: $param.chauffeurName})
RETURN person.name AS name,
       person.bornIn AS bornIn,
      person.chauffeurName AS chauffeur
```

`MERGE` properties using parameters.

```cypher
MERGE (greta:$($nodeLabels) {name: 'Greta Gerwig'})
WITH greta
UNWIND $movies AS movieTitle
MERGE (greta)-[rel:$($relType)]->(m:Movie {title: movieTitle})
RETURN greta.name AS name, labels(greta) AS labels, type(rel) AS relType, collect(m.title) AS movies
```

Merge nodes and relationships using dynamic node labels and relationship types.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_delete)[DELETE](https://neo4j.com/docs/cypher-manual/25/clauses/delete/)

```cypher
MATCH (n:Person {name: 'Tom Hanks'})
DELETE n
```

Delete a single node.

```cypher
MATCH (n:Person {name: 'Laurence Fishburne'})-[r:ACTED_IN]->()
DELETE r
```

Delete a single relationship.

```cypher
MATCH (n:Person {name: 'Carrie-Anne Moss'})
DETACH DELETE n
```

Delete a node and all relationships connected to it.

```cypher
MATCH (n)
DETACH DELETE n
```

Delete all nodes and relationships. `DETACH DELETE` is useful when experimenting with small example datasets, but it is not suitable for deleting large amounts of data, nor does it delete indexes or any schema.

```cypher
MATCH (n)
CALL (n) {
 DETACH DELETE n
} IN TRANSACTIONS
```

Delete large amounts of data without deleting indexes and any schema. To remove all data, including indexes and constraints, recreate the database using the following command: `CREATE OR REPLACE DATABASE [name]`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_remove)[REMOVE](https://neo4j.com/docs/cypher-manual/25/clauses/remove/)

```cypher
MATCH (a {name: 'Andy'})
REMOVE a.age
RETURN a.name, a.age
```

Remove a property.

```cypher
MATCH (n)
WITH n, [k IN keys(n) WHERE k CONTAINS "Test" | k] as propertyKeys (1)
FOREACH (i IN propertyKeys | REMOVE n[i]) (2)
RETURN n.name, keys(n);
```

Dynamically remove a property.

```cypher
MATCH (n {name: 'Peter'})
REMOVE n:German
RETURN n.name, labels(n)
```

Remove a node label.

MATCH (n {name: 'Peter'})
UNWIND labels(n) AS label
REMOVE n:$(label)
RETURN n.name, labels(n)

Dynamically remove a node label.

```cypher
MATCH (n {name: 'Peter'})
REMOVE n:German:Swedish
RETURN n.name, labels(n)
```

Remove multiple node labels.

```cypher
MATCH (n {name: 'Peter'})
REMOVE n:$(labels(n))
RETURN n.name, labels(n)
```

Dynamically remove multiple node labels.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_cypher_query_versioning)Cypher query versioning

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_select_cypher_version_for_queries)[Select Cypher version for queries](https://neo4j.com/docs/cypher-manual/25/queries/select-version/)

```cypher
CYPHER 25
MATCH (n:Order)-[r:SHIPPED_TO]->(:Address)
SET n = properties(r)
```

Prepending a query with `CYPHER 25` ensures that the query will be executed using Cypher 25 as it exists in the version of Neo4j that the database is currently running, provided it is on Neo4j 2025.06 or later.

```cypher
CYPHER 5
MATCH (n:Order)-[r:SHIPPED_TO]->(:Address)
SET n = r
```

Selecting `CYPHER 5` ensures that the query will be executed using the Cypher 5 as it existed at the time of the Neo4j 2025.06 release. Any changes introduced after the 2025.06 release will not affect the query.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_composed_queries)Composed queries

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_combined_queries_union)[Combined queries (UNION)](https://neo4j.com/docs/cypher-manual/25/queries/composed-queries/combined-queries/)

```cypher
MATCH (n:Actor)
RETURN n.name AS name
UNION
MATCH (n:Movie)
RETURN n.title AS name
```

Return the distinct union of all query results. Result column types and names must match.

```cypher
MATCH (n:Actor)
RETURN n.name AS name
UNION ALL
MATCH (n:Movie)
RETURN n.title AS name
```

Return the union of all query results, including duplicate rows.

```cypher
CALL () {
  MATCH (a:Actor)
  RETURN a.name AS name
UNION ALL
  MATCH (m:Movie)
  RETURN m.title AS name
}
RETURN name, count(*) AS count
ORDER BY count
```

The `UNION` clause can be used within a `CALL` subquery to further process the combined results before a final output is returned.

```cypher
{
   MATCH (n:Actor)
   RETURN n.name AS name
   UNION
   MATCH (n:Director)
   RETURN n.name AS name
}
UNION ALL
MATCH (n:Movie)
RETURN n.title AS name
```

To combine `UNION` (or `UNION DISTINCT`) and `UNION ALL` in the same query, enclose one or more `UNION` operations of the same type in curly braces. This allows the enclosed query to act as an argument that can be combined with an outer `UNION` operation of any type.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_conditional_queries_when)[Conditional queries (WHEN)](https://neo4j.com/docs/cypher-manual/25/queries/composed-queries/combined-queries/)

```cypher
WHEN false THEN RETURN 1 AS x
WHEN true THEN RETURN 2 AS x
WHEN true THEN RETURN 3 AS x
ELSE RETURN 3 AS x
```

`WHEN`, together with `THEN` and `ELSE`, enables different branches of a query to execute based on certain conditions. The first branch with a predicate that evaluates to `true` will be executed. If no `WHEN` branches are executed and an `ELSE` branch exists, it is executed. If no `WHEN` branches evaluates to `true` and no `ELSE` branch is present, no branches are executed and no rows are produced.

```cypher
WHEN true THEN {
  MATCH (n:Person) WHERE n.name STARTS WITH "A"
  RETURN n.name AS name
}
ELSE {
  MATCH (n:Person)
  RETURN n.name AS name
}
```

Queries can be executed conditionally executed in standalone `WHEN` branches.

```cypher
MATCH (n:Person)
OPTIONAL MATCH (n)-[:WORKS_FOR]->(manager:Person)
CALL (*) {
  WHEN manager IS NULL THEN {
    MERGE (newManager: Person {name: 'Peter', age: 36})
    MERGE (n)-[:WORKS_FOR]->(newManager)
    RETURN newManager, n.name AS employee
  }
}
RETURN newManager.name AS newManager,
       collect(employee) AS employees
```

`WHEN` can be used inside one or several `CALL` subqueries to execute a set of operations only when a specified condition evaluates to `true`.

```cypher
MATCH (n:Person)
WHERE EXISTS {
  WHEN n.age > 40 THEN {
    RETURN n.name AS x
  }
  ELSE {
    MATCH (n)-[:LOVES]->(x:Person)
    RETURN x
  }
}
RETURN n.name AS name,
       n.age AS age
```

`EXISTS`, `COLLECT`, and `COUNT` subquery expressions can also contain `WHEN` branches.

```cypher
{
  WHEN true THEN RETURN 1 AS x
  WHEN false THEN RETURN 2 AS x
  ELSE RETURN 3 AS x
}
UNION
{
  WHEN false THEN RETURN 4 AS x
  WHEN false THEN RETURN 5 AS x
  ELSE RETURN 6 AS x
}
```

The results of multiple conditional queries can also be combined using `UNION [DISTINCT]` or `UNION ALL`. If the conditional query begins with `WHEN` and involves `UNION`, the `WHEN` branches **must** be enclosed within curly braces, `{}`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_sequential_queries_next)[Sequential queries (NEXT)](https://neo4j.com/docs/cypher-manual/25/queries/composed-queries/sequential-queries/)

```cypher
MATCH (c:Customer)
RETURN c AS customer

NEXT

MATCH (customer)-[:BUYS]->(:Product {name: 'Chocolate'})
RETURN customer.firstName AS chocolateCustomer
```

`NEXT` allows for linear composition of queries into a sequence of smaller, self-contained segments, passing the return values from one segment to the next.

```cypher
MATCH (c:Customer)-[:BUYS]->(p:Product)
RETURN c AS customer, p AS product

NEXT

RETURN product.name AS product,
       COUNT(customer) AS numberOfCustomers
```

`NEXT` passes the result table as a whole to the subsequent query. This is particularly useful when aggregating values.

```cypher
MATCH (c:Customer)-[:BUYS]->(p:Product)
RETURN c, p

NEXT

RETURN c.firstName AS name, COLLECT(p.price * (1 - c.discount)) AS purchases, "discounted price" AS type
UNION
RETURN c.firstName AS name, COLLECT(p.price) AS purchases, "real price" AS type

NEXT

RETURN * ORDER BY name, type
```

If a `UNION` query follows a `NEXT` the full table of intermediate results is passed into all arms of the `UNION` query.

```cypher
MATCH (c:Customer)-[:BUYS]->(:Product)<-[:SUPPLIES]-(s:Supplier)
RETURN c.firstName AS customer, s.name AS supplier

NEXT

WHEN supplier = "TechCorp" THEN
  RETURN customer, "Tech enjoyer" AS personality
WHEN supplier = "Foodies Inc." THEN
  RETURN customer, "Tropical plant enjoyer" AS personality

NEXT

RETURN customer, collect(DISTINCT personality) AS personalities

NEXT

WHEN size(personalities) > 1 THEN
  RETURN customer, "Enjoyer of tech and plants" AS personality
ELSE
  RETURN customer, personalities[0] AS personality
```

`NEXT` can be used to chain conditional `WHEN` constructs.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_patterns)Patterns

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_fixed_length_paths)[Fixed-length paths](https://neo4j.com/docs/cypher-manual/25/patterns/fixed-length-paths/)

```cypher
MATCH (n:Station WHERE n.name STARTS WITH 'Preston')
RETURN n
```

Match a node pattern including a `WHERE` clause predicate.

```cypher
MATCH (s:Stop)-[:CALLS_AT]->(:Station {name: 'Denmark Hill'})
RETURN s.departs AS departureTime
```

Match a fixed-length path pattern to paths in a graph.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_variable_length_paths)[Variable-length paths](https://neo4j.com/docs/cypher-manual/25/patterns/variable-length-paths/)

```cypher
MATCH (:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(d:Stop)
      ((:Stop)-[:NEXT]->(:Stop)){1,3}
      (a:Stop)-[:CALLS_AT]->(:Station { name: 'Clapham Junction' })
RETURN d.departs AS departureTime, a.arrives AS arrivalTime
```

Quantified path pattern matching a sequence of paths whose length is constrained to a specific range (1 to 3 in this case) between two nodes.

```cypher
MATCH (d:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-
        (n:Stop)-[:NEXT]->{1,10}(m:Stop)-[:CALLS_AT]->
        (a:Station { name: 'Clapham Junction' })
WHERE m.arrives < time('17:18')
RETURN n.departs AS departureTime
```

Quantified relationship matching paths where a specified relationship occurs between 1 and 10 times.

```cypher
MATCH (bfr:Station {name: "London Blackfriars"}),
      (ndl:Station {name: "North Dulwich"})
MATCH p = (bfr)
          ((a)-[:LINK]-(b:Station)
            WHERE point.distance(a.location, ndl.location) >
              point.distance(b.location, ndl.location))+ (ndl)
RETURN reduce(acc = 0, r in relationships(p) | round(acc + r.distance, 2))
  AS distance
```

Quantified path pattern including a predicate.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_non_linear_paths)[Non-linear paths](https://neo4j.com/docs/cypher-manual/25/patterns/non-linear-paths/)

```cypher
MATCH (n:Station {name: 'London Euston'})<-[:CALLS_AT]-(s1:Stop)
  -[:NEXT]->(s2:Stop)-[:CALLS_AT]->(:Station {name: 'Coventry'})
  <-[:CALLS_AT]-(s3:Stop)-[:NEXT]->(s4:Stop)-[:CALLS_AT]->(n)
RETURN s1.departs+'-'+s2.departs AS outbound,
  s3.departs+'-'+s4.departs AS `return`
```

An equijoin is an operation on paths that requires more than one of the nodes or relationships of the paths to be the same. The equality between the nodes or relationships is specified by declaring a node variable or relationship variable more than once. An equijoin on nodes allows cycles to be specified in a path pattern. Due to relationship uniqueness, an equijoin on relationships yields no solutions.

```cypher
MATCH (:Station {name: 'Starbeck'})<-[:CALLS_AT]-
        (a:Stop {departs: time('11:11')})-[:NEXT]->*(b)-[:NEXT]->*
        (c:Stop)-[:CALLS_AT]->(lds:Station {name: 'Leeds'}),
      (b)-[:CALLS_AT]->(l:Station)<-[:CALLS_AT]-(m:Stop)-[:NEXT]->*
        (n:Stop)-[:CALLS_AT]->(lds),
      (lds)<-[:CALLS_AT]-(x:Stop)-[:NEXT]->*(y:Stop)-[:CALLS_AT]->
        (:Station {name: 'Huddersfield'})
WHERE b.arrives < m.departs AND n.arrives < x.departs
RETURN a.departs AS departs,
       l.name AS changeAt,
       m.departs AS changeDeparts,
       y.arrives AS arrives
ORDER BY y.arrives LIMIT 1
```

Multiple path patterns can be combined in a comma-separated list to form a graph pattern. In a graph pattern, each path pattern is matched separately, and where node variables are repeated in the separate path patterns, the solutions are reduced via equijoins.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_shortest_paths)[Shortest paths](https://neo4j.com/docs/cypher-manual/25/patterns/shortest-paths/)

```cypher
MATCH p = SHORTEST 1 (wos:Station)-[:LINK]-+(bmv:Station)
WHERE wos.name = "Worcester Shrub Hill" AND bmv.name = "Bromsgrove"
RETURN length(p) AS result
```

`SHORTEST k` finds the shortest path(s) (by number of hops) between nodes, where `k` is the number of paths to match.

```cypher
MATCH p = ALL SHORTEST (wos:Station)-[:LINK]-+(bmv:Station)
WHERE wos.name = "Worcester Shrub Hill" AND bmv.name = "Bromsgrove"
RETURN [n in nodes(p) | n.name] AS stops
```

Find all shortest paths between two nodes.

```cypher
MATCH p = SHORTEST 2 GROUPS (wos:Station)-[:LINK]-+(bmv:Station)
WHERE wos.name = "Worcester Shrub Hill" AND bmv.name = "Bromsgrove"
RETURN [n in nodes(p) | n.name] AS stops, length(p) AS pathLength
```

`SHORTEST k GROUPS` returns all paths that are tied for first, second, and so on, up to the kth shortest length. This example finds all paths with the first and second shortest lengths between two nodes.

```cypher
MATCH path = ANY
  (:Station {name: 'Pershore'})-[l:LINK WHERE l.distance < 10]-+(b:Station {name: 'Bromsgrove'})
RETURN [r IN relationships(path) | r.distance] AS distances
```

The `ANY` keyword can be used to test the reachability of nodes from a given node(s). It returns the same as `SHORTEST 1`, but by using the `ANY` keyword the intent of the query is clearer.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_paths_with_unique_relationships)[Paths with unique relationships](https://neo4j.com/docs/cypher-manual/25/patterns/unique-relationship-paths/)

```cypher
MATCH p = (:Location {name: 'Kneiphof'})--{7}()
RETURN count(p) AS pathCount
```

By default, Cypher only prevents relationships being repeated in a `MATCH` result, not nodes. This behavior can be explicitly defined by adding the `DIFFERENT RELATIONSHIPS` keyword after `MATCH`, though this does not alter the rules how patterns are matched in Cypher.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_paths_with_repeatable_nodes_and_relationships)[Paths with repeatable nodes and relationships](https://neo4j.com/docs/cypher-manual/25/patterns/repeatable-node-and-relationship-paths/)

```cypher
MATCH REPEATABLE ELEMENTS p = (:Location {name: 'Kneiphof'})-[:BRIDGE]-{7}()
WITH collect(p)[0] AS samplePath
RETURN [n IN nodes(samplePath) | n.name] AS samplePathLocations,
       [r IN relationships(samplePath) | r.id] AS samplePathBridges
```

Cypher’s default behavior of not allowing repeated relationships in a graph pattern match can be bypassed using the `REPEATABLE ELEMENTS` keyword, which ensures there are no restrictions on how many times a node or relationship can occur for a given `MATCH` result.

Queries using `REPEATABLE ELEMENTS` must specify an upper bound to a pattern to ensure that a finite number of solutions are returned in a finite amount of time (i.e. quantifiers such as `*`, `+`, or `{1,}` are not allowed using `REPEATABLE ELEMENTS`).

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_acyclic_paths)[Acyclic paths](https://neo4j.com/docs/cypher-manual/25/patterns/acyclic-paths/)

```cypher
MATCH p = ACYCLIC (:Router {name: 'A'})-[:LINK]-+(:Router {name: 'Z'})
RETURN [n IN nodes(p) | n.name] AS routeWithoutCycles
ORDER BY p LIMIT 1
```

Prepending a path pattern with the `ACYCLIC` keyword ensure that neither nodes or relationships can be repeated within a path, but nodes can still be repeated across paths to form equijoins.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_clauses)Clauses

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_finish)[FINISH](https://neo4j.com/docs/cypher-manual/25/clauses/finish/)

```cypher
MATCH (p:Person)
FINISH
```

A query ending in `FINISH` — instead of `RETURN` — has no result but executes all its side effects.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_for)[FOR](https://neo4j.com/docs/cypher-manual/25/clauses/for/)

```cypher
FOR x IN [1, 2, 3, null]
RETURN x, 'val' AS y
```

The `FOR` clause makes it possible to transform any list back into individual rows. It is functionally equivalent to `UNWIND`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_foreach)[FOREACH](https://neo4j.com/docs/cypher-manual/25/clauses/foreach/)

```cypher
MATCH p=(start)-[*]->(finish)
WHERE start.name = 'A' AND finish.name = 'D'
FOREACH (n IN nodes(p) | SET n.marked = true)
```

`FOREACH` can be used to update data, such as executing update commands on elements in a path, or on a list created by aggregation. This example sets the property `marked` to `true` on all nodes along a path.

```cypher
MATCH p=(start)-[*]->(finish)
WHERE start.name = 'A' AND finish.name = 'D'
FOREACH ( r IN relationships(p) | SET r.marked = true )
```

This example sets the property `marked` to `true` on all relationships along a path.

```cypher
WITH ['E', 'F', 'G'] AS names
FOREACH ( value IN names | CREATE (:Person {name: value}) )
```

This example creates a new node for each label in a list.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_limit)[LIMIT](https://neo4j.com/docs/cypher-manual/25/clauses/limit/)

```cypher
MATCH (n)
ORDER BY n.name DESC
SKIP 2
LIMIT 2
RETURN collect(n.name) AS names
```

`LIMIT` constrains the number of returned rows. It can be used in conjunction with [`ORDER BY`](https://neo4j.com/docs/cypher-manual/25/clauses/order-by/) and [`SKIP`](https://neo4j.com/docs/cypher-manual/25/clauses/skip/).

```cypher
MATCH (n)
LIMIT 2
RETURN collect(n.name) AS names
```

`LIMIT` can be used as a standalone clause.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_load_csv)[LOAD CSV](https://neo4j.com/docs/cypher-manual/25/clauses/load-csv/)

```cypher
LOAD CSV FROM 'file:///artists.csv' AS row
MERGE (a:Artist {name: row[1], year: toInteger(row[2])})
RETURN a.name, a.year
```

`LOAD CSV` is used to import data from CSV files into a Neo4j database. This example imports the name and year information of artists from a local file.

```cypher
LOAD CSV FROM 'https://data.neo4j.com/bands/artists.csv' AS row
MERGE (a:Artist {name: row[1], year: toInteger(row[2])})
RETURN a.name, a.year
```

Import artists name and year information from a remote file URL.

```cypher
LOAD CSV WITH HEADERS FROM 'file:///bands-with-headers.csv' AS line
MERGE (n:$(line.Label) {name: line.Name})
RETURN n AS bandNodes
```

CSV columns can be referenced dynamically to map labels to nodes in the graph. This enables flexible data handling, allowing labels to be be populated from CSV column values without manually specifying each entry.

```cypher
LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/persons.csv' AS row
CALL (row) {
  MERGE (p:Person {tmdbId: row.person_tmdbId})
  SET p.name = row.name, p.born = row.born
} IN TRANSACTIONS OF 200 ROWS
```

Load a CSV file in several [transactions](https://neo4j.com/docs/cypher-manual/25/subqueries/subqueries-in-transactions/). This example uses a [variable scope clause](https://neo4j.com/docs/cypher-manual/current/subqueries/call-subquery/#variable-scope-clause) (introduced in Neo4j 5.23) to import variables into the `CALL` subquery.

```cypher
LOAD CSV FROM 'file:///artists.csv' AS row
RETURN linenumber() AS number, row
```

Access line numbers in a CSV with the [`linenumber()`](https://neo4j.com/docs/cypher-manual/25/functions/load-csv/#functions-linenumber) function.

```cypher
LOAD CSV FROM 'file:///artists.csv' AS row
RETURN DISTINCT file() AS path
```

Access the CSV file path with the [`file()`](https://neo4j.com/docs/cypher-manual/25/functions/load-csv/#functions-file) function.

```cypher
LOAD CSV WITH HEADERS FROM 'file:///artists-with-headers.csv' AS row
MERGE (a:Artist {name: row.Name, year: toInteger(row.Year)})
RETURN
  a.name AS name,
  a.year AS year
```

Load CSV data with headers.

```cypher
LOAD CSV FROM 'file:///artists-fieldterminator.csv' AS row FIELDTERMINATOR ';'
MERGE (:Artist {name: row[1], year: toInteger(row[2])})
```

Import a CSV using `;` as field delimiter.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_order_by)[ORDER BY](https://neo4j.com/docs/cypher-manual/25/clauses/order-by/)

```cypher
MATCH (o:Order)
RETURN o.id AS order,
       o.total AS total
  ORDER BY total
```

`ORDER BY` specifies how the output of a clause should be sorted. It can be used as a sub-clause following [`RETURN`](https://neo4j.com/docs/cypher-manual/25/clauses/return/) or [`WITH`](https://neo4j.com/docs/cypher-manual/25/clauses/with/).

```cypher
MATCH (o:Order)
RETURN o.id AS order,
       o.total AS total,
       o.orderDate AS orderDate
  ORDER BY total,
           orderDate
```

You can order by multiple properties by stating each variable in the `ORDER BY` clause.

```cypher
MATCH (i:Item)
ORDER BY i.price DESC
SKIP 1
LIMIT 1
RETURN i.name AS secondMostExpensiveItem,
       i.price AS price
```

By adding `DESC[ENDING]` after the variable to sort on, the sort will be done in reverse order.

`ORDER BY` can be used in conjunction with `SKIP` and `LIMIT`.

```cypher
MATCH (i:Item)
ORDER BY i.price
RETURN collect(i.name || " ($" || toString(i.price) || ")") AS orderedPriceList
```

`ORDER BY` can be used as a standalone clause.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show)[SHOW](https://neo4j.com/docs/cypher-manual/25/clauses/show/)

```cypher
SHOW INDEXES
```

The `SHOW` command can be used to show the metadata of a database or a DBMS The following variations of the command are available:

-   [`SHOW AUTH RULES`](https://neo4j.com/docs/operations-manual/current/authentication-authorization/attribute-based-access-control/#_showing_auth_rules)

-   [`SHOW ALIASES`](https://neo4j.com/docs/operations-manual/current/database-administration/syntax/#_show_aliases)

-   [`SHOW CONSTRAINTS`](https://neo4j.com/docs/cypher-manual/25/schema/constraints/list-constraints/)

-   [`SHOW CURRENT GRAPH TYPE`](https://neo4j.com/docs/cypher-manual/25/schema/graph-types/list-graph-types/)

-   [`SHOW DATABASES`](https://neo4j.com/docs/operations-manual/current/database-administration/standard-databases/listing-databases/)

-   [`SHOW FUNCTIONS`](https://neo4j.com/docs/cypher-manual/25/functions/show-functions/)

-   [`SHOW INDEXES`](https://neo4j.com/docs/cypher-manual/25/indexes/search-performance-indexes/list-indexes/)

-   [`SHOW PRIVILEGES`](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-privileges/#access-control-list-privileges)

-   [`SHOW PROCEDURES`](https://neo4j.com/docs/operations-manual/current/procedures/show-procedures/)

-   [`SHOW ROLES`](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-roles/#access-control-list-roles)

-   [`SHOW SERVERS`](https://neo4j.com/docs/operations-manual/current/clustering/server-syntax/#_show_servers)

-   [`SHOW SETTINGS`](https://neo4j.com/docs/operations-manual/current/configuration/show-settings/)

-   [`SHOW TRANSACTIONS`](https://neo4j.com/docs/operations-manual/current/database-internals/show-and-terminate-transactions/#show-transactions)

-   [`SHOW USERS`](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/#access-control-list-users)


When used without `YIELD`, the `SHOW` commands only return the default columns.

```cypher
SHOW INDEXES
YIELD name, type, indexProvider
```

`YIELD` can be used to only return specific columns.

```cypher
SHOW INDEXES
YIELD *
```

If `YIELD *` is used, all columns are returned (both default and non-default).

```cypher
SHOW SETTINGS YIELD name, value, description
WHERE name STARTS WITH 'server'
RETURN name, value, description
```

All `SHOW` commands can be filtered using the `WHERE` clause. If the `RETURN` clause is used, `YIELD` is mandatory.

```cypher
SHOW PROCEDURES
YIELD name, signature
RETURN name, signature, 'procedure' AS type
UNION
SHOW FUNCTIONS
YIELD name, signature
RETURN name, signature, 'function' AS type
```

The following `SHOW` commands can be combined with general Cypher clauses:

-   `SHOW CONSTRAINTS`

-   `SHOW CURRENT GRAPH TYPE`

-   `SHOW DATABASES`

-   `SHOW FUNCTIONS`

-   `SHOW INDEXES`

-   `SHOW PROCEDURES`

-   `SHOW SETTINGS`

-   `SHOW TRANSACTIONS`


When combining a `SHOW` command with other clauses, the `YIELD` clause is mandatory and must not be omitted. `YIELD` must explicitly list the yielded columns. `YIELD *` is not permitted. The query must also end with a valid last clause (like a `RETURN` or an updating clause).

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_skip)[SKIP](https://neo4j.com/docs/cypher-manual/25/clauses/skip/)

```cypher
MATCH (n)
RETURN n.name
ORDER BY n.name
SKIP 1
LIMIT 2
```

`SKIP` defines from which row to start including the rows in the output. It can be used in conjunction with [`LIMIT`](https://neo4j.com/docs/cypher-manual/25/clauses/limit/) and [`ORDER BY`](https://neo4j.com/docs/cypher-manual/25/clauses/order-by/).

```cypher
MATCH (n)
SKIP 2
RETURN collect(n.name) AS names
```

`SKIP` can be used as a standalone clause.

```cypher
MATCH (n)
ORDER BY n.name
OFFSET 2
LIMIT 2
RETURN collect(n.name) AS names
```

`OFFSET` can be used as a synonym to `SKIP`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_unwind)[UNWIND](https://neo4j.com/docs/cypher-manual/25/clauses/unwind/)

```cypher
UNWIND [1, 2, 3, null] AS x
RETURN x, 'val' AS y
```

The `UNWIND` clause expands a list into a sequence of rows.

Four rows are returned.

```cypher
UNWIND $events AS event
MERGE (y:Year {year: event.year})
MERGE (y)<-[:IN]-(e:Event {id: event.id})
RETURN e.id AS x ORDER BY x
```

Multiple `UNWIND` clauses can be chained to unwind nested list elements.

Five rows are returned.

```cypher
UNWIND [1, 2, 3, null] AS x
RETURN x, 'val' AS y
```

Create a number of nodes and relationships from a parameter-list without using `FOREACH`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_use)[USE](https://neo4j.com/docs/cypher-manual/25/clauses/use/)

```cypher
USE myDatabase
MATCH (n) RETURN n
```

The `USE` clause determines which graph a query is executed against. This example assumes that the DBMS contains a database named `myDatabase`.

```cypher
USE myComposite.myConstituent
MATCH (n) RETURN n
```

This example assumes that the DBMS contains a composite database named `myComposite`, which includes an alias named `myConstituent`.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_subqueries)Subqueries

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_call)[CALL](https://neo4j.com/docs/cypher-manual/25/subqueries/call-subquery/)

```cypher
UNWIND [0, 1, 2] AS x
CALL () {
  RETURN 'hello' AS innerReturn
}
RETURN innerReturn
```

A `CALL` subquery is executed once for each row. In this example, the `CALL` subquery executes three times.

```cypher
MATCH (t:Team)
CALL (t) {
  MATCH (p:Player)-[:PLAYS_FOR]->(t)
  RETURN collect(p) as players
}
RETURN t AS team, players
```

Variables are imported into a `CALL` subquery using a [variable scope clause](https://neo4j.com/docs/cypher-manual/current/subqueries/call-subquery/#variable-scope-clause), `CALL (<variable>)`, or an [importing `WITH` clause](https://neo4j.com/docs/cypher-manual/current/subqueries/call-subquery/#importing-with) (deprecated). In this example, the subquery will process each `Team` at a time and `collect` a list of all `Player` nodes.

```cypher
MATCH (p:Player)
OPTIONAL CALL (p) {
    MATCH (p)-[:PLAYS_FOR]->(team:Team)
    RETURN team
}
RETURN p.name AS playerName, team.name AS team
```

Optionally `CALL` a subquery. Similar to OPTIONAL MATCH, any empty rows produced by the `OPTIONAL CALL` will return `null` and not affect the remainder of the subquery evaluation.

```cypher
CALL () {
  MATCH (p:Player)
  RETURN p
  ORDER BY p.age ASC
  LIMIT 1
UNION
  MATCH (p:Player)
  RETURN p
  ORDER BY p.age DESC
  LIMIT 1
}
RETURN p.name AS playerName, p.age AS age
```

`CALL` subqueries can be used to further process the results of a `UNION` query. This example finds the youngest and the oldest `Player` in the graph.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_call_subqueries_in_transactions)[CALL subqueries in transactions](https://neo4j.com/docs/cypher-manual/25/subqueries/subqueries-in-transactions/)

```cypher
LOAD CSV FROM 'file:///friends.csv' AS line
CALL (line) {
  CREATE (:Person {name: line[1], age: toInteger(line[2])})
} IN TRANSACTIONS
```

`CALL` subqueries can execute in separate, inner transactions, producing intermediate commits.

```cypher
LOAD CSV FROM 'file:///friends.csv' AS line
CALL (line) {
  CREATE (:Person {name: line[1], age: toInteger(line[2])})
} IN TRANSACTIONS OF 2 ROWS
```

Specify the number of rows processed in each transaction.

```cypher
UNWIND [1, 0, 2, 4] AS i
CALL (i) {
  CREATE (n:Person {num: 100/i}) // Note, fails when i = 0
  RETURN n
} IN TRANSACTIONS
  OF 1 ROW
  ON ERROR CONTINUE
RETURN n.num
```

There are four different option flags to control the behavior in case of an error occurring in any of the inner transactions:

-   `ON ERROR CONTINUE` - ignores a recoverable error and continues the execution of subsequent inner transactions. The outer transaction succeeds.

-   `ON ERROR BREAK` - ignores a recoverable error and stops the execution of subsequent inner transactions. The outer transaction succeeds.

-   `ON ERROR FAIL` - acknowledges a recoverable error and stops the execution of subsequent inner transactions. The outer transaction fails.

-   `ON ERROR RETRY` - uses an exponential delay between retry attempts for transaction batches that fail due to transient errors (i.e. errors where retrying a transaction can be expected to give a different result), with an optional maximum retry duration. If the transaction still fails after the maximum duration, the failure is handled according to an optionally specified fallback error handling mode (`THEN CONTINUE`, `THEN BREAK`, `THEN FAIL` (default)).


```cypher
LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/persons.csv' AS row
CALL (row) {
  CREATE (p:Person {tmdbId: row.person_tmdbId})
  SET p.name = row.name, p.born = row.born
} IN 3 CONCURRENT TRANSACTIONS OF 10 ROWS
RETURN count(*) AS personNodes
```

`CALL` subqueries can execute batches in parallel by appending `IN [n] CONCURRENT TRANSACTIONS`, where `n` is an optional concurrency value used to set the maximum number of transactions that can be executed in parallel.

```cypher
LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/movies.csv' AS row
CALL (row) {
   MERGE (m:Movie {movieId: row.movieId})
   MERGE (y:Year {year: row.year})
   MERGE (m)-[r:RELEASED_IN]->(y)
} IN 2 CONCURRENT TRANSACTIONS OF 10 ROWS ON ERROR RETRY FOR 3 SECONDS THEN CONTINUE REPORT STATUS AS status
RETURN status.transactionId as transaction, status.committed AS successfulTransaction
```

`ON ERROR RETRY …​ THEN CONTINUE` can be used to retry the execution of a transaction for a specified maximum duration before continuing the execution of subsequent inner transactions by ignoring any recoverable errors.

```cypher
LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/movies.csv' AS line
CALL (line) {
  MERGE (m:Movie {movieId: line.movieId})
  MERGE (y:Year {year: line.year})
  MERGE (m)-[:RELEASED_IN]->(y)
} IN CONCURRENT TRANSACTIONS
  DISJOINT BY (line.year, line.movieId)
  ON ERROR RETRY THEN CONTINUE
```

`DISJOINT BY` can be added to individual `CALL { …​ } IN CONCURRENT TRANSACTIONS` statements to control batch scheduling at the query level. Batch scheduling prevents deadlocks in concurrent transactions by ensuring that batches sharing resources never run at the same time, while batches that do not share resources run concurrently.

There are three forms of `DISJOINT BY`:

-   `DISJOINT BY (<expr>, …​)`: declares lock-prone resources explicitly per row.

-   `DISJOINT BY AUTO`: the runtime infers lock-prone resources automatically.

-   `DISJOINT BY NONE`: disables scheduling explicitly, overriding any database-level default set by [`dbms.cypher.transactions.default_subquery_batch_strategy`](https://neo4j.com/docs/operations-manual/current/configuration/configuration-settings/#config_dbms.cypher.transactions.default_subquery_batch_strategy).


### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_count_collect_and_exists)[COUNT, COLLECT, and EXISTS](https://neo4j.com/docs/cypher-manual/25/subqueries)

```cypher
MATCH (person:Person)
WHERE COUNT { (person)-[:HAS_DOG]->(:Dog) } > 1
RETURN person.name AS name
```

A `COUNT` subquery counts the number of rows returned by the subquery. Unlike `CALL` subqueries, variables introduced by the outer scope can be used in `EXISTS`, `COLLECT`, and `COUNT` subqueries.

```cypher
MATCH (person:Person)
WHERE EXISTS {
  MATCH (person)-[:HAS_DOG]->(dog:Dog)
  WHERE person.name = dog.name
}
RETURN person.name AS name
```

An `EXISTS` subquery determines if a specified pattern exists at least once in the graph. A `WHERE` clause can be used inside `COLLECT`, `COUNT`, and `EXISTS` patterns.

```cypher
MATCH (person:Person) WHERE person.name = "Peter"
SET person.dogNames = COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }
RETURN person.dogNames as dogNames
```

A `COLLECT` subquery creates a list with the rows returned by the subquery. `COLLECT`, `COUNT`, and `EXISTS` subqueries can be used inside other clauses.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_predicates)Predicates

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_boolean_operators)[Boolean operators](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/boolean-operators/)

```cypher
MATCH (n:Person)
WHERE n.age > 30 AND n.role = 'Software developer'
RETURN n.name AS name, n.age AS age, n.role AS role
```

The `AND` operator is used to combine multiple boolean expressions, returning `true` only if all conditions are true.

```cypher
MATCH (n:Person)
WHERE n.age < 30 OR n.role = 'Software developer'
RETURN n.name AS name, n.age AS age, n.role AS role
```

The `OR` operator is used to combine multiple boolean expressions, returning `true` if at least one of the conditions is true.

```cypher
MATCH (n:Person)
WHERE n.age > 30 XOR n.role = 'Software developer'
RETURN n.name AS name, n.age AS age, n.role AS role
```

The `XOR` operator returns `true` if exactly one of the two boolean expressions is true, but not both.

```cypher
MATCH (n:Person)
WHERE NOT n.age = 39
RETURN n.name AS name, n.age AS age
```

The `NOT` operator negates a boolean expression, returning `true` if the expression is false and `false` if it is true.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_comparison_operators)[Comparison operators](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/comparison-operators/)

```cypher
MATCH (n:Person)
WHERE n.role = 'Software developer'
RETURN n.name AS name, n.role AS role
```

The equality operator `=` checks for equality between two values.

```cypher
MATCH (n:Person)
WHERE n.role <> 'Software developer'
RETURN n.name AS name, n.role AS role
```

The inequality operator `<>` checks if two values are not equal.

```cypher
MATCH (n:Person)
WHERE n.age < 39
RETURN n.name AS name, n.age AS age
```

The less than operator `<` returns `true` if the value on the left is less than the value on the right.

```cypher
MATCH (n:Person)
WHERE n.age <= 39
RETURN n.name AS name, n.age AS age
```

The less than or equal or operator `<=` returns `true` if the value on the left is less than or equal to the value on the right.

```cypher
MATCH (n:Person)
WHERE n.age > 39
RETURN n.name AS name, n.age AS age
```

The greater than operator `>` returns `true` if the value on the left is greater than the value on the right.

```cypher
MATCH (n:Person)
WHERE n.age >= 39
RETURN n.name AS name, n.age AS age
```

The greater than or equal operator `>=` returns `true` if the value on the left is greater than the value on the right.

```cypher
MATCH (n:Person)
WHERE n.email IS NULL
RETURN n.name AS name
```

The `IS NULL` operator returns `true` if the value is `NULL`, and `false` otherwise.

```cypher
MATCH (n:Person)
WHERE n.email IS NOT NULL
RETURN n.name AS name, n.email AS email
```

The `IS NOT NULL` operator returns `true` if the value is not `NULL`, and `false` otherwise.

```cypher
MATCH (n:Person)
WHERE PROPERTY_EXISTS(n, email)
RETURN n.name AS name, n.email AS email
```

The `PROPERTY_EXISTS` predicate returns `true` if the value is not `NULL`, and `false` otherwise. Unlike `IS NOT NULL`, `PROPERTY_EXISTS` can only check node and relationship properties.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_label_expression_predicates)[Label expression predicates](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/label-expression-predicates/)

```cypher
MATCH (p:Person)
RETURN p.name AS name, p:Manager AS isManager
```

Use a colon (`:`) to verify that the labels of a node match a given label expression.

```cypher
MATCH (p:Person)
RETURN p.name AS name, p IS LABELED Manager AS isManager
```

The `IS [NOT] LABELED` predicate can be used to verify that the labels of a node match a given label expression.

```cypher
MATCH ()-[r]->(p:Person)
UNWIND labels(p) AS label
FILTER label <> "Person"
RETURN COLLECT(label) AS managerLabels
NEXT
MATCH (p)
RETURN p.name AS name, p:$any(managerLabels) AS isManager
```

A label expression predicate can be used to match a dynamic label expression

```cypher
MATCH (p:Person)-[r]->()
RETURN p.name AS name,
       r:WORKS_FOR AS isNotManager
```

Label expression predicate to test that the type of a relationship match a given label expression.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_list_operators)[List operators](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/list-operators/)

```cypher
MATCH (n:Person)
WHERE n.role IN ['Software developer', 'Project manager']
RETURN n.name AS name, n.role AS role
```

The `IN` operator checks if a value is present in a `LIST`.

```cypher
RETURN any(x IN [1, 2, null] WHERE x IS NULL) AS containsNull
```

To check if `NULL` is a member of a `LIST`, use the [`any()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-any) function.

```cypher
RETURN [3, 4] IN [[1, 2], [3, 4]] AS listInNestedList
```

When used with nested `LIST` values, the `IN` operator evaluates whether a `LIST` is an exact match to any of the nested `LIST` values that are part of an outer `LIST`. Partial matches of individual elements within a nested `LIST` will return `false`.

```cypher
WITH [1,3,4] AS sub, [3,5,1,7,6,2,8,4] AS list
RETURN all(x IN sub WHERE x IN list) AS subInList
```

A subset check using the [`all()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-all) function verifies if all elements of one `LIST` exist in another.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_path_pattern_expressions)[Path pattern expressions](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/path-pattern-expressions/)

```cypher
MATCH (employee:Person)
WHERE (employee)-[:WORKS_FOR]->(:Person {name: 'Alice'})
RETURN employee.name AS employee
```

Similar to [`EXISTS` subqueries](https://neo4j.com/docs/cypher-manual/25/subqueries/existential/), path pattern expressions can be used to assert whether a specified path exists at least once in a graph.

```cypher
MATCH (employee:Person)
WHERE NOT employee.name = 'Cecil' AND (employee)-[:WORKS_FOR]->(:Person {name: 'Alice'})
RETURN employee.name AS employee
```

Path pattern expression with boolean operators.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_string_operators)[String operators](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/string-operators/)

```cypher
MATCH (n:Person)
WHERE n.name STARTS WITH 'C'
RETURN n.name AS name
```

The `STARTS WITH` operator checks if a `STRING` value begins with a specified prefix.

```cypher
MATCH (n:Person)
WHERE n.role ENDS WITH 'developer'
RETURN n.name AS name, n.role AS role
```

The `ENDS WITH` operator checks if a `STRING` value ends with a specified suffix

```cypher
MATCH (n:Person)
WHERE n.role CONTAINS 'eng'
RETURN n.name AS name, n.role AS role
```

The `CONTAINS` operator checks if a `STRING` value contains a specified substring.

```cypher
MATCH (n:Person)
WHERE n.email =~ '.*@company.com'
RETURN n.name AS name, n.email AS email
```

The regular expression operator `=~` checks if a \`STRING\`value matches a regular expression.

```cypher
MATCH (n:Person)
WHERE n.name =~ '(?i)CEC.*'
RETURN n.name
```

The `=~` operator can be used with regular expression flags, such as `(?i)` for case-insensitive matching, to modify how the regex is applied.

```cypher
RETURN 'the \u212B char' IS NORMALIZED AS normalized
```

The `IS NORMALIZED` operator is used to check whether the given `STRING` value is in the `NFC` Unicode normalization form.

```cypher
RETURN 'the \u212B char' IS NOT NORMALIZED AS notNormalized
```

The `IS NOT NORMALIZED` operator is used to check whether the given `STRING` value is not in the `NFC` Unicode normalization form.

```cypher
WITH 'the \u00E4 char' as myString
RETURN myString IS NFC NORMALIZED AS nfcNormalized,
    myString IS NFD NORMALIZED AS nfdNormalized
```

It is possible to define which Unicode normalization type is used. The available normalization types are: `NFC` (default), `NFD`, `NFKC`, and `NFKD`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_type_predicate_expressions)[Type predicate expressions](https://neo4j.com/docs/cypher-manual/25/expressions/predicates/type-predicate-expressions/)

```cypher
UNWIND [42, true, 'abc', null] AS val
RETURN val, val IS :: INTEGER AS isInteger
```

A type predicate expression can be used to verify the type of a variable, literal, property or other Cypher expression.

```cypher
UNWIND [42, true, 'abc', null] AS val
RETURN val, val IS NOT :: STRING AS notString
```

It is possible to verify that a Cypher expression is not of a certain type, using the negated type predicate expression `IS NOT ::`.

```cypher
RETURN
  NULL IS :: BOOLEAN AS isBoolean,
  NULL IS :: BOOLEAN NOT NULL AS isNotNullBoolean
```

All Cypher types includes the `NULL` value. Type predicate expressions can be appended with `NOT NULL`. This means that `IS ::` returns `TRUE` for all expressions evaluating to `NULL`, unless `NOT NULL` is appended.

```cypher
MATCH (n:Person)
WHERE n.age IS :: INTEGER AND n.age > 18
RETURN n.name AS name, n.age AS age
```

Type predicate expressions can also be used to filter out nodes or relationships with properties of a certain type.

```cypher
UNWIND [42, 42.0, "42"] as val
RETURN val, val IS :: INTEGER | FLOAT AS isNumber
```

Closed dynamic union types allow for the testing of multiple types in the same predicate.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_expressions)Expressions

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_conditional_expressionscase)[Conditional expressions(`CASE`)](https://neo4j.com/docs/cypher-manual/25/expressions/conditional-expressions/)

```cypher
MATCH (n:Person)
RETURN
CASE n.eyes
  WHEN 'blue'  THEN 1
  WHEN 'brown', 'hazel' THEN 2
  ELSE 3
END AS result, n.eyes
```

The simple `CASE` form is used to compare a single expression against multiple values, and is analogous to the `switch` construct of programming languages. The expressions are evaluated by the `WHEN` operator until a match is found. If no match is found, the expression in the `ELSE` operator is returned. If there is no `ELSE` case and no match is found, `null` will be returned.

```cypher
MATCH (n:Person)
RETURN n.name,
CASE n.age
  WHEN IS NULL, IS NOT TYPED INTEGER | FLOAT THEN "Unknown"
  WHEN = 0, = 1, = 2 THEN "Baby"
  WHEN <= 13 THEN "Child"
  WHEN < 20 THEN "Teenager"
  WHEN < 30 THEN "Young Adult"
  WHEN > 1000 THEN "Immortal"
  ELSE "Adult"
END AS result
```

The extended simple `CASE` can use comparison operators.

```cypher
MATCH (n:Person)
RETURN
CASE
  WHEN n.eyes = 'blue' THEN 1
  WHEN n.age < 40      THEN 2
  ELSE 3
END AS result, n.eyes, n.age
```

The generic `CASE` expression supports multiple conditional statements, and is analogous to the `if-elseif-else` construct of programming languages. Each row is evaluated in order until a `true` value is found. If no match is found, the expression in the `ELSE` operator is returned. If there is no `ELSE` case and no match is found, `null` will be returned.

```cypher
MATCH (n:Person)
WITH n,
CASE n.eyes
  WHEN 'blue'  THEN 1
  WHEN 'brown' THEN 2
  ELSE 3
END AS colorCode
SET n.colorCode = colorCode
RETURN n.name, n.colorCode
```

The results of a `CASE` expression can be used to set properties on a node or relationship.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_label_expressions)[Label expressions](https://neo4j.com/docs/cypher-manual/25/patterns/reference/node-and-relationship-patterns/#label-expressions)

```cypher
MATCH (n:Movie|Person)
RETURN n.name AS name, n.title AS title
```

Node pattern using the `OR` (`|`) label expression.

```cypher
MATCH (n:!Movie)
RETURN labels(n) AS label, count(n) AS labelCount
```

Node pattern using the negation (`!`) label expression.

```cypher
MATCH (:Movie {title: 'Wall Street'})<-[:ACTED_IN|DIRECTED]-(person:Person)
RETURN person.name AS person
```

Relationship pattern using the `OR` (`|`) label expression. As relationships can only have exactly one type each, `()-[:A&B]→()` will never match a relationship.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_list_expressions)[List expressions](https://neo4j.com/docs/cypher-manual/25/expressions/list-expressions)

```cypher
WITH [1, 2, 3, 4] AS list
RETURN list[0] AS firstElement,
       list[2] AS thirdElement,
       list[-1] AS finalElement
```

The subscript operator, `[]`, can be used to access specific elements in a `LIST`. `[0]` refers to the first element in a `LIST`, `[1]` to the second, and so on. `[-1]` refers to the last element in a `LIST`, `[-2]` to the penultimate element, and so on.

```cypher
WITH [[1, 2], [3, 4], [5, 6]] AS nestedList
RETURN nestedList[1] AS secondList
```

Access a `LIST` within a nested `LIST`.

```cypher
WITH [[1, 2], [3, 4], [5, 6]] AS nestedList
RETURN nestedList[1] AS secondList,
       nestedList[1][0] AS firstElementOfSecondList
```

Access specific elements in a nested `LIST`.

```cypher
WITH [1, 2, 3, 4, 5, 6] AS list
RETURN list[2..4] AS middleElements,
       list[..2] AS noLowerBound,
       list[2..] AS noUpperBound
```

`LIST` values can be sliced if a range is provided within the subscript operator `[]`. The bounds of the range are separated using two dots (`..`). This allows for extracting a subset of a `LIST` rather than a single element. List slicing is inclusive at the start of the range, but exclusive at the end (e.g. `list[start..end]` includes `start`, but excludes `end`).

```cypher
WITH [1, 2, 3, 4, 5, 6] AS list
RETURN list[..-1] AS finalElementRemoved,
       list[..-2] AS finalTwoElementsRemoved,
       list[-3..-1] AS removedFirstThreeAndLast
```

Negative indexing in list slicing references elements from the end of the `LIST`; `..-1` excludes the last element, `..-2` excludes the last two elements, and so on.

```cypher
WITH [[1, 2, 3], [4, 5, 6], [7, 8, 9]] AS nestedList
RETURN nestedList[1][0..2] AS slicedInnerList
```

Slicing inner `LIST` values require two `[]` operators; the first `[]` accesses elements from the outer `LIST`, while the second slices or accesses elements from the inner `LIST`.

```cypher
RETURN [1,2] || [3,4] AS list1,
       [1,2] + [3,4] AS list2
```

Cypher contains two list concatenation operators: `||` and `+`. They are functionally equivalent but `||` is GQL conformant and `+` is not.

```cypher
WITH [1, 2, 3, 4] AS list
RETURN 0 + list AS newBeginning,
       list + 5 AS newEnd
```

The `+` operator can add elements to the beginning or end of a `LIST` value. This is not possible using the `||` operator.

```cypher
WITH [1, 2, 3, 4, 5] AS list
RETURN [n IN list WHERE n > 2 | n] AS filteredList
```

List comprehension is used to create new `LIST` values by iterating over existing `LIST` values and transforming the elements based on certain conditions or operations. This process effectively maps each element in the original `LIST` to a new value. The result is a new `LIST` that consists of the transformed elements.

```cypher
MATCH (p:Person) WHERE p.skills IS NOT NULL
ORDER BY p.name
RETURN p.name AS name,
      [skill IN p.skills | skill + " expert"] AS modifiedSkills
```

List comprehension using node properties.

```cypher
MATCH (p:Person)
RETURN [person IN collect(p) WHERE 'Python' IN person.skills | person.name] AS pythonExperts
```

List comprehension with a `WHERE` predicate.

```cypher
RETURN [x IN ([1, null, 3] || [null, 5, null]) WHERE x IS NOT NULL] AS listWithoutNull
```

List comprehension can be used to remove any unknown `NULL` values when concatenating `LIST` values.

```cypher
MATCH (alice:Person {name: 'Alice'})
RETURN [(employee:Person)-[:WORKS_FOR]->(alice) | employee.name] AS employees
```

Pattern comprehension is used to create new `LIST` values by matching graph patterns and applying conditions to the matched elements, returning custom projections.

```cypher
MATCH (alice:Person {name: 'Alice'})
RETURN [(employee:Person)-[:WORKS_FOR]->(alice) WHERE employee.age > 30 | employee.name || ', ' || toString(employee.age)] AS employeesAbove30
```

Pattern comprehension with a `WHERE` predicate.

```cypher
MATCH (cecil:Person {name: 'Cecil'})
WITH [(cecil)-[:WORKS_FOR*]->(superior:Person) | superior.skills] AS allSuperiorsSkills
WITH reduce(accumulatedSkills = [], superiorSkills IN allSuperiorsSkills | accumulatedSkills || superiorSkills) AS allSkills
UNWIND allSkills AS superiorsSkills
RETURN collect(DISTINCT superiorsSkills) AS distinctSuperiorsSkills
```

Variable-length pattern comprehension.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_node_and_relationship_operators)[Node and relationship operators](https://neo4j.com/docs/cypher-manual/25/expressions/node-relationship-operators/)

```cypher
MATCH (employee:Person)-[r:WORKS_FOR]->(manager:Person)
RETURN employee.firstName AS employee,
       r.since AS employedSince,
       manager.firstName AS manager
```

Property values of nodes and relationships can be accessed statically by specifying a property name after the `.` operator.

```cypher
LET nodeProperty = 'lastName'
MATCH (p:Person)
RETURN p[nodeProperty] AS lastName
```

Property values can be accessed dynamically by using the subscript operator `[]`.

```cypher
MATCH (p:Person)
RETURN p.firstName || coalesce(' ' + p.middleName, '') || ' ' || p.lastName AS fullName
```

If a property (or property value) is missing in an expression that tries to access a property statically or dynamically, the whole expression will evaluate to `NULL`. The [`coalesce()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-coalesce) function can be used to skip the first `NULL` value in an expression.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_mathematical_operators)[Mathematical operators](https://neo4j.com/docs/cypher-manual/25/expressions/mathematical-operators/)

```cypher
RETURN 10 + 5 AS result
```

The addition operator `+` is used to add numeric values.

```cypher
RETURN 10 - 5 AS result
```

The subtraction operator `-` is used to subtract numeric values.

```cypher
RETURN 10 * 5 AS result
```

The multiplication operator `*` is used to multiply numeric values.

```cypher
RETURN 10 / 5 AS result
```

The division operator `/` is used to divide numeric values.

```cypher
RETURN 10 % 3 AS result
```

The modulo division operation `%` returns the remainder when one number is divided by another.

```cypher
RETURN 10 ^ 5 AS result
```

The exponentiation operator `^` raises a number to the power of another.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_map_expressions)[Map expressions](https://neo4j.com/docs/cypher-manual/25/expressions/map-expressions)

```cypher
WITH {a: 10, b: 20, c: 30} AS map
RETURN map.a AS firstValue,
       map.c AS lastValue
```

`MAP` values can be accessed statically by specifying a key after the `.` operator.

```cypher
WITH {a: 10, b: 20, c: 30, innerMap: {x: 100, y: 200, z: 300}} AS map
RETURN map.a AS firstOuterValue,
       map.innerMap.y AS secondInnerValue
```

To statically access a value in a nested `MAP`, use chained `.` operators. Each `.` operator traverses one level deeper into the nested structure.

```cypher
WITH {a: 10, b: 20, c: 30} AS map,
     'a' AS dynamicKey
RETURN map[dynamicKey] AS dynamicValue
```

To dynamically access a `MAP` value, use the subscript operator, `[]`. The key can be provided by a variable or a parameter.

```cypher
WITH {a: 10, b: 20, c: 30, innerMap: {x: 100, y: 200, z: 300}} AS map,
     'z' AS dynamicInnerKey
RETURN map.innerMap[dynamicInnerKey] AS dynamicInnerValue
```

Dynamically access a nested `MAP` value.

```cypher
WITH {a: 10, b: 20, c: 30} AS map
RETURN map{.a, .c} AS projectedMap
```

Map projection with a key selector to extract specific key-value pairs from a `MAP`.

```cypher
WITH {a: 10, b: 20, c: 30} AS map
RETURN map{a: map.a, valueSum: map.a + map.b + map.c} AS projectedMap
```

Map projection with a literal entry to add custom values to a projected `MAP` value without modifying the original data structure.

```cypher
MATCH (keanu:Person {name: 'Keanu Reeves'})
LET dob = date('1964-09-02'), birthPlace =  'Beirut, Lebanon'
RETURN keanu{.name, dob, birthPlace} AS projectedKeanu
```

Map projection with a variable selector to project values based on a variable name.

```cypher
WITH {a: 10, b: 20, c: 30} AS map
RETURN map{.*} AS projectedMap
```

Map projection with an all-map projection to project all key-value pairs from a `MAP` without explicitly listing them.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_string_concatenation_operators)[String concatenation operators](https://neo4j.com/docs/cypher-manual/25/expressions/string-operators/)

```cypher
RETURN 'Neo' || '4j' AS result1,
       'Neo' + '4j' AS result2
```

Cypher contains two operators for the concatenation of `STRING` values: `||` and `+` The two operators are functionally equivalent. However, `||` is GQL conformant, while `+` is not.

```cypher
RETURN 'Alpha' || 'Beta' AS result1,
       'Alpha' || ' ' || 'Beta' AS result2
```

Cypher does not insert spaces when concatenating `STRING` values.

```cypher
CREATE (p:Person {firstName: 'Keanu', lastName: 'Reeves'})
SET p.fullName = p.firstName || ' ' || p.lastName
RETURN p.fullName AS fullName
```

String concatenation on two `STRING` properties.

```cypher
RETURN 'My favorite fruits are: ' || 'apples' || ', ' || 'bananas' || ', and ' || 'oranges' || '.' AS result
```

String concatenation adding a prefix, suffix, and separator.

```cypher
WITH ['Neo', '4j'] AS list
RETURN reduce(acc = '', item IN list| acc || item) AS result
```

`STRING` values in a `LIST` can be concatenated using the [`reduce()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-reduce) function.

```cypher
WITH ['Apples', null, 'Bananas', null, 'Oranges', null] AS list
RETURN 'My favorite fruits are: ' || reduce(acc = head(list), item IN tail(list) | acc || coalesce(', ' || item, '')) || '.' AS result
```

Concatenating a `STRING` value with `NULL` returns `NULL`. To skip the first `NULL` value in a list of expressions, use the [`coalesce()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-coalesce) function.

```cypher
WITH ['Apples', 'Bananas', 'Oranges'] AS list
RETURN [item IN list | 'Eat more ' || item || '!'] AS result
```

List comprehension allows concatenating a `STRING` value to each item in a `LIST` to generate a new `LIST` of modified `STRING` values.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_temporal_operators)[Temporal operators](https://neo4j.com/docs/cypher-manual/25/expressions/temporal-operators)

```cypher
WITH localdatetime({year:1984, month:10, day:11, hour:12, minute:31, second:14}) AS aDateTime,
     duration({years: 12, nanoseconds: 2}) AS aDuration
RETURN aDateTime + aDuration AS addition,
      aDateTime - aDuration AS subtraction
```

`DURATION` values can be added and subtracted from temporal instant values, such as `LOCAL DATETIME`.

```cypher
WITH duration({days: 14, minutes: 12, seconds: 70, nanoseconds: 1}) AS aDuration
RETURN aDuration,
       aDuration * 2 AS multipliedDuration,
       aDuration / 3 AS dividedDuration
```

When multiplying or dividing a `DURATION`, each component is handled separately. In multiplication, the value of each component is multiplied by the given factor, while in division, each component is divided by the given number. If the result of the division does not fit into the original components, it overflows into smaller components (e.g. converting days into hours).

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_functions)Functions

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show_functions)[SHOW FUNCTIONS](https://neo4j.com/docs/cypher-manual/25/functions/show-functions/)

```cypher
SHOW FUNCTIONS
```

Show all functions in a database and return default columns (`name`, `category`, and `description`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW BUILT IN FUNCTIONS YIELD name, isBuiltIn
WHERE name STARTS WITH 'a'
```

`SHOW FUNCTIONS` can be filtered with the `ALL`, `BUILT IN` and `USER DEFINED` keywords.

```cypher
SHOW FUNCTIONS EXECUTABLE BY CURRENT USER YIELD name, category, description, rolesExecution, rolesBoostedExecution
LIMIT 5
```

Functions can be filtered on whether a user can execute them. This filtering is only available through the `EXECUTABLE` clause and not through the `WHERE` clause. This example filters on the functions executable by the current user.

```cypher
SHOW FUNCTIONS EXECUTABLE BY jake
```

Filter on the functions executable by a specific user.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_aggregating_functions)[Aggregating functions](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/)

```cypher
MATCH (p:Person)
RETURN avg(p.age)
```

The [`avg()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-avg) function returns the average of a set of `INTEGER` or `FLOAT` values.

```cypher
UNWIND [duration('P2DT3H'), duration('PT1H45S')] AS dur
RETURN avg(dur)
```

The [`avg()` duration](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-avg-duration) function returns the average of a set of `DURATION` values.

```cypher
MATCH (p:Person)
RETURN collect(p.age)
```

The [`collect()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-collect) function returns a single aggregated list containing the non-`null` values returned by an expression.

```cypher
MATCH (p:Person {name: 'Keanu Reeves'})-->(x)
RETURN labels(p), p.age, count(*)
```

The [`count()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-count) function returns the number of values or rows. When `count(*)` is used, the function returns the number of matching rows.

```cypher
MATCH (p:Person)
RETURN count(p.age)
```

The `count()` function can also be passed an expression. If so, it returns the number of non-`null` values returned by the given expression.

```cypher
MATCH (p:Person)
RETURN max(p.age)
```

The [`max()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-max) function returns the maximum value in a set of values.

```cypher
MATCH (p:Person)
RETURN min(p.age)
```

The [`min()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-min) function returns the minimum value in a set of values.

```cypher
MATCH (p:Person)
RETURN percentileCont(p.age, 0.4)
```

The [`percentileCont()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-percentilecont) function returns the percentile of the given value over a group, with a percentile from `0.0` to `1.0`. It uses a linear interpolation method, calculating a weighted average between two values if the desired percentile lies between them.

```cypher
MATCH (p:Person)
RETURN percentileDisc(p.age, 0.5)
```

The [`percentileDisc()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-percentiledisc) function returns the percentile of the given value over a group, with a percentile from `0.0` to `1.0`. It uses a rounding method and calculates the nearest value to the percentile.

```cypher
MATCH (p:Person)
WHERE p.name IN ['Keanu Reeves', 'Liam Neeson', 'Carrie Anne Moss']
RETURN stDev(p.age)
```

The [`stDev()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-stdev) function returns the standard deviation for the given value over a group. It uses a standard two-pass method, with `N - 1` as the denominator, and should be used when taking a sample of the population for an unbiased estimate.

```cypher
MATCH (p:Person)
WHERE p.name IN ['Keanu Reeves', 'Liam Neeson', 'Carrie Anne Moss']
RETURN stDevP(p.age)
```

The [`stDevP()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-stdevp) function returns the standard deviation for the given value over a group. It uses a standard two-pass method, with `N` as the denominator, and should be used when calculating the standard deviation for an entire population.

```cypher
MATCH (p:Person)
RETURN sum(p.age)
```

The [`sum()`](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-sum) function returns the sum of a set of numeric values.

```cypher
UNWIND [duration('P2DT3H'), duration('PT1H45S')] AS dur
RETURN sum(dur)
```

The [`sum()` duration](https://neo4j.com/docs/cypher-manual/25/functions/aggregating/#functions-sum-duration) function returns the sum of a set of durations.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_database_functions)[Database functions](https://neo4j.com/docs/cypher-manual/25/functions/database/)

```cypher
WITH "2:efc7577d-022a-107c-a736-dbcdfc189c03:0" AS eid
RETURN db.nameFromElementId(eid) AS name
```

The [`db.nameFromElementId()`](https://neo4j.com/docs/cypher-manual/25/functions/database/#functions-database-nameFromElementId) function returns the name of a database to which the element id belongs. The name of the database can only be returned if the provided element id belongs to a standard database in the DBMS.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_graph_functions)[Graph functions](https://neo4j.com/docs/cypher-manual/25/functions/graph/)

```cypher
RETURN graph.names() AS name
```

The [`graph.names()`](https://neo4j.com/docs/cypher-manual/25/functions/graph/#functions-graph-names) function returns a list containing the names of all graphs on the current composite database. It is only supported on [composite databases](https://neo4j.com/docs/operations-manual/current/database-administration/composite-databases/concepts/).

```cypher
UNWIND graph.names() AS name
RETURN name, graph.propertiesByName(name) AS props
```

The [`graph.propertiesByName()`](https://neo4j.com/docs/cypher-manual/25/functions/graph/#functions-graph-propertiesByName) function returns a map containing the properties associated with the given graph. The properties are set on the [alias](https://neo4j.com/docs/operations-manual/current/database-administration/aliases/manage-aliases-standard-databases/) that adds the graph as a constituent of a composite database. It is only supported on [composite databases](https://neo4j.com/docs/operations-manual/current/database-administration/composite-databases/concepts/).

```cypher
UNWIND graph.names() AS graphName
CALL () {
  USE graph.byName(graphName)
  MATCH (n)
  RETURN n
}
RETURN n
```

The [`graph.byName()`](https://neo4j.com/docs/cypher-manual/25/functions/graph/#functions-graph-byname) function resolves a constituent graph by name. It is only supported in the [`USE`](https://neo4j.com/docs/cypher-manual/25/clauses/use/) clause on [composite databases](https://neo4j.com/docs/operations-manual/current/database-administration/composite-databases/concepts/).

```cypher
USE graph.byElementId("4:c0a65d96-4993-4b0c-b036-e7ebd9174905:0")
MATCH (n) RETURN n
```

The [`graph.byElementId()`](https://neo4j.com/docs/cypher-manual/25/functions/graph/#functions-graph-by-elementid) function is used in the [`USE`](https://neo4j.com/docs/cypher-manual/25/clauses/use/) clause to resolve a constituent graph to which a given element id belongs. If the constituent database is not a standard database in the DBMS, an error will be thrown.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_list_functions)[List functions](https://neo4j.com/docs/cypher-manual/25/functions/list/)

```cypher
RETURN coll.distinct([1, true, true, null, 'a', false, true, 1, null])
```

The [`coll.distinct()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-distinct) function returns a given list with all duplicate values removed.

```cypher
RETURN coll.flatten(['a', ['b', ['c']]], 2)
```

The [`coll.flatten()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-flatten) function returns a list flattened to the given nesting depth, default is 1.

```cypher
RETURN coll.indexOf(['a', 'b', 'c', 'c'], 'c')
```

The [`coll.indexOf()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-indexOf) function returns the index of the first match of a value in the given list or -1 if the value is not present.

```cypher
RETURN coll.insert([true, 'a', 1, 5.4], 1, false)
```

The [`coll.insert()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-insert) function returns a list with the given value inserted at the given index.

```cypher
RETURN coll.max([true, 'a', 1, 5.4])
```

The [`coll.max()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-max) function returns the largest value present in the given list.

```cypher
RETURN coll.min([true, 'a', 1, 5.4])
```

The [`coll.min()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-min) function returns the smallest value present in the given list.

```cypher
RETURN coll.remove([true, 'a', 1, 5.4], 1)
```

The [`coll.remove()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-remove) function returns a list with the value at the given index removed.

```cypher
RETURN coll.sort([true, 'a', 1, 2])
```

The [`coll.sort()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-coll-sort) function returns a sorted list.

```cypher
MATCH (a) WHERE a.name = 'Alice'
RETURN keys(a)
```

The [`keys()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-keys) function returns a `LIST<STRING>` containing the `STRING` representations for all the property names of a `NODE`, `RELATIONSHIP`, or `MAP`.

```cypher
MATCH (a) WHERE a.name = 'Alice'
RETURN labels(a)
```

The [`labels()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-labels) function returns a `LIST<STRING>` containing the `STRING` representations for all the labels of a `NODE`.

```cypher
MATCH p = (a)-->(b)-->(c)
WHERE a.name = 'Alice' AND c.name = 'Eskil'
RETURN nodes(p)
```

The [`nodes()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-nodes) function returns a `LIST<NODE>` containing all the `NODE` values in a `PATH`.

```cypher
RETURN range(0, 10), range(2, 18, 3), range(0, 5, -1)
```

The [`range()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-range) function returns a `LIST<INTEGER>` comprising all `INTEGER` values within a range bounded by a start value and an end value, where the difference step between any two consecutive values is constant; i.e. an arithmetic progression.

```cypher
MATCH p = (a)-->(b)-->(c)
WHERE a.name = 'Alice' AND b.name = 'Bob' AND c.name = 'Daniel'
RETURN reduce(totalAge = 0, n IN nodes(p) | totalAge + n.age) AS reduction
```

The [`reduce()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-reduce) function returns the value resulting from the application of an expression on each successive element in a list in conjunction with the result of the computation thus far.

```cypher
MATCH p = (a)-->(b)-->(c)
WHERE a.name = 'Alice' AND c.name = 'Eskil'
RETURN relationships(p)
```

The [`relationships()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-relationships) function returns a `LIST<RELATIONSHIP>` containing all the `RELATIONSHIP` values in a `PATH`.

```cypher
WITH [4923,'abc',521, null, 487] AS ids
RETURN reverse(ids)
```

The [`reverse()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-reverse-list) function returns a `LIST<ANY>` in which the order of all elements in the given `LIST<ANY>` have been reversed.

```cypher
MATCH (a) WHERE a.name = 'Eskil'
RETURN a.likedColors, tail(a.likedColors)
```

The [`tail()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-tail) function returns a `LIST<ANY>` containing all the elements, excluding the first one, from a given `LIST<ANY>`.

```cypher
RETURN toBooleanList(null) as noList,
toBooleanList([null, null]) as nullsInList,
toBooleanList(['a string', true, 'false', null, ['A','B']]) as mixedList
```

The [`toBooleanList()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-tobooleanlist) converts a `LIST<ANY>` and returns a `LIST<BOOLEAN>`. If any values are not convertible to `BOOLEAN` they will be `null` in the `LIST<BOOLEAN>` returned.

```cypher
RETURN toFloatList(null) as noList,
toFloatList([null, null]) as nullsInList,
toFloatList(['a string', 2.5, '3.14159', null, ['A','B']]) as mixedList
```

The [`toFloatList()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-tofloatlist) converts a `LIST<ANY>` of values and returns a `LIST<FLOAT>`. If any values are not convertible to `FLOAT` they will be `null` in the `LIST<FLOAT>` returned.

```cypher
RETURN toIntegerList(null) as noList,
toIntegerList([null, null]) as nullsInList,
toIntegerList(['a string', 2, '5', null, ['A','B']]) as mixedList
```

The [`toIntegerList()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-tointegerlist) converts a `LIST<ANY>` of values and returns a `LIST<INTEGER>`. If any values are not convertible to `INTEGER` they will be `null` in the `LIST<INTEGER>` returned.

```cypher
RETURN toStringList(null) as noList,
toStringList([null, null]) as nullsInList,
toStringList(['already a string', 2, date({year:1955, month:11, day:5}), null, ['A','B']]) as mixedList
```

The [`toStringList()`](https://neo4j.com/docs/cypher-manual/25/functions/list/#functions-tostringlist) converts a `LIST<ANY>` of values and returns a `LIST<STRING>`. If any values are not convertible to `STRING` they will be `null` in the `LIST<STRING>` returned.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_mathematical_functions_numerical)[Mathematical functions - numerical](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric)

```cypher
MATCH (a), (e) WHERE a.name = 'Alice' AND e.name = 'Eskil'
RETURN a.age, e.age, abs(a.age - e.age)
```

The [`abs()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-abs) function returns the absolute value of the given number.

```cypher
RETURN ceil(0.1)
```

The [`ceil()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-ceil) function returns the smallest `FLOAT` that is greater than or equal to the given number and equal to an `INTEGER`.

```cypher
RETURN floor(0.9)
```

The [`floor()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-floor) function returns the largest `FLOAT` that is less than or equal to the given number and equal to an `INTEGER`.

```cypher
RETURN isNaN(0/0.0)
```

The [`isNan()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-isnan) function returns `true` if the given numeric value is `NaN` (Not a Number).

```cypher
RETURN rand()
```

The [`rand()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-rand) function returns a random `FLOAT` in the range from 0 (inclusive) to 1 (exclusive). The numbers returned follow an approximate uniform distribution.

```cypher
RETURN round(3.141592)
```

The [`round()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-round) function returns the value of the given number rounded to the nearest `INTEGER`, with ties always rounded towards positive infinity.

```cypher
RETURN round(3.141592, 3)
```

The [`round()` with precision](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-round2) function returns the value of the given number rounded to the closest value of given precision, with ties always being rounded away from zero (using rounding mode `HALF_UP`). The exception is for precision 0, where ties are rounded towards positive infinity to align with `round()` without precision.

```cypher
RETURN round(1.249, 1, 'UP') AS positive,
round(-1.251, 1, 'UP') AS negative,
round(1.25, 1, 'UP') AS positiveTie,
round(-1.35, 1, 'UP') AS negativeTie
```

The [`round()` with precision and rounding mode](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-round3) function returns the value of the given number rounded with the specified precision and the specified rounding mode.

```cypher
RETURN sign(-17), sign(0.1)
```

The [`sign()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-numeric/#functions-sign) function returns the signum of the given number: `0` if the number is 0, `-1` for any negative number, and `1` for any positive number.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_mathematical_functions_logarithmic)[Mathematical functions - logarithmic](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic)

```cypher
RETURN e()
```

The [`e()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic/#functions-e) function returns the base of the natural logarithm, *e*.

```cypher
RETURN exp(2)
```

The [`exp()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic/#functions-exp) function returns `en`, where `e` is the base of the natural logarithm, and `n` is the value of the argument expression.

```cypher
RETURN log(27)
```

The [`log()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic/#functions-log) function returns the natural logarithm of a number.

```cypher
RETURN log10(27)
```

The [`log10()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic/#functions-log10) function returns the common logarithm (base 10) of a number.

```cypher
RETURN sqrt(256)
```

The [`sqrt()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-logarithmic/#functions-sqrt) function returns the square root of a number.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_mathematical_functions_trigonometric)[Mathematical Functions - trigonometric](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric)

```cypher
RETURN acos(0.5)
```

The [`acos()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-acos) function returns the arccosine of a `FLOAT` in radians.

```cypher
RETURN asin(0.5)
```

The [`asin()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-asin) function returns the arcsine of a `FLOAT` in radians.

```cypher
RETURN atan(0.5)
```

The [`atan()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-atan) function returns the arctangent of a `FLOAT` in radians.

```cypher
RETURN atan2(0.5, 0.6)
```

The [`atan2()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-atan2) function returns the arctangent2 of a set of coordinates in radians.

```cypher
RETURN cos(0.5)
```

The [`cos()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-cos) function returns the cosine of a `FLOAT`.

```cypher
RETURN cosh(0.7)
```

The [`cosh()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-cosh) function returns the hyperbolic cosine of a `FLOAT`.

```cypher
RETURN cot(0.5)
```

The [`cot()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-cot) function returns the cotangent of a `FLOAT`.

```cypher
RETURN coth(0.7)
```

The [`coth()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-coth) function returns the hyperbolic cotangent of a `FLOAT`.

```cypher
RETURN degrees(3.14159)
```

The [`degrees()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-degrees) function converts radians to degrees.

```cypher
RETURN haversin(0.5)
```

The [`haversin()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-haversin) function converts half the versine of a number.

```cypher
RETURN pi()
```

The [`pi()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-pi) function returns the mathematical constant *pi*.

```cypher
RETURN radians(180)
```

The [`radians()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-radians) function converts degrees to radians.

```cypher
RETURN sin(0.5)
```

The [`sin()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-sin) function returns the sine of a number.

```cypher
RETURN sinh(0.7)
```

The [`sinh()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-sinh) function returns the hyperbolic sine of a `FLOAT`.

```cypher
RETURN tan(0.5)
```

The [`tan()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-tan) function returns the tangent of a number.

```cypher
RETURN tanh(0.7)
```

The [`tanh()`](https://neo4j.com/docs/cypher-manual/25/functions/mathematical-trigonometric/#functions-tanh) function returns the hyperbolic tangent of a `FLOAT`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_predicate_functions)[Predicate functions](https://neo4j.com/docs/cypher-manual/25/functions/predicate/)

```cypher
MATCH p = (a:Person {name: 'Keanu Reeves'})-[]-{2,}()
WHERE all(x IN nodes(p) WHERE x.age < 60)
RETURN [n IN nodes(p) | n.name] AS actorsList
```

The [`all()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-all) function returns `true` if the predicate holds for all elements in the given `LIST<ANY>`.

```cypher
MATCH (s) (()-[:KNOWS]-(n)){3}
WHERE allReduce(
  acc = s.age,
  node IN n | acc + node.age,
  acc < 230
)
RETURN [i IN [s] + n | i.name || " (" + toString(i.age) || ")"] AS ageSequence,
      reduce(acc = 0, node IN [s] + n | acc + node.age) AS aggregatedAges
ORDER BY aggregatedAges
```

The [`allReduce()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-allreduce) function returns `true` if, during the stepwise evaluation of a value across the elements in a given `LIST<ANY>`, the accumulated result satisfies a specified predicate at every step. Where that list is a group variable defined in a quantified path pattern, it allows for the early pruning of paths that do not satisfy the predicate.

```cypher
MATCH p = (n:Person {name: 'Keanu Reeves'})-[:KNOWS]-{3}()
WHERE any(rel IN relationships(p) WHERE rel.since < 2000)
RETURN [person IN nodes(p) | person.name] AS connectedActors,
       [rel IN relationships(p) | rel.since] AS sinceYears
```

The [`any()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-any) function returns `true` if the predicate holds for at least one element in the given `LIST<ANY>`.

```cypher
MATCH (p:Person)
RETURN p.name AS name,
       exists((p)-[:ACTED_IN]->()) AS has_acted_in_rel
```

The [`exists()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-exists) function returns `true` if a match for the given pattern exists in the graph.

```cypher
MATCH (p:Person)
WHERE NOT isEmpty(p.nationality)
RETURN p.name, p.nationality
```

The [`isEmpty()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-isempty) function returns `true` if the given `LIST<ANY>` or `MAP` contains no elements, or if the given `STRING` contains no characters.

```cypher
MATCH p = (n:Person {name: 'Keanu Reeves'})-[]-{2}()
WHERE none(x IN nodes(p) WHERE x.age > 60)
RETURN [x IN nodes(p) | x.name] AS connectedActors
```

The [`none()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-none) function returns `true` if the predicate does not hold for any element in the given `LIST<ANY>`.

```cypher
MATCH p = (n:Person {name: 'Keanu Reeves'})-[:KNOWS]-+(b)
WHERE single(x IN [b] WHERE x.nationality = 'Northern Irish')
RETURN [person IN nodes(p) | person.name + " (" + person.nationality + ")"] AS northernIrishPaths
ORDER BY length(p)
```

The [`single()`](https://neo4j.com/docs/cypher-manual/25/functions/predicate/#functions-single) function returns `true` if the predicate holds for exactly *one* of the elements in the given `LIST<ANY>`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_scalar_functions)[Scalar functions](https://neo4j.com/docs/cypher-manual/25/functions/scalar/)

```cypher
RETURN char_length('Alice')
```

The [`char_length()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-char_length) function returns the number of Unicode characters in a `STRING`. This function is an alias of the [`size()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-size) function.

```cypher
RETURN character_length('Alice')
```

The [`character_length()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-character_length) function returns the number of Unicode characters in a `STRING`. This function is an alias of the [`size()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-size) function.

```cypher
MATCH (a)
WHERE a.name = 'Alice'
RETURN coalesce(a.hairColor, a.eyes)
```

The [`coalesce()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-coalesce) function returns the first given non-null argument.

```cypher
MATCH (n:Developer)
RETURN elementId(n)
```

The [`elementId()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-elementid) function returns a `STRING` representation of a node or relationship identifier, unique within a specific transaction and DBMS.

```cypher
MATCH (x:Developer)-[r]-()
RETURN endNode(r)
```

The [`endNode()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-endnode) function returns the the end `NODE` of a `RELATIONSHIP`.

```cypher
MATCH (a)
WHERE a.name = 'Eskil'
RETURN a.likedColors, head(a.likedColors)
```

The [`head()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-head) function returns the first element of the list. Returns `null` for an empty list. Equivalent to the list indexing `$list[0]`.

```cypher
MATCH (a)
RETURN id(a)
```

The [`id()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-id) function returns an `INTEGER` (the internal ID of a node or relationship). Do not rely on the internal ID for your business domain; the internal ID can change between transactions. It is recommended to use `elementId` instead.

```cypher
MATCH (a)
WHERE a.name = 'Eskil'
RETURN a.likedColors, last(a.likedColors)
```

The [`last()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-last) function returns the last element of the list. Returns `null` for an empty list. Equivalent to the list indexing `$list[-1]`.

```cypher
MATCH p = (a)-->(b)-->(c)
WHERE a.name = 'Alice'
RETURN length(p)
```

The [`length()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-length) function returns the length of a `PATH`.

```cypher
RETURN nullIf("abc", "def")
```

The [`nullIf()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-nullIf) function returns `null` if the two given parameters are equivalent, otherwise it returns the value of the first parameter.

```cypher
CREATE (p:Person {name: 'Stefan', city: 'Berlin'})
RETURN properties(p)
```

The [`properties()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-properties) function returns a `MAP` containing all the properties of a node or relationship.

```cypher
RETURN randomUUID() AS uuid
```

The [`randomUUID()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-randomuuid) function returns a `STRING`; a randomly-generated universally unique identifier (UUID).

```cypher
RETURN size(['Alice', 'Bob'])
```

The [`size()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-size) function returns the number of elements in the list.

```cypher
MATCH (x:Developer)-[r]-()
RETURN startNode(r)
```

The function [`startNode()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-startnode) function returns the start `NODE` of a `RELATIONSHIP`.

```cypher
RETURN timestamp()
```

The [`timestamp()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-timestamp) function returns the time in milliseconds since `midnight, January 1, 1970 UTC.` and the current time.

```cypher
RETURN toBoolean('true'), toBoolean('not a boolean'), toBoolean(0)
```

The [`toBoolean()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-toboolean) function converts a `STRING`, `INTEGER` or `BOOLEAN` value to a `BOOLEAN` value.

```cypher
RETURN toBooleanOrNull('true'), toBooleanOrNull('not a boolean'), toBooleanOrNull(0), toBooleanOrNull(1.5)
```

The [`toBooleanOrNull()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-tobooleanornull) function converts a `STRING`, `INTEGER` or `BOOLEAN` value to a `BOOLEAN` value. For any other input value, `null` will be returned.

```cypher
RETURN toFloat('11.5'), toFloat('not a number')
```

The [`toFloat()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-tofloat) function converts an `INTEGER`, `FLOAT` or a `STRING` value to a `FLOAT`.

```cypher
RETURN toFloatOrNull('11.5'), toFloatOrNull('not a number'), toFloatOrNull(true)
```

The [`toFloatOrNull()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-tofloatornull) function converts an `INTEGER`, `FLOAT` or a `STRING` value to a `FLOAT`. For any other input value, `null` will be returned.

```cypher
RETURN toInteger('42'), toInteger('not a number'), toInteger(true)
```

The [`toInteger()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-tointeger) function converts a `BOOLEAN`, `INTEGER`, `FLOAT` or a `STRING` value to an `INTEGER` value.

```cypher
RETURN toIntegerOrNull('42'), toIntegerOrNull('not a number'), toIntegerOrNull(true), toIntegerOrNull(['A', 'B', 'C'])
```

The [`toIntegerOrNull()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-tointegerornull) function converts a `BOOLEAN`, `INTEGER`, `FLOAT` or a `STRING` value to an `INTEGER` value. For any other input value, `null` will be returned.

```cypher
MATCH (n)-[r]->()
WHERE n.name = 'Alice'
RETURN type(r)
```

The [`type()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-type) function returns the `STRING` representation of the `RELATIONSHIP` type.

```cypher
UNWIND ["abc", 1, 2.0, true, [date()]] AS value
RETURN valueType(value) AS result
```

The [`valueType()`](https://neo4j.com/docs/cypher-manual/25/functions/scalar/#functions-valueType) function returns a `STRING` representation of the most precise value type that the given expression evaluates to.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_security_functions)[Security functions](https://neo4j.com/docs/cypher-manual/25/functions/security/)

```cypher
CREATE AUTH RULE nativeAdminRule
SET CONDITION 'admin' IN abac.native.user_tags()
```

The [`abac.native.user_tags()`](https://neo4j.com/docs/cypher-manual/25/functions/security/#functions-security-native-user-tags) function returns the list of tags for the native user. `abac.native.user_tags()` cannot be called directly in queries. It can only be used in the condition of a `CREATE AUTH RULE` or `ALTER AUTH RULE` command.

```cypher
CREATE AUTH RULE salesRule
SET CONDITION abac.oidc.user_attribute('department') = 'sales'
```

The [`abac.oidc.user_attribute()`](https://neo4j.com/docs/cypher-manual/25/functions/security/#functions-security-oidc-user-attribute) function returns the value of the specified user attribute from the OIDC claims. Returns `null` if the attribute is not present. `abac.oidc.user_attribute()` cannot be called directly in queries. It can only be used in the condition of a `CREATE AUTH RULE` or `ALTER AUTH RULE` command.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_string_functions)[String functions](https://neo4j.com/docs/cypher-manual/25/functions/string/)

```cypher
RETURN btrim('   hello    '), btrim('xxyyhelloxyxy', 'xy')
```

The [`btrim()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-btrim) function returns the original `STRING` with leading and trailing `trimCharacterString` characters removed. If `trimCharacterString` is not specified then all leading and trailing whitespace will be removed.

```cypher
RETURN left('hello', 3)
```

The [`left()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-left) function returns a `STRING` containing the specified number of leftmost characters of the given `STRING`.

```cypher
RETURN lower('HELLO')
```

The [`lower()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-lower) function returns the given `STRING` in lowercase. This function is an alias of the [`toLower`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-tolower) function.

```cypher
RETURN ltrim('   hello'), ltrim('xxyyhelloxyxy', 'xy')
```

The [`ltrim()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-ltrim) function returns the original `STRING` with leading `trimCharacterString` characters removed. If `trimCharacterString` is not specified then all leading whitespace will be removed.

```cypher
RETURN normalize('\u212B') = '\u00C5' AS result
```

The [`normalize()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-normalize) function returns a given `STRING` normalized using the `NFC` Unicode normalization form.

```cypher
RETURN replace("hello", "l", "w")
```

The [`replace()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-replace) function returns a `STRING` in which all occurrences of a specified `STRING` in the given `STRING` have been replaced by another (specified) replacement `STRING`.

```cypher
RETURN reverse('palindrome')
```

The [`reverse()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-reverse) function returns a `STRING` in which the order of all characters in the given `STRING` have been reversed.

```cypher
RETURN right('hello', 3)
```

The [`right()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-right) function returns a `STRING` containing the specified number of rightmost characters in the given `STRING`.

```cypher
RETURN rtrim('hello   '), rtrim('xxyyhelloxyxy', 'xy')
```

The [`rtrim()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-rtrim) function returns the given `STRING` with trailing `trimCharacterString` characters removed. If `trimCharacterString` is not specified then all trailing whitespace will be removed.

```cypher
RETURN split('one,two', ',')
```

The [`split()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-split) function returns a `LIST<STRING>` resulting from the splitting of the given `STRING` around matches of the given delimiter.

```cypher
RETURN string.indexOf('hello', 'l')
```

The [`string.indexOf()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-string.indexof) function returns the index of the first occurrence of the given `value` within the `input` `STRING`, or -1 if no match is found.

```cypher
RETURN string.join(['one', 'two'], ', ')
```

The [`string.join()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-string.join) function concatenates the elements in the `input` `STRING`, inserting a `delimiter` between each element, and returns the resulting `STRING`.

```cypher
RETURN string.regexReplace("hello", "l.", "w")
```

The [`string.regexReplace()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-string.regexreplace) function returns a `STRING` where all matches of `regex` in the `original` `STRING` are replaced with the `replacement` `STRING`.

```cypher
RETURN substring('hello', 1, 3), substring('hello', 2)
```

The [`substring()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-substring) function returns a substring of the given `STRING`, beginning with a zero-based index start and length.

```cypher
RETURN toLower('HELLO')
```

The [`toLower()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-tolower) function returns the given `STRING` in lowercase.

```cypher
RETURN
  toString(11.5),
  toString('already a string'),
  toString(true),
  toString(date({year: 1984, month: 10, day: 11})) AS dateString,
  toString(datetime({year: 1984, month: 10, day: 11, hour: 12, minute: 31, second: 14, millisecond: 341, timezone: 'Europe/Stockholm'})) AS datetimeString,
  toString(duration({minutes: 12, seconds: -60})) AS durationString
```

The [`toString()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-tostring) function converts an `INTEGER`, `FLOAT`, `BOOLEAN`, `STRING`, `POINT`, `DURATION`, `DATE`, `ZONED TIME`, `LOCAL TIME`, `LOCAL DATETIME` or `ZONED DATETIME` value to a `STRING`.

```cypher
RETURN toStringOrNull(11.5),
toStringOrNull('already a string'),
toStringOrNull(true),
toStringOrNull(date({year: 1984, month: 10, day: 11})) AS dateString,
toStringOrNull(datetime({year: 1984, month: 10, day: 11, hour: 12, minute: 31, second: 14, millisecond: 341, timezone: 'Europe/Stockholm'})) AS datetimeString,
toStringOrNull(duration({minutes: 12, seconds: -60})) AS durationString,
toStringOrNull(['A', 'B', 'C']) AS list
```

The [`toStringOrNull()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-tostringornull) function converts an `INTEGER`, `FLOAT`, `BOOLEAN`, `STRING`, `POINT`, `DURATION`, `DATE`, `ZONED TIME`, `LOCAL TIME`, `LOCAL DATETIME` or `ZONED DATETIME` value to a `STRING`. For any other input value, `null` will be returned.

```cypher
RETURN toUpper('hello')
```

The [`toUpper()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-toupper) function returns the given `STRING` in uppercase.

```cypher
RETURN trim('   hello   '), trim(BOTH 'x' FROM 'xxxhelloxxx')
```

The [`trim()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-trim) function returns the given `STRING` with leading and trailing whitespace removed.

```cypher
RETURN upper('hello')
```

The [`upper()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-upper) function returns the given `STRING` in uppercase. This function is an alias of the [`toUpper()`](https://neo4j.com/docs/cypher-manual/25/functions/string/#functions-toupper) function.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_spatial_functions)[Spatial functions](https://neo4j.com/docs/cypher-manual/25/functions/spatial/)

```cypher
WITH
  point({longitude: 12.53, latitude: 55.66}) AS lowerLeft,
  point({longitude: 12.614, latitude: 55.70}) AS upperRight
MATCH (t:TrainStation)
WHERE point.withinBBox(point({longitude: t.longitude, latitude: t.latitude}), lowerLeft, upperRight)
RETURN count(t)
```

The [`point()` Cartesian 2D](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-point-cartesian-2d) function returns a 2D `POINT` in the *Cartesian* CRS corresponding to the given coordinate values.

```cypher
RETURN
  point.withinBBox(
    null,
    point({longitude: 56.7, latitude: 12.78}),
    point({longitude: 57.0, latitude: 13.0})
  ) AS in
```

The [`point()` Cartesian 3D](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-point-cartesian-3d) function returns a 3D `POINT` in the *Cartesian* CRS corresponding to the given coordinate values.

```cypher
MATCH (t:TrainStation)-[:TRAVEL_ROUTE]->(o:Office)
WITH
  point({longitude: t.longitude, latitude: t.latitude}) AS trainPoint,
  point({longitude: o.longitude, latitude: o.latitude}) AS officePoint
RETURN round(point.distance(trainPoint, officePoint)) AS travelDistance
```

The [`point()` WGS 84 2D](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-point-wgs84-2d) function returns a 2D `POINT` in the *WGS 84 CRS* corresponding to the given coordinate values.

```cypher
WITH
  point({x: 0, y: 0, crs: 'cartesian'}) AS lowerLeft,
  point({x: 10, y: 10, crs: 'cartesian'}) AS upperRight
RETURN point.withinBBox(point({x: 5, y: 5, crs: 'cartesian'}), lowerLeft, upperRight) AS result
```

The [`point()` WGS 84 3D](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-point-wgs84-3d) function returns a 3D `POINT` in the *WGS 84 CRS* corresponding to the given coordinate values.

```cypher
MATCH (p:Office)
RETURN point({longitude: p.longitude, latitude: p.latitude}) AS officePoint
```

The [`point.distance()`](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-distance) function returns returns a `FLOAT` representing the geodesic distance between two points in the same Coordinate Reference System (CRS).

```cypher
RETURN point({x: 2.3, y: 4.5}) AS point
```

The [`point.withinBBox()`](https://neo4j.com/docs/cypher-manual/25/functions/spatial/#functions-withinBBox) function takes the following arguments: the `POINT` to check, the lower-left (south-west) `POINT` of a bounding box, and the upper-right (or north-east) `POINT` of a bounding box. The return value will be true if the provided point is contained in the bounding box (boundary included), otherwise the return value will be false.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_temporal_functions_duration)[Temporal functions - duration](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/)

```cypher
UNWIND [
duration({days: 14, hours:16, minutes: 12}),
duration({months: 5, days: 1.5}),
duration({months: 0.75}),
duration({weeks: 2.5}),
duration({minutes: 1.5, seconds: 1, milliseconds: 123, microseconds: 456, nanoseconds: 789}),
duration({minutes: 1.5, seconds: 1, nanoseconds: 123456789})
] AS aDuration
RETURN aDuration
```

The [`duration()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-durations) function can construct a `DURATION` from a `MAP` of its components.

```cypher
UNWIND [
duration("P14DT16H12M"),
duration("P5M1.5D"),
duration("P0.75M"),
duration("PT0.75M"),
duration("P2012-02-02T14:37:21.545"),
duration("5 hours 6 minutes", "h 'hours' m 'minutes'")
] AS aDuration
RETURN aDuration
```

The [`duration()` from a string](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-duration-create-string) function returns the `DURATION` value obtained by parsing a `STRING` representation of a temporal amount.

```cypher
UNWIND [
duration.between(date("1984-10-11"), date("1985-11-25")),
duration.between(date("1985-11-25"), date("1984-10-11")),
duration.between(date("1984-10-11"), datetime("1984-10-12T21:40:32.142+0100")),
duration.between(date("2015-06-24"), localtime("14:30")),
duration.between(localtime("14:30"), time("16:30+0100")),
duration.between(localdatetime("2015-07-21T21:40:32.142"), localdatetime("2016-07-21T21:45:22.142")),
duration.between(datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/Stockholm'}), datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/London'}))
] AS aDuration
RETURN aDuration
```

The [`duration.between()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-duration-between) function returns the `DURATION` value equal to the difference between the two given instants.

```cypher
UNWIND [
duration.inMonths(date("1984-10-11"), date("1985-11-25")),
duration.inMonths(date("1985-11-25"), date("1984-10-11")),
duration.inMonths(date("1984-10-11"), datetime("1984-10-12T21:40:32.142+0100")),
duration.inMonths(date("2015-06-24"), localtime("14:30")),
duration.inMonths(localdatetime("2015-07-21T21:40:32.142"), localdatetime("2016-07-21T21:45:22.142")),
duration.inMonths(datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/Stockholm'}), datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/London'}))
] AS aDuration
RETURN aDuration
```

The [`duration.inDays()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-duration-indays) function returns the `DURATION` value equal to the difference in whole days or weeks between the two given instants.

```cypher
UNWIND [
duration.inDays(date("1984-10-11"), date("1985-11-25")),
duration.inDays(date("1985-11-25"), date("1984-10-11")),
duration.inDays(date("1984-10-11"), datetime("1984-10-12T21:40:32.142+0100")),
duration.inDays(date("2015-06-24"), localtime("14:30")),
duration.inDays(localdatetime("2015-07-21T21:40:32.142"), localdatetime("2016-07-21T21:45:22.142")),
duration.inDays(datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/Stockholm'}), datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/London'}))
] AS aDuration
RETURN aDuration
```

The [`duration.inMonths()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-duration-inmonths) function returns the `DURATION` value equal to the difference in whole months between the two given instants.

```cypher
UNWIND [
duration.inSeconds(date("1984-10-11"), date("1984-10-12")),
duration.inSeconds(date("1984-10-12"), date("1984-10-11")),
duration.inSeconds(date("1984-10-11"), datetime("1984-10-12T01:00:32.142+0100")),
duration.inSeconds(date("2015-06-24"), localtime("14:30")),
duration.inSeconds(datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/Stockholm'}), datetime({year: 2017, month: 10, day: 29, hour: 0, timezone: 'Europe/London'}))
] AS aDuration
RETURN aDuration
```

The [`duration.inSeconds()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/duration/#functions-duration-inseconds) function returns the `DURATION` value equal to the difference in seconds and nanoseconds between the two given instants.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_temporal_functions_instant)[Temporal functions - instant](https://neo4j.com/docs/cypher-manual/25/functions/temporal/)

```cypher
RETURN date() AS currentDate
```

The [`date`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-date) function returns the current `DATE` value. If no time zone parameter is specified, the local time zone will be used.

```cypher
RETURN date.realtime() AS currentDate
```

The [`date.realtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-date-realtime) function returns the current `DATE` instant using the realtime clock.

```cypher
RETURN date.statement() AS currentDate
```

The [`date.statement()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-date-statement) function returns the current `DATE` instant using the statement clock.

```cypher
RETURN date.transaction() AS currentDate
```

The [`date.transaction()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-date-transaction) function returns the current `DATE` instant using the transaction clock.

```cypher
WITH
  datetime({
    year: 2017, month: 11, day: 11,
    hour: 12, minute: 31, second: 14, nanosecond: 645876123,
    timezone: '+01:00'
  }) AS d
RETURN
  date.truncate('millennium', d) AS truncMillenium,
  date.truncate('century', d) AS truncCentury,
  date.truncate('decade', d) AS truncDecade,
  date.truncate('year', d, {day: 5}) AS truncYear,
  date.truncate('weekYear', d) AS truncWeekYear,
  date.truncate('quarter', d) AS truncQuarter,
  date.truncate('month', d) AS truncMonth,
  date.truncate('week', d, {dayOfWeek: 2}) AS truncWeek,
  date.truncate('day', d) AS truncDay
```

The [`date.truncate()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-date-truncate) function truncates the given temporal value to a `DATE` instant using the specified unit.

```cypher
RETURN datetime() AS currentDateTime
```

The [`datetime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime) function creates a `ZONED DATETIME` instant.

```cypher
WITH datetime.fromEpoch(1683000000, 123456789) AS dateTimeFromEpoch
RETURN dateTimeFromEpoch
```

The [`datetime.fromEpoch()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-fromepoch) function creates a `ZONED DATETIME` given the seconds and nanoseconds since the start of the epoch.

```cypher
WITH datetime.fromEpochMillis(1724198400000) AS dateTimeFromMillis
RETURN dateTimeFromMillis
```

The [`datetime.fromEpochMillis()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-fromepochmillis) function creates a `ZONED DATETIME` given the milliseconds since the start of the epoch.

```cypher
RETURN datetime.realtime() AS currentDateTime
```

The [`datetime.realtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-realtime) function returns the current `ZONED DATETIME` instant using the realtime clock.

```cypher
RETURN datetime.statement() AS currentDateTime
```

The [`datetime.statement()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-statement) function returns the current `ZONED DATETIME` instant using the statement clock.

```cypher
RETURN datetime.transaction() AS currentDateTime
```

The [`datetime.transaction()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-transaction) function returns the current `ZONED DATETIME` instant using the transaction clock.

```cypher
WITH
  datetime({
    year:2017, month:11, day:11,
    hour:12, minute:31, second:14, nanosecond: 645876123,
    timezone: '+03:00'
  }) AS d
RETURN
  datetime.truncate('millennium', d, {timezone: 'Europe/Stockholm'}) AS truncMillenium,
  datetime.truncate('year', d, {day: 5}) AS truncYear,
  datetime.truncate('month', d) AS truncMonth,
  datetime.truncate('day', d, {millisecond: 2}) AS truncDay,
  datetime.truncate('hour', d) AS truncHour,
  datetime.truncate('second', d) AS truncSecond
```

The [`datetime.truncate()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-datetime-truncate) function truncates the given temporal value to a `ZONED DATETIME` instant using the specified unit.

```cypher
RETURN
  localdatetime({
    year: 1984, ordinalDay: 202,
    hour: 12, minute: 31, second: 14, microsecond: 645876
  }) AS theDate
```

The [`localdatetime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localdatetime) function creates a `LOCAL DATETIME` instant.

```cypher
RETURN localdatetime.realtime() AS now
```

The [`localdatetime.realtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localdatetime-realtime) function returns the current `LOCAL DATETIME` instant using the realtime clock.

```cypher
RETURN localdatetime.statement() AS now
```

The [`localdatetime.statement()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localdatetime-statement) function returns the current `LOCAL DATETIME` instant using the statement clock.

```cypher
RETURN localdatetime.transaction() AS now
```

The [`localdatetime.transaction()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localdatetime-transaction) function returns the current `LOCAL DATETIME` instant using the transaction clock.

```cypher
WITH
  localdatetime({
    year: 2017, month: 11, day: 11,
    hour: 12, minute: 31, second: 14, nanosecond: 645876123
  }) AS d
RETURN
  localdatetime.truncate('millennium', d) AS truncMillenium,
  localdatetime.truncate('year', d, {day: 2}) AS truncYear,
  localdatetime.truncate('month', d) AS truncMonth,
  localdatetime.truncate('day', d) AS truncDay,
  localdatetime.truncate('hour', d, {nanosecond: 2}) AS truncHour,
  localdatetime.truncate('second', d) AS truncSecond
```

The [`localdatetime.truncate()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localdatetime-truncate) function truncates the given temporal value to a `LOCAL DATETIME` instant using the specified unit.

```cypher
RETURN localtime() AS now
```

The [`localtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localtime) function creates a `LOCAL TIME` instant.

```cypher
RETURN localtime.realtime() AS now
```

The [`localtime.realtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localtime-realtime) function creates a `LOCAL TIME` instant. function returns the current `LOCAL TIME` instant using the realtime clock.

```cypher
RETURN localtime.statement() AS now
```

The [`localtime.statement()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localtime-statement) function creates a `LOCAL TIME` instant. function returns the current `LOCAL TIME` instant using the statement clock.

```cypher
RETURN localtime.transaction() AS now
```

The [`localtime.transaction()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localtime-transaction) function returns the current `LOCAL TIME` instant using the transaction clock.

```cypher
WITH time({hour: 12, minute: 31, second: 14, nanosecond: 645876123, timezone: '-01:00'}) AS t
RETURN
  localtime.truncate('day', t) AS truncDay,
  localtime.truncate('hour', t) AS truncHour,
  localtime.truncate('minute', t, {millisecond: 2}) AS truncMinute,
  localtime.truncate('second', t) AS truncSecond,
  localtime.truncate('millisecond', t) AS truncMillisecond,
  localtime.truncate('microsecond', t) AS truncMicrosecond
```

The [`localtime.truncate()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-localtime-truncate) function truncates the given temporal value to a `LOCAL TIME` instant using the specified unit.

```cypher
RETURN time() AS currentTime
```

The [`time()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-time) function creates a `ZONED TIME` instant.

```cypher
RETURN time.realtime() AS currentTime
```

The [`time.realtime()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-time-realtime) function returns the current `ZONED TIME` instant using the realtime clock.

```cypher
RETURN time.statement() AS currentTime
```

The [`time.statement()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-time-statement) function returns the current `ZONED TIME` instant using the statement clock.

```cypher
RETURN time.transaction() AS currentTime
```

The [`time.transaction()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-time-transaction) function returns the current `ZONED TIME` instant using the transaction clock.

```cypher
WITH time({hour: 12, minute: 31, second: 14, nanosecond: 645876123, timezone: '-01:00'}) AS t
RETURN
  time.truncate('day', t) AS truncDay,
  time.truncate('hour', t) AS truncHour,
  time.truncate('minute', t) AS truncMinute,
  time.truncate('second', t) AS truncSecond,
  time.truncate('millisecond', t, {nanosecond: 2}) AS truncMillisecond,
  time.truncate('microsecond', t) AS truncMicrosecond
```

The [`time.truncate()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/#functions-time-truncate) function truncates the given temporal value to a `ZONED TIME` instant using the specified unit.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_temporal_functions_format)[Temporal functions - format](https://neo4j.com/docs/cypher-manual/25/functions/temporal/format/)

```cypher
WITH datetime('1986-11-18T6:04:45.123456789+01:00[Europe/Berlin]') AS dt
RETURN format(dt, "MM/dd/yyyy") AS US, format(dt, "dd/MM/yyyy") AS EU
```

The [`format()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/format/#query-functions-temporal-format-function) function can format instance types, for example as US American and European date strings.

```cypher
WITH duration({years: 1, months: 4}) AS d
RETURN format(d, "y 'years' q 'quarters' M 'months'") AS withYears, format(d, "q 'quarters' M 'months'") AS withoutYears
```

The [`format()`](https://neo4j.com/docs/cypher-manual/25/functions/temporal/format/#query-functions-temporal-format-function) function can format duration types as strings.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_vector_functions)[Vector functions](https://neo4j.com/docs/cypher-manual/25/functions/vector/)

```cypher
MATCH (n:Label)
WITH n, vector.similarity.euclidean($query, n.vector) AS score
RETURN n, score
```

The [`vector.similarity.euclidean()`](https://neo4j.com/docs/cypher-manual/25/functions/vector/#functions-similarity-euclidean) function returns a `FLOAT` representing the similarity between the argument vectors based on their Euclidean distance.

```cypher
MATCH (n:Label)
WITH n, vector.similarity.cosine($query, n.vector) AS score
RETURN n, score
```

The [`vector.similarity.cosine()`](https://neo4j.com/docs/cypher-manual/25/functions/vector/#functions-similarity-cosine) function returns a `FLOAT` representing the similarity between the argument vectors based on their cosine.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_procedures)Procedures

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_call_procedures)[CALL procedures](https://neo4j.com/docs/operations-manual/current/procedures/call-procedures)

```cypher
CALL db.labels()
```

Standalone procedure call.

```cypher
CALL dbms.checkConfigValue('server.bolt.enabled', 'true')
```

Call a procedure using literal arguments.

```cypher
CALL dbms.checkConfigValue($setting, $value)
```

Call a procedure using parameters as arguments.

```cypher
CALL db.propertyKeys() YIELD propertyKey AS prop
MATCH (n)
WHERE n[prop] IS NOT NULL
RETURN prop, count(n) AS numNodes
```

Filter procedure call using `YIELD`.

```cypher
MATCH (n)
OPTIONAL CALL apoc.neighbors.tohop(n, "KNOWS>", 1)
YIELD node
RETURN n.name AS name, collect(node.name) AS connections
```

Optional procedure call. Any empty rows produced by `OPTIONAL CALL` return `null`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show_procedures)[SHOW procedures](https://neo4j.com/docs/operations-manual/current/procedures/show-procedures)

```cypher
SHOW PROCEDURES
```

Show all procedures in a database and return default columns (`name`, `description`, `mode`, and `worksOnSystem`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW PROCEDURES EXECUTABLE BY CURRENT USER YIELD *
```

Procedures can be filtered on whether a user can execute them. This filtering is only available through the `EXECUTABLE` clause and not through the `WHERE` clause. This example filters on the procedures executable by the current user.

```cypher
SHOW PROCEDURES EXECUTABLE BY jake
```

Filter on the procedures executable by a specific user.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_indexes)Indexes

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_search_performance_indexes)[Search-performance indexes](https://neo4j.com/docs/cypher-manual/25/indexes/search-performance-indexes/)

Cypher includes four search-performance indexes: range (default), text, point, and token lookup.

```cypher
CREATE INDEX node_range_index_name FOR (n:Person) ON (n.surname)
```

The create syntax for creating indexes is: `CREATE [RANGE|TEXT|POINT|LOOKUP|FULLTEXT|VECTOR] INDEX …​`. If no index type is specified, a range index will be created since it supports most types of predicates. This example, therefore, creates a range index.

Best practice is to always specify a sensible name when creating a index.

```cypher
CREATE INDEX node_range_index_name IF NOT EXISTS
FOR (n:Person) ON (n.surname)
```

To avoid failing on existing indexes, `IF NOT EXISTS` can be added to the `CREATE` command. This will ensure that no error is thrown and that no index is created if there already exists an index with the same schema and type, same name or both.

```cypher
CREATE INDEX composite_range_rel_index_name FOR ()-[r:PURCHASED]-() ON (r.date, r.amount)
```

Create a composite range index on multiple properties.

```cypher
CREATE INDEX $name FOR (n:Person) ON (n.firstname)
```

Create a range index with a parameterized name. All index types can be created in this way.

```cypher
CREATE TEXT INDEX node_text_index_nickname FOR (n:Person) ON (n.nickname)
```

Create a text index. Text indexes only solve predicates operating on `STRING` values.

```cypher
CREATE POINT INDEX rel_point_index_name FOR ()-[r:STREET]-() ON (r.intersection)
```

Create a point index. Point indexes only solve predicates operating on `POINT` values.

```cypher
CREATE POINT INDEX point_index_with_config
FOR (n:Label) ON (n.prop2)
OPTIONS {
  indexConfig: {
    `spatial.cartesian.min`: [-100.0, -100.0],
    `spatial.cartesian.max`: [100.0, 100.0]
  }
}
```

Create a point index with a specific configuration.

```cypher
CREATE LOOKUP INDEX node_label_lookup_index FOR (n) ON EACH labels(n)
```

Create a node token lookup index. Two token lookup indexes are present by default (node token lookup and relationship token lookup) and solve only node label and relationship type predicates. It is not recommended to remove lookup indexes.

```cypher
SHOW INDEXES
```

Show all indexes and return default columns(`id`, `name`, `state`, `populationPercent`, `type`, `entityType`, `labelsOrTypes`, `properties`, `indexProvider`, `owningConstraint`, `lastRead`, and `readCount`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW RANGE INDEXES WHERE owningConstraint IS NULL
```

`SHOW INDEXES` can be filtered on index type. The available types are: `ALL`, `FULLTEXT`, `LOOKUP`, `POINT`, `RANGE`, `TEXT`, and `VECTOR`.

```cypher
DROP INDEX example_index
```

Drop an index by name.

```cypher
DROP INDEX $name
```

Drop an index by parameterized name.

```cypher
PROFILE
MATCH
  (s:Scientist {born: 1850})-[:RESEARCHED]->
  (sc:Science)<-[i:INVENTED_BY {year: 560}]-
  (p:Pioneer {born: 525})-[:LIVES_IN]->
  (c:City)-[:PART_OF]->
  (cc:Country {formed: 411})
USING INDEX i:INVENTED_BY(year)
RETURN *
```

Index usage can be enforced when Cypher uses a suboptimal index, or when more than one index should be used.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_full_text_indexes)[Full-text indexes](https://neo4j.com/docs/cypher-manual/25/indexes/semantic-indexes/full-text-indexes/)

```cypher
CREATE FULLTEXT INDEX namesAndTeams IF NOT EXISTS
FOR (n:Employee|Manager) ON EACH [n.name, n.team]
```

Create a fulltext index. With `IF NOT EXISTS`, no error is thrown and nothing happens should an index with the same name, schema or both already exist.

Best practice is to always specify a sensible name when creating an index.

```cypher
CREATE FULLTEXT INDEX $name FOR (n:Employee|Manager) ON EACH [n.peerReviews]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: true
  }
}
```

Create a fulltext index using the `OPTIONS` map to specify an `indexConfig`.

```cypher
CALL db.index.fulltext.queryNodes("namesAndTeams", "nils") YIELD node, score
RETURN node.name, score
```

Query a node fulltext index with the `db.index.fulltext.queryNodes()` procedure. Fulltext indexes on relationships are queried using the `db.index.fulltext.queryRelationships()` procedure.

```cypher
SHOW FULLTEXT INDEXES
```

Show all fulltext indexes. For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
DROP INDEX communications
```

Drop a fulltext index by name.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_vector_indexes)[Vector indexes](https://neo4j.com/docs/cypher-manual/25/indexes/semantic-indexes/vector-indexes/)

```cypher
CREATE VECTOR INDEX moviePlots IF NOT EXISTS
FOR (m:Movie)
ON m.embedding
OPTIONS { indexConfig: {
 `vector.dimensions`: 1536,
 `vector.similarity_function`: 'cosine'
}}
```

Create a vector index, specifying vector dimension and similarity function. With `IF NOT EXISTS`, no error is thrown and nothing happens should an index with the same name, schema or both already exist.

Best practice is to always specify a sensible name when creating an index.

```cypher
CREATE VECTOR INDEX multiLabelAdditionalProperties IF NOT EXISTS
FOR (n:Movie|Actor)
ON n.embedding
WITH [n.title, n.plot, n.name, n.born]
OPTIONS { indexConfig: {
 `vector.dimensions`: 1536,
 `vector.similarity_function`: 'cosine'
}}
```

Create a vector index for multiple labels and with additional properties used for filtering.

```cypher
MATCH (m:Movie {title: 'Godfather, The'})
MATCH (movie: Movie)
  SEARCH movie IN (
    VECTOR INDEX moviePlots
    FOR m.embedding
    LIMIT 5
  ) SCORE AS score
RETURN movie.title AS title, movie.plot AS plot, score
```

Query a vector index using the `SEARCH` clause.

```cypher
SHOW VECTOR INDEXES
```

Show all vector indexes. For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
DROP INDEX moviePlots
```

Drop a vector index by name.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_schema)Schema

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_constraints)[Constraints](https://neo4j.com/docs/cypher-manual/25/schema/constraints/)

```cypher
CREATE CONSTRAINT book_isbn
FOR (book:Book) REQUIRE book.isbn IS UNIQUE
```

Create a node property uniqueness constraint.

Best practice is to always specify a sensible name when creating a constraint.

```cypher
CREATE CONSTRAINT sequels IF NOT EXISTS
FOR ()-[sequel:SEQUEL_OF]-() REQUIRE sequel.order IS UNIQUE
```

Create a relationship property uniqueness constraint.

Appending the keyword `IF NOT EXISTS` to any `CREATE CONSTRAINT` command makes the command idempotent, and no error will be thrown if an attempt is made to create the same constraint twice.Expand commentComment on line R21Resolved

```cypher
CREATE CONSTRAINT prequels
FOR ()-[prequel:PREQUEL_OF]-() REQUIRE (prequel.order, prequel.author) IS UNIQUE
```

Create a composite relationship property uniqueness constraint on several properties.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT author_name
FOR (author:Author) REQUIRE author.name IS NOT NULL
```

Create a node property existence constraint.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT part_of
FOR ()-[part:PART_OF]-() REQUIRE part.order IS :: INTEGER
```

Create a relationship property type constraint.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT movie_tagline
FOR (movie:Movie) REQUIRE movie.tagline IS :: STRING | LIST<STRING NOT NULL>
```

Create a node property type constraint with dynamic union type, allowing the constrained property to be of more than one type.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT director_imdbId
FOR (director:Director) REQUIRE (director.imdbId) IS NODE KEY
```

Create a node key constraint.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT knows_since_how
FOR ()-[knows:KNOWS]-() REQUIRE (knows.since, knows.how) IS RELATIONSHIP KEY
```

Create a composite relationship key constraint on several properties.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
CREATE CONSTRAINT $name
FOR (book:Book) REQUIRE book.prop1 IS UNIQUE
```

Create a constraint with a parameterized constraint name.

```cypher
SHOW CONSTRAINTS
```

Show all constraints and return default columns (`id`, `name`, `type`, `entityType`, `labelsOrTypes`, `properties`, `ownedIndex`, and `propertyType`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW KEY CONSTRAINTS
```

`SHOW CONSTRAINTS` can be filtered on constraint type. The available types are: `NODE PROPERTY UNIQUENESS`, `RELATIONSHIP PROPERTY UNIQUENESS`, `PROPERTY UNIQUENESS`, `NODE EXISTENCE`, `RELATIONSHIP EXISTENCE`, `EXISTENCE`, `NODE PROPERTY EXISTENCE`, `RELATIONSHIP PROPERTY EXISTENCE`, `PROPERTY EXISTENCE`, `NODE PROPERTY TYPE`, `RELATIONSHIP PROPERTY TYPE`, `PROPERTY TYPE`, `NODE KEY`, `RELATIONSHIP KEY`, and `KEY`.

```cypher
DROP CONSTRAINT book_isbn
```

Drop a constraint by its name.

```cypher
DROP CONSTRAINT $name
```

Drop a constraint using a parameterized name.

```cypher
DROP CONSTRAINT missing_constraint_name IF EXISTS
```

Appending `IF EXISTS` to `DROP CONSTRAINT` makes the command idempotent; if a constraint with the given name exists, it will be dropped; otherwise, no error will be thrown.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_graph_types)[Graph types](https://neo4j.com/docs/cypher-manual/25/schema/graph-types/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE SET {
    (p:Person => :Resident {name :: STRING, ssn :: INTEGER})
      REQUIRE (p.name, p.ssn) IS KEY,
    (:Pet => :Resident&Animal {insuranceNumber :: INTEGER IS KEY, healthCertificate :: STRING IS UNIQUE, name :: STRING}),
    (:Robot => :Resident {application :: STRING NOT NULL}),
    (:City => {name :: STRING NOT NULL, population :: INTEGER}),
    (:Resident)-[:LIVES_IN => {since :: DATE NOT NULL}]->(:City),
    CONSTRAINT company_name FOR (c:Company) REQUIRE c.name IS KEY,
    CONSTRAINT animal_id FOR (a:Animal) REQUIRE a.id IS UNIQUE,
    CONSTRAINT resident_address FOR (resident:Resident) REQUIRE resident.address :: STRING
}
```

Graph types can be set with command `ALTER CURRENT GRAPH TYPE SET`. A graph type enables users to impose a schema on the nodes, relationships, and properties included in the graph type. Cypher supports open graph types, meaning that a graph type only constrains the data included by the graph type. It does not impose any constraints on nodes, relationships, and properties not included by the graph type. **Setting a graph type will replace any existing graph type/constraints in a database.**

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE ADD {
    (:Company => {name :: STRING, address :: STRING IS UNIQUE}),
    (:Person)-[:WORKS_FOR => {role :: STRING}]->(:Company)
}
```

Graph types can be extended with the command `ALTER CURRENT GRAPH TYPE ADD`.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE ALTER {
    (:Robot => :Resident&Machine {application :: STRING NOT NULL, id :: INTEGER NOT NULL}),
    (:Resident)-[:LIVES_IN => {since :: ANY NOT NULL}]->(:City)
}
```

The node element types and relationship element types in a graph type can be altered with the command `ALTER CURRENT GRAPH TYPE ALTER`. **This replaces the previous definition of that element type with the new definition.**

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
SHOW CURRENT GRAPH TYPE
```

The graph type of a database can be shown using the command `SHOW CURRENT GRAPH TYPE`. This command returns one column, `specification`, which is returned by default. For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
SHOW CURRENT GRAPH TYPE AS GRAPH
```

The graph type of a database can be shown as a virtual graph using the command `SHOW CURRENT GRAPH TYPE AS GRAPH`. This command returns two columns, `nodes` and `relationships`. Both are returned by default. For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE DROP {
    (:Pet => ),
    ()-[:LIVES_IN => ]->()
}
```

Node element types and relationship element types can be dropped from a graph type with the command `ALTER CURRENT GRAPH TYPE DROP`.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE DROP {
    CONSTRAINT animal_id,
    CONSTRAINT constraint_302a3693
}
```

Constraints in a graph type can be dropped using the `CONSTRAINT name` syntax inside the `ALTER CURRENT GRAPH TYPE DROP` command.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER CURRENT GRAPH TYPE SET { }
```

To drop a full graph type, use the `ALTER CURRENT GRAPH TYPE SET` command. This will replace the existing graph type with a new (possibly empty) graph type.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_performance)Performance

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_performance_2)[Performance](https://neo4j.com/docs/cypher-manual/25/planning-and-tuning/query-tuning/)

Use parameters instead of literals when possible. This allows Neo4j DBMS to cache your queries instead of having to parse and build new execution plans.

Always set an upper limit for your variable length patterns. It is possible to have a query go wild and touch all nodes in a graph by mistake.

Return only the data you need. Avoid returning whole nodes and relationships; instead, pick the data you need and return only that.

Use `PROFILE` / `EXPLAIN` to analyze the performance of your queries. See [Query Tuning](https://neo4j.com/docs/cypher-manual/25/planning-and-tuning/query-tuning/) for more information on these and other topics, such as planner hints.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_configuration_settings)Configuration settings

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show_settings)[SHOW SETTINGS](https://neo4j.com/docs/operations-manual/current/configuration/show-settings/)

Community EditionEnterprise Edition

Community EditionEnterprise Edition

```cypher
SHOW SETTINGS
```

Show configuration settings (within the instance) and return default columns (`name`, `value`, `isDynamic`, `defaultValue`, and `description`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

Community EditionEnterprise Edition

```cypher
SHOW SETTINGS 'server.bolt.advertised_address', 'server.bolt.listen_address' YIELD *
```

Show the configuration settings (within the instance) named `server.bolt.advertised_address` and `server.bolt.listen_address`. As long as the setting names evaluate to a string or a list of strings at runtime, they can be any expression.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_transactions)Transactions

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_transaction_management)[TRANSACTION management](https://neo4j.com/docs/operations-manual/current/database-internals/show-and-terminate-transactions/)

```cypher
SHOW TRANSACTIONS
```

Show running transactions (within the instance) and return default columns (`database`, `transactionId`, `currentQueryId`, `connectionId`, `clientAddress`, `username`, `currentQuery`, `startTime`, `status`, and `elapsedTime`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW TRANSACTIONS 'transaction_id' YIELD *
```

Show the running transaction (within the instance), with a specific `transaction_id`. As long as the transaction IDs evaluate to a string or a list of strings at runtime, they can be any expression.

```cypher
TERMINATE TRANSACTIONS 'transaction_id'
```

Terminate a transaction with a specific `transaction_id`. Returns the `transactionId`, `username`, and `message` columns. As long as the transaction IDs evaluate to a string or a list of strings at runtime, they can be any expression.

```cypher
TERMINATE TRANSACTIONS "neo4j-transaction-1","neo4j-transaction-2"
YIELD transactionId, message
WHERE message <> "Transaction terminated."
```

`TERMINATE TRANSACTIONS` can be filtered using `WHERE`. If so, the `YIELD` clause is mandatory (in contrast to the `SHOW TRANSACTIONS` command, which does not require it).

```cypher
SHOW TRANSACTIONS
YIELD transactionId AS txId, username AS user
WHERE user = "Alice"
TERMINATE TRANSACTIONS txId
YIELD message
RETURN txId, message
```

`TERMINATE TRANSACTIONS` and `SHOW TRANSACTIONS` can be combined to identify and terminate transactions in the same statement. Multiple `SHOW` and `TERMINATE` transactions can be included in a single statement. This example shows all transactions run by user `Alice` and terminates them.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_database_management)Database Management

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_database_management_2)[DATABASE Management](https://neo4j.com/docs/operations-manual/current/database-administration/standard-databases/manage-databases/)

```none
dba
`db1`
`database-name`
`database-name-123`
`database.name`
`database.name.123`
```

The naming rules for a database:

-   The character length of a database name must be at least `3` characters; and not more than `63` characters.

-   The first character of a database name must be an ASCII alphabetic character.

-   Subsequent characters must be ASCII alphabetic or numeric characters, dots or dashes; `[a..z][0..9].-`.

-   Database names are case-insensitive and normalized to lowercase.

-   Database names that begin with an underscore (`_`) or with the prefix `system` are reserved for internal use.


Database names may include dots (`.`) without being quoted with backticks, although this behavior is deprecated as it may introduce ambiguity when addressing composite databases. Naming a database `foo.bar.baz` is valid, but deprecated. `` `foo.bar.baz` `` is valid.

Enterprise Edition

```cypher
CREATE DATABASE `database-name` IF NOT EXISTS
```

Create a standard database named `database-name` if it does not already exist.

Enterprise Edition

```cypher
CREATE OR REPLACE DATABASE `database-name`
```

Create a standard database named `database-name`. If a database with that name exists, then the existing database is deleted and a new one created.

Enterprise Edition

```cypher
CREATE DATABASE `topology-example` IF NOT EXISTS
TOPOLOGY 1 PRIMARY 0 SECONDARIES
```

Create a standard database named `topology-example` in a cluster environment, to use 1 primary server and 0 secondary servers.

Enterprise Edition

```cypher
CREATE COMPOSITE DATABASE `composite-database-name`
```

Create a composite database named `composite-database-name`.

Enterprise Edition

```cypher
CREATE DATABASE actors SET DEFAULT LANGUAGE CYPHER 25
```

Set the default Cypher version for a standard or composite database when creating it. The available versions are `CYPHER 25` and `CYPHER 5`. If not specified, the default language for the database is set to the default language of the DBMS.

Enterprise Edition

```cypher
STOP DATABASE `database-name`
```

Stop a database named `database-name`.

Enterprise Edition

```cypher
START DATABASE `database-name`
```

Start a database named `database-name`.

Enterprise Edition

```cypher
ALTER DATABASE `database-name` IF EXISTS
SET ACCESS READ ONLY
```

Modify a standard database named `database-name` to accept only read queries.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER DATABASE actors SET DEFAULT LANGUAGE CYPHER 5
```

Alter the default Cypher version of an existing standard or composite database. The available versions are `CYPHER 25` and `CYPHER 5`.

Enterprise Edition

```cypher
ALTER DATABASE `database-name` IF EXISTS
SET ACCESS READ WRITE
```

Modify a standard database named `database-name` to accept write and read queries.

Enterprise Edition

```cypher
ALTER DATABASE `topology-example`
SET TOPOLOGY 1 PRIMARY 0 SECONDARIES
```

Modify a standard database named `topology-example` in a cluster environment to use 1 primary server and 0 secondary servers.

Enterprise Edition

```cypher
ALTER DATABASE `topology-example`
SET TOPOLOGY 1 PRIMARY
SET ACCESS READ ONLY
```

Modify a standard database named `topology-example` in a cluster environment to use 1 primary server and 0 secondary servers, and to only accept read queries.

```cypher
SHOW DATABASES
```

Show all databases in Neo4j DBMS and return default columns (`name`, `type`, `aliases`, `access`, `address`, `role`, `writer`, `requestedStatus`, `currentStatus`, `statusMessage`, `default`, `home`, and `constituents`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW DATABASE `database-name` YIELD *
```

Show information about the database `database-name`.

```cypher
SHOW DEFAULT DATABASE
```

Show information about the default database, for the Neo4j DBMS.

```cypher
SHOW HOME DATABASE
```

Show information about the current users home database.

Enterprise Edition

```cypher
DROP DATABASE `database-name` IF EXISTS
```

Delete the database `database-name`, if it exists. This command can delete both standard and composite databases.

Enterprise Edition

```cypher
DROP COMPOSITE DATABASE `composite-database-name`
```

Delete the database named `composite-database-name`. In case the given database name does not exist or is not composite, and error will be thrown.

Enterprise Edition

```cypher
DROP DATABASE `topology-example` CASCADE ALIASES
```

Drop the database `topology-example` and any database aliases referencing the database. This command can drop both standard and composite databases. For standard databases, the database aliases that will be dropped are any local database aliases targeting the database. For composite databases, the database aliases that will be dropped are any constituent database aliases belonging to the composite database.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_alias_management)[ALIAS Management](https://neo4j.com/docs/operations-manual/current/database-administration/aliases/manage-aliases-standard-databases/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
CREATE ALIAS `database-alias` IF NOT EXISTS
FOR DATABASE `database-name`
```

Create a local alias named `database-alias` for the database named `database-name`.

```cypher
CREATE OR REPLACE ALIAS `database-alias`
FOR DATABASE `database-name`
```

Create or replace a local alias named `database-alias` for the database named `database-name`.

```cypher
CREATE ALIAS `database-alias`
FOR DATABASE `database-name`
PROPERTIES { property = $value }
```

Database aliases can be given properties.

```cypher
CREATE ALIAS `database-alias`
FOR DATABASE `database-name`
AT $url
USER user_name
PASSWORD $password
```

Create a remote alias named `database-alias` for the database named `database-name`.

```cypher
CREATE ALIAS `remote-with-default-language`
FOR DATABASE `northwind-graph-2020`
	AT "neo4j+s://location:7687"
	USER alice
	PASSWORD 'example_secret'
	DEFAULT LANGUAGE CYPHER 25
```

Set the default Cypher version for a remote database alias when creating it. The available versions are `CYPHER 5` and `CYPHER 25`. Local database aliases and database aliases in composite databases cannot be assigned a default Cypher version. Local database aliases always have the Cypher version of their target database and database aliases in composite databases always have the Cypher version of the composite database they belong to.

```cypher
CREATE ALIAS `composite-database-name`.`alias-in-composite-name`
FOR DATABASE `database-name`
AT $url
USER user_name
PASSWORD $password
```

Create a remote alias named `alias-in-composite-name` as a constituent alias in the composite database named `composite-database-name` for the database with name `database-name`.

```cypher
ALTER ALIAS `database-alias` IF EXISTS
SET DATABASE TARGET `database-name`
```

Alter the alias named `database-alias` to target the database named `database-name`.

```cypher
ALTER ALIAS `remote-database-alias` IF EXISTS
SET DATABASE
USER user_name
PASSWORD $password
```

Alter the remote alias named `remote-database-alias`, set the username (`user_name`) and the password.

```cypher
ALTER ALIAS `database-alias`
SET DATABASE PROPERTIES { key: value }
```

Update the properties for the database alias named `database-alias`.

```cypher
ALTER ALIAS `remote-with-default-language` SET DATABASE DEFAULT LANGUAGE CYPHER 25
```

Alter the default Cypher version of a remote database alias. The available versions are `CYPHER 25` and `CYPHER 5`. It is not possible to alter the default Cypher version of a local database alias or an alias belonging to a composite database. Local database aliases always have the Cypher version of their target database and aliases belonging to composite databases always have the Cypher version of the composite database.

```cypher
SHOW ALIASES FOR DATABASE
```

Show all database aliases in Neo4j DBMS and return default columns (`name`, `composite`, `database`, `location`, `url`, and `user`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW ALIASES `database-alias` FOR DATABASE
```

Show the database alias named `database-alias` and the information about it.

```cypher
DROP ALIAS `database-alias` IF EXISTS FOR DATABASE
```

Delete the alias named `database-alias`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_server_management)[SERVER Management](https://neo4j.com/docs/operations-manual/current/clustering/servers/)

AuraDB Business CriticalAuraDB Virtual Dedicated Cloud

```cypher
SHOW SERVERS
```

Show all servers running in the cluster (including servers that have yet to be enabled as well as dropped servers) and return default columns (`name`, `address`, `state`, `health`, and `hosting`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

Enterprise Edition

```cypher
ENABLE SERVER 'serverId'
```

Make the server with the ID `serverId` an active member of the cluster.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
RENAME SERVER 'oldName' TO 'newName'
```

Change the name of a server.

Enterprise Edition

```cypher
ALTER SERVER 'name' SET OPTIONS {modeConstraint: 'PRIMARY'}
```

Only allow the specified server to host databases in primary mode.

Enterprise Edition

```cypher
REALLOCATE DATABASES
```

Re-balance databases among the servers in the cluster.

Enterprise Edition

```cypher
DEALLOCATE DATABASES FROM SERVER 'name'
```

Remove all databases from the specified server, adding them to other servers as needed. The specified server is not allowed to host any new databases.

Enterprise Edition

```cypher
DROP SERVER 'name'
```

Remove the specified server from the cluster.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_access_control)Access Control

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_user_management)[USER Management](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/)

```cypher
CREATE USER user_name
SET PASSWORD $password
```

Create a new user and set the password. This password must be changed on the first login.

```cypher
CREATE USER new_user
SET AUTH 'native' {
  SET PASSWORD $password
  SET PASSWORD CHANGE REQUIRED
}
```

Create a new user and set the password using the auth provider syntax. This password must be changed on the first login.

```cypher
RENAME USER user_name TO renamed_user_name
```

Rename the specified user.

```cypher
ALTER CURRENT USER
SET PASSWORD FROM $oldPassword TO $newPassword
```

Change the password of the logged-in user. The user will not be required to change this password on the next login.

```cypher
ALTER USER renamed_user_name
SET PASSWORD $newPassword
CHANGE NOT REQUIRED
```

Set a new password (a String) for a user. This user will not be required to change this password on the next login.

```cypher
ALTER USER renamed_user_name IF EXISTS
SET PASSWORD CHANGE REQUIRED
```

If the specified user exists, force this user to change the password on the next login.

Enterprise Edition

```cypher
ALTER USER renamed_user_name
SET AUTH 'externalProviderName' {
  SET ID 'userIdForExternalProvider'
}
```

Add another way for the user to authenticate and authorize using the external provider `externalProviderName`. This provider needs to be defined in the configurations settings.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER USER renamed_user_name
SET STATUS SUSPENDED
```

Change the status to `SUSPENDED`, for the specified user.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
ALTER USER renamed_user_name
SET STATUS ACTIVE
```

Change the status to `ACTIVE`, for the specified user.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
ALTER USER renamed_user_name
SET HOME DATABASE `database-name`
```

Set the home database for the specified user. The home database can either be a database or an alias.

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
ALTER USER renamed_user_name
REMOVE HOME DATABASE
```

Unset the home database for the specified user and fallback to the default database.

```cypher
SHOW USERS
```

List all users in Neo4j DBMS, returns only the default outputs (`user`, `roles`, `passwordChangeRequired`, `suspended`, and `home`).

```cypher
SHOW CURRENT USER
```

List the currently logged-in user, returns only the default outputs (`user`, `roles`, `passwordChangeRequired`, `suspended`, and `home`).

AuraDB Business CriticalAuraDB Virtual Dedicated CloudAuraDB FreeAuraDB ProfessionalAuraDS EnterpriseAuraDS ProfessionalEnterprise Edition

```cypher
SHOW USERS
WHERE suspended = true
```

List users that are suspended.

```cypher
SHOW USERS
WHERE passwordChangeRequired
```

List users that must change their password at the next login.

```cypher
SHOW USERS WITH AUTH
```

List users with their auth providers. Will return one row per user per auth provider.

```cypher
SHOW USERS WITH AUTH WHERE provider = 'oidc1'
```

List users who have the `oidc1` auth provider.

```cypher
DROP USER renamed_user_name
```

Delete the specified user.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_role_management)[ROLE Management](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-roles/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
CREATE ROLE role_name IF NOT EXISTS
```

Create a role, unless it already exists.

```cypher
CREATE ROLE copy_role_name AS COPY OF role_name
```

Create a role, as a copy of the existing `role_name`.

```cypher
RENAME ROLE role_name TO renamed_role_name
```

Rename a role.

```cypher
GRANT ROLE renamed_role_name, copy_role_name TO user_name
```

Assign roles to a user.

```cypher
REVOKE ROLE renamed_role_name FROM user_name
```

Remove the specified role from a user.

```cypher
SHOW ROLES
```

Show all roles in the system and return default column (`role`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW POPULATED ROLES
```

Show all roles that are assigned to at least one user in the system.

```cypher
SHOW POPULATED ROLES WITH USERS
```

Show all roles that are assigned to at least one user in the system, and the users assigned to those roles. The returned outputs are `role` and `member`.

```cypher
SHOW POPULATED ROLES WITH USERS
YIELD member, role
WHERE member = $user
RETURN role
```

Show all roles that are assigned to a `$user`.

```cypher
DROP ROLE renamed_role_name
```

Delete a role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_auth_management)[AUTH Management](https://neo4j.com/docs/operations-manual/current/authentication-authorization/attribute-based-access-control/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
CREATE AUTH RULE salesRule
    SET CONDITION abac.oidc.user_attribute('department') = 'sales'
```

Creates an auth rule named `salesRule`. Users whose OIDC token contains `department = 'sales'` are granted the roles assigned to this rule.

```cypher
CREATE AUTH RULE ruleset_countries SET CONDITION
  any(country IN abac.oidc.user_attribute('citizenshipCountries')
    WHERE country IN ['c1', 'c5'])
```

Create auth rules based on a list of values.

```cypher
CREATE OR REPLACE AUTH RULE managementRule
    SET CONDITION abac.oidc.user_attribute('department') = 'management'
```

Adding `OR REPLACE` to the command deletes any existing auth rule with the same name and creates a new auth rule with the same name. Any assigned roles associated with the old auth rule will not be associated to the new auth rule.

```cypher
CREATE AUTH RULE managementRule IF NOT EXISTS
    SET CONDITION abac.oidc.user_attribute('department') = 'management'
```

Appending `IF NOT EXISTS` to the command ensures that no error is returned and nothing happens should a rule with the same name already exists, and the command has no effect. `OR REPLACE` and `IF NOT EXISTS` cannot be used at the same time.

```cypher
CREATE AUTH RULE managementRule
    SET CONDITION abac.oidc.user_attribute('department') = 'sales'
    SET ENABLED false
```

`SET ENABLED false` creates the rule in a disabled state so it is not evaluated until explicitly enabled. Default is `true`.

```cypher
GRANT ROLE management TO AUTH RULE managementRule
```

Assign a role to an auth rule.

```cypher
REVOKE ROLE reader FROM AUTH RULE temporary_reader
```

Revoke a role from an auth rule.

```cypher
SHOW AUTH RULES
```

Show all auth rules and return default columns (`name`, `condition`, `enabled`, `roles`) For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW AUTH RULES AS COMMANDS
```

Show auth rules as Cypher commands.

```cypher
RENAME AUTH RULE managementRule IF EXISTS TO managementRuleNew
```

Rename an auth rule.

```cypher
ALTER AUTH RULE ruleset_countries SET CONDITION any(country IN abac.oidc.user_attribute('citizenshipCountries')
WHERE country IN ['c1', 'c5', 'c6'])
```

Modify the condition of an auth rule (this example adds `c6` to the list of allowed countries).

```cypher
ALTER AUTH RULE ruleset_countries SET ENABLED false
```

Disable an auth rule.

```cypher
DROP AUTH RULE ruleset_countries IF EXISTS
```

Drop an auth rule.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show_privileges)[SHOW Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-privileges/#access-control-list-privileges)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
SHOW PRIVILEGES
```

Show all privileges in the system and return default columns (`access`, `action`, `resource`, `graph`, `segment`, `role`, and `immutable`). For more information about specifying return columns and filtering, see the general [`SHOW`](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_show) section.

```cypher
SHOW PRIVILEGES AS COMMANDS
```

Show all privileges in the system as Cypher commands, for example `` GRANT ACCESS ON DATABASE * TO `admin` ``. Returns only the default output (`command`).

```cypher
SHOW USER PRIVILEGES
```

Show all privileges of the currently logged-in user, and the roles that they are assigned to. Outputs returned are: `access`, `action`, `resource`, `graph`, `segment`, `role`, `immutable`, and `user`.

```cypher
SHOW USER PRIVILEGES AS COMMANDS
```

Show all privileges of the currently logged-in user, and the roles that they are assigned to as Cypher commands, for example `GRANT ACCESS ON DATABASE * TO $role`. Returns only the default output (`command`).

```cypher
SHOW USER user_name PRIVILEGES
```

Show all privileges assigned to each of the specified users (multiple users can be specified separated by commas `n1, n2, n3`), and the roles that they are assigned to. Outputs returned are: `access`, `action`, `resource`, `graph`, `segment`, `role`, `immutable`, and `user`.

```cypher
SHOW USER user_name PRIVILEGES AS COMMANDS YIELD *
```

Show all privileges assigned to each of the specified users (multiple users can be specified separated by commas `n1, n2, n3`), as generic Cypher commands, for example `GRANT ACCESS ON DATABASE * TO $role`. Outputs returned are: `command` and `immutable`.

```cypher
SHOW ROLE role_name PRIVILEGES
```

Show all privileges assigned to each of the specified roles (multiple roles can be specified separated by commas `r1, r2, r3`). Outputs returned are: `access`, `action`, `resource`, `graph`, `segment`, `role`, and `immutable`.

```cypher
SHOW ROLE role_name PRIVILEGES AS COMMANDS
```

Show all privileges assigned to each of the specified roles (multiple roles can be specified separated by commas `r1, r2, r3`) as Cypher commands, for example `` GRANT ACCESS ON DATABASE * TO `admin` ``. Returns only the default output (`command`).

```cypher
SHOW SUPPORTED PRIVILEGES
```

Show all privileges that are possible to grant or deny on a server. Outputs returned are: `action`, `qualifier`, `target`, `scope`, and `description`.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_immutable_privileges)[IMMUTABLE Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/privileges-immutable/)

Enterprise Edition

```cypher
GRANT IMMUTABLE TRAVERSE
ON GRAPH * TO role_name
```

Grant immutable `TRAVERSE` privilege on all graphs to the specified role.

```cypher
DENY IMMUTABLE START
ON DATABASE * TO role_name
```

Deny immutable `START` privilege to start all databases to the specified role.

```cypher
REVOKE IMMUTABLE CREATE ROLE
ON DBMS FROM role_name
```

Revoke immutable `CREATE ROLE` privilege from the specified role. When immutable is specified in conjunction with a `REVOKE` command, it will act as a filter and only remove the matching immutable privileges.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_load_privileges)[Load Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/load-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT LOAD
ON ALL DATA
TO role_name
```

Grant `LOAD` privilege on `ALL DATA` to allow loading all data to the specified role.

```cypher
DENY LOAD
ON CIDR "127.0.0.1/32"
TO role_name
```

Deny `LOAD` privilege on CIDR range `127.0.0.1/32` to disallow loading data from sources in that range to the specified role.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_graph)ON GRAPH

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_graph_read_privileges)[ON GRAPH Read Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/privileges-reads/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT TRAVERSE
ON GRAPH * NODE * TO role_name
```

Grant `TRAVERSE` privilege on all graphs and all nodes to the specified role.

-   `GRANT` – gives privileges to roles.

-   `DENY` – denies privileges to roles.


```cypher
REVOKE GRANT TRAVERSE
ON GRAPH * NODE * FROM role_name
```

To remove a granted or denied privilege, prepend the privilege query with `REVOKE` and replace the `TO` with `FROM`.

```cypher
GRANT TRAVERSE
ON GRAPH * RELATIONSHIP * TO role_name
```

Grant `TRAVERSE` privilege on all graphs and all relationships to the specified role.

```cypher
DENY READ {prop}
ON GRAPH `database-name` RELATIONSHIP rel_type TO role_name
```

Deny `READ` privilege on a specified property, on all relationships with a specified type in a specified graph, to the specified role.

```cypher
REVOKE READ {prop}
ON GRAPH `database-name` FROM role_name
```

Revoke `READ` privilege on a specified property in a specified graph from the specified role.

```cypher
GRANT MATCH {*}
ON HOME GRAPH ELEMENTS label_or_type TO role_name
```

Grant `MATCH` privilege on all nodes and relationships with the specified label/type, on the home graph, to the specified role. This is semantically the same as having both `TRAVERSE` privilege and `READ {*}` privilege.

```cypher
GRANT READ {*}
ON GRAPH *
FOR (n) WHERE n.secret = false
TO role_name
```

Grant `READ` privilege on all graphs and all nodes with a `secret` property set to `false` to the specified role.

```cypher
DENY TRAVERSE
ON GRAPH *
FOR (n:label) WHERE n.secret <> false
TO role_name
```

Deny `TRAVERSE` privilege on all graphs and all nodes with the specified label and with a `secret` property not set to `false` to the specified role.

```cypher
REVOKE MATCH {*}
ON GRAPH *
FOR (n:foo_label|bar_label) WHERE n.secret IS NULL
FROM role_name
```

Revoke `MATCH` privilege on all graphs and all nodes with either `foo_label` or `bar_label` and with a `secret` property that is `null` from the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_graph_write_privileges)[ON GRAPH Write Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/privileges-writes/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ALL GRAPH PRIVILEGES
ON GRAPH `database-name` TO role_name
```

Grant `ALL GRAPH PRIVILEGES` privilege on a specified graph to the specified role.

```cypher
GRANT ALL ON GRAPH `database-name` TO role_name
```

Short form for grant `ALL GRAPH PRIVILEGES` privilege.

-   `GRANT` – gives privileges to roles.

-   `DENY` – denies privileges to roles.


To remove a granted or denied privilege, prepend the privilege query with `REVOKE` and replace the `TO` with `FROM`; (``REVOKE GRANT ALL ON GRAPH `database-name`` FROM role\_name\`).

```cypher
DENY CREATE
ON GRAPH * NODES node_label TO role_name
```

Deny `CREATE` privilege on all nodes with a specified label in all graphs to the specified role.

```cypher
REVOKE DELETE
ON GRAPH `database-name` FROM role_name
```

Revoke `DELETE` privilege on all nodes and relationships in a specified graph from the specified role.

```cypher
GRANT SET LABEL node_label
ON GRAPH * TO role_name
```

Grant `SET LABEL` privilege for the specified label on all graphs to the specified role.

```cypher
DENY REMOVE LABEL *
ON GRAPH `database-name` TO role_name
```

Deny `REMOVE LABEL` privilege for all labels on a specified graph to the specified role.

```cypher
GRANT SET PROPERTY {prop_name}
ON GRAPH `database-name` RELATIONSHIPS rel_type TO role_name
```

Grant `SET PROPERTY` privilege on a specified property, on all relationships with a specified type in a specified graph, to the specified role.

```cypher
GRANT MERGE {*}
ON GRAPH * NODES node_label TO role_name
```

Grant `MERGE` privilege on all properties, on all nodes with a specified label in all graphs, to the specified role.

```cypher
REVOKE WRITE
ON GRAPH * FROM role_name
```

Revoke `WRITE` privilege on all graphs from the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_graph_property_access_privileges)[ON GRAPH property access privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/property-based-access-control/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT READ { address } ON GRAPH *
    FOR (n:Email|Website) WHERE n.domain = 'exampledomain.com'
    TO regularUsers
```

Grant `READ` on a specific property for nodes matching a label and property condition.

```cypher
GRANT READ { address } ON GRAPH *
    FOR (:Email|Website {domain: 'exampledomain.com'})
    TO regularUsers
```

Equivalent inline pattern syntax. The `{property: value}` shorthand can be used instead of a `WHERE` clause.

```cypher
DENY MATCH {*} ON GRAPH *
    FOR (n) WHERE n.classification <> 'UNCLASSIFIED'
    TO regularUsers
```

Deny `READ` and `TRAVERSE` on all nodes where a property does not match a given value.

```cypher
GRANT READ {*} ON GRAPH *
    FOR (n) WHERE n.securityLevel > 3
    TO regularUsers
```

Grant `READ` on all properties for nodes matching a numeric comparison. Supported operators: `=`, `<>`, `>`, `>=`, `<`, `<=`.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database)ON DATABASE

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database_privileges)[ON DATABASE Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/database-administration/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ALL DATABASE PRIVILEGES
ON DATABASE * TO role_name
```

Grant `ALL DATABASE PRIVILEGES` privilege for all databases to the specified role.

-   Allows access (`GRANT ACCESS`).

-   Index management (`GRANT INDEX MANAGEMENT`).

-   Constraint management (`GRANT CONSTRAINT MANAGEMENT`).

-   Name management (`GRANT NAME MANAGEMENT`).


Note that the privileges for starting and stopping all databases, and transaction management, are not included.

```cypher
GRANT ALL ON DATABASE * TO role_name
```

Short form for grant `ALL DATABASE PRIVILEGES` privilege.

-   `GRANT` – gives privileges to roles.

-   `DENY` – denies privileges to roles.


To remove a granted or denied privilege, prepend the privilege query with `REVOKE` and replace the `TO` with `FROM`; (`REVOKE GRANT ALL ON DATABASE * FROM role_name`).

```cypher
REVOKE ACCESS
ON HOME DATABASE FROM role_name
```

Revoke `ACCESS` privilege to access and run queries against the home database from the specified role.

```cypher
GRANT START
ON DATABASE * TO role_name
```

Grant `START` privilege to start all databases to the specified role.

```cypher
DENY STOP
ON HOME DATABASE TO role_name
```

Deny `STOP` privilege to stop the home database to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database_index_management_privileges)[ON DATABASE - INDEX MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/database-administration/#access-control-database-administration-index)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT INDEX MANAGEMENT
ON DATABASE * TO role_name
```

Grant `INDEX MANAGEMENT` privilege to create, drop, and list indexes for all database to the specified role.

-   Allow creating an index - (`GRANT CREATE INDEX`).

-   Allow removing an index - (`GRANT DROP INDEX`).

-   Allow listing an index - (`GRANT SHOW INDEX`).


```cypher
GRANT CREATE INDEX
ON DATABASE `database-name` TO role_name
```

Grant `CREATE INDEX` privilege to create indexes on a specified database to the specified role.

```cypher
GRANT DROP INDEX
ON DATABASE `database-name` TO role_name
```

Grant `DROP INDEX` privilege to drop indexes on a specified database to the specified role.

```cypher
GRANT SHOW INDEX
ON DATABASE * TO role_name
```

Grant `SHOW INDEX` privilege to list indexes on all databases to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database_constraint_management_privileges)[ON DATABASE - CONSTRAINT MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/database-administration/#access-control-database-administration-constraints)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT CONSTRAINT MANAGEMENT
ON DATABASE * TO role_name
```

Grant `CONSTRAINT MANAGEMENT` privilege to create, drop, and list constraints for all database to the specified role.

-   Allow creating a constraint - (`GRANT CREATE CONSTRAINT`).

-   Allow removing a constraint - (`GRANT DROP CONSTRAINT`).

-   Allow listing a constraint - (`GRANT SHOW CONSTRAINT`).


```cypher
GRANT CREATE CONSTRAINT
ON DATABASE * TO role_name
```

Grant `CREATE CONSTRAINT` privilege to create constraints on all databases to the specified role.

```cypher
GRANT DROP CONSTRAINT
ON DATABASE * TO role_name
```

Grant `DROP CONSTRAINT` privilege to create constraints on all databases to the specified role.

```cypher
GRANT SHOW CONSTRAINT
ON DATABASE `database-name` TO role_name
```

Grant `SHOW CONSTRAINT` privilege to list constraints on a specified database to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database_name_management_privileges)[ON DATABASE - NAME MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/database-administration/#access-control-database-administration-tokens)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT NAME MANAGEMENT
ON DATABASE * TO role_name
```

Grant `NAME MANAGEMENT` privilege to create new labels, new relationship types, and new property names for all databases to the specified role.

-   Allow creating a new label - (`GRANT CREATE NEW LABEL`).

-   Allow creating a new relationship type - (`GRANT CREATE NEW TYPE`).

-   Allow creating a new property name - (`GRANT CREATE NEW NAME`).


```cypher
GRANT CREATE NEW LABEL
ON DATABASE * TO role_name
```

Grant `CREATE NEW LABEL` privilege to create new labels on all databases to the specified role.

```cypher
DENY CREATE NEW TYPE
ON DATABASE * TO role_name
```

Deny `CREATE NEW TYPE` privilege to create new relationship types on all databases to the specified role.

```cypher
GRANT CREATE NEW NAME
ON DATABASE * TO role_name
```

Grant `CREATE NEW NAME` privilege to create new property names on all databases to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_database_transaction_management_privileges)[ON DATABASE - TRANSACTION MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/database-administration/#access-control-database-administration-transaction)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT TRANSACTION MANAGEMENT (*)
ON DATABASE * TO role_name
```

Grant `TRANSACTION MANAGEMENT` privilege to show and terminate transactions on all users, for all databases, to the specified role.

-   Allow listing transactions - (`GRANT SHOW TRANSACTION`).

-   Allow terminate transactions - (`GRANT TERMINATE TRANSACTION`).


```cypher
GRANT SHOW TRANSACTION (*)
ON DATABASE * TO role_name
```

Grant `SHOW TRANSACTION` privilege to list transactions on all users on all databases to the specified role.

```cypher
GRANT SHOW TRANSACTION (user_name1, user_name2)
ON HOME DATABASE TO role_name1, role_name2
```

Grant `SHOW TRANSACTION` privilege to list transactions by the specified users on home database to the specified roles.

```cypher
GRANT TERMINATE TRANSACTION (*)
ON DATABASE * TO role_name
```

Grant `TERMINATE TRANSACTION` privilege to terminate transactions on all users on all databases to the specified role.

## [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms)ON DBMS

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_privileges)[ON DBMS Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ALL DBMS PRIVILEGES
ON DBMS TO role_name
```

Grant `ALL DBMS PRIVILEGES` privilege to perform management for roles, users, databases, aliases, and privileges to the specified role. Also privileges to execute procedures and user defined functions are granted.

-   Allow controlling roles - (`GRANT ROLE MANAGEMENT`).

-   Allow controlling users - (`GRANT USER MANAGEMENT`).

-   Allow controlling databases - (`GRANT DATABASE MANAGEMENT`).

-   Allow controlling aliases - (`GRANT ALIAS MANAGEMENT`).

-   Allow controlling privileges - (`GRANT PRIVILEGE MANAGEMENT`).

-   Allow user impersonation - (`GRANT IMPERSONATE (*)`).

-   Allow to execute all procedures with elevated privileges.

-   Allow to execute all user defined functions with elevated privileges.


```cypher
GRANT ALL
ON DBMS TO role_name
```

Short form for grant `ALL DBMS PRIVILEGES` privilege.

-   `GRANT` – gives privileges to roles.

-   `DENY` – denies privileges to roles.


To remove a granted or denied privilege, prepend the privilege query with `REVOKE` and replace the `TO` with `FROM`; (`REVOKE GRANT ALL ON DBMS FROM role_name`).

```cypher
DENY IMPERSONATE (user_name1, user_name2)
ON DBMS TO role_name
```

Deny `IMPERSONATE` privilege to impersonate the specified users (`user_name1` and `user_name2`) to the specified role.

```cypher
REVOKE IMPERSONATE (*)
ON DBMS FROM role_name
```

Revoke `IMPERSONATE` privilege to impersonate all users from the specified role.

```cypher
GRANT EXECUTE PROCEDURE *
ON DBMS TO role_name
```

Enables the specified role to execute all procedures.

```cypher
GRANT EXECUTE BOOSTED PROCEDURE *
ON DBMS TO role_name
```

Enables the specified role to use elevated privileges when executing all procedures.

```cypher
GRANT EXECUTE ADMIN PROCEDURES
ON DBMS TO role_name
```

Enables the specified role to execute procedures annotated with `@Admin`. The procedures are executed with elevated privileges.

```cypher
GRANT EXECUTE FUNCTIONS *
ON DBMS TO role_name
```

Enables the specified role to execute all user defined functions.

```cypher
GRANT EXECUTE BOOSTED FUNCTIONS *
ON DBMS TO role_name
```

Enables the specified role to use elevated privileges when executing all user defined functions.

```cypher
GRANT SHOW SETTINGS *
ON DBMS TO role_name
```

Enables the specified role to view all configuration settings.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_role_management_privileges)[ON DBMS - ROLE MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-role-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ROLE MANAGEMENT
ON DBMS TO role_name
```

Grant `ROLE MANAGEMENT` privilege to manage roles to the specified role.

-   Allow creating roles - (`GRANT CREATE ROLE`).

-   Allow renaming roles - (`GRANT RENAME ROLE`).

-   Allow deleting roles - (`GRANT DROP ROLE`).

-   Allow assigning (`GRANT`) roles to a user - (`GRANT ASSIGN ROLE`).

-   Allow removing (`REVOKE`) roles from a user - (`GRANT REMOVE ROLE`).

-   Allow listing roles - (`GRANT SHOW ROLE`).


```cypher
GRANT CREATE ROLE
ON DBMS TO role_name
```

Grant `CREATE ROLE` privilege to create roles to the specified role.

```cypher
GRANT RENAME ROLE
ON DBMS TO role_name
```

Grant `RENAME ROLE` privilege to rename roles to the specified role.

```cypher
DENY DROP ROLE
ON DBMS TO role_name
```

Deny `DROP ROLE` privilege to delete roles to the specified role.

```cypher
GRANT ASSIGN ROLE
ON DBMS TO role_name
```

Grant `ASSIGN ROLE` privilege to assign roles to users to the specified role.

```cypher
DENY REMOVE ROLE
ON DBMS TO role_name
```

Deny `REMOVE ROLE` privilege to remove roles from users to the specified role.

```cypher
GRANT SHOW ROLE
ON DBMS TO role_name
```

Grant `SHOW ROLE` privilege to list roles to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_user_management_privileges)[ON DBMS - USER MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-user-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT USER MANAGEMENT
ON DBMS TO role_name
```

Grant `USER MANAGEMENT` privilege to manage users to the specified role.

-   Allow creating users - (`GRANT CREATE USER`).

-   Allow renaming users - (`GRANT RENAME USER`).

-   Allow modifying a user - (`GRANT ALTER USER`).

-   Allow deleting users - (`GRANT DROP USER`).

-   Allow listing users - (`GRANT SHOW USER`).


```cypher
DENY CREATE USER
ON DBMS TO role_name
```

Deny `CREATE USER` privilege to create users to the specified role.

```cypher
GRANT RENAME USER
ON DBMS TO role_name
```

Grant `RENAME USER` privilege to rename users to the specified role.

```cypher
GRANT ALTER USER
ON DBMS TO role_name
```

Grant `ALTER USER` privilege to alter users to the specified role.

-   Allow changing a user’s password - (`GRANT SET PASSWORD`).

-   Allow adding or removing a user’s auth providers - (`GRANT SET AUTH`).

-   Allow changing a user’s home database - (`GRANT SET USER HOME DATABASE`).

-   Allow changing a user’s status - (`GRANT USER STATUS`).


```cypher
DENY SET PASSWORD
ON DBMS TO role_name
```

Deny `SET PASSWORD` privilege to alter a user password to the specified role.

```cypher
GRANT SET AUTH
ON DBMS TO role_name
```

Grant `SET AUTH` privilege to add/remove auth providers to the specified role.

```cypher
GRANT SET USER HOME DATABASE
ON DBMS TO role_name
```

Grant `SET USER HOME DATABASE` privilege to alter the home database of users to the specified role.

```cypher
GRANT SET USER STATUS
ON DBMS TO role_name
```

Grant `SET USER STATUS` privilege to alter user account status to the specified role.

```cypher
GRANT DROP USER
ON DBMS TO role_name
```

Grant `DROP USER` privilege to delete users to the specified role.

```cypher
DENY SHOW USER
ON DBMS TO role_name
```

Deny `SHOW USER` privilege to list users to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_auth_rule_management_privileges)[ON DBMS - AUTH RULE MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-auth-rule-management-privileges/#grant-create-auth-rule-privilege)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT AUTH RULE MANAGEMENT ON DBMS TO authRuleManager
```

Umbrella privilege equivalent to granting all five auth rule privileges:

-   `CREATE AUTH RULE`: create auth rules

-   `SHOW AUTH RULE`: list auth rules

-   `ALTER AUTH RULE`: modify auth rules

-   `RENAME AUTH RULE`: rename auth rules

-   `DROP AUTH RULE`: drop auth rules


```cypher
GRANT CREATE AUTH RULE ON DBMS TO authRuleCreator
```

Grant the privilege to create auth rules.

```cypher
DENY SHOW AUTH RULE ON DBMS TO authRuleViewer
```

Deny the privilege to list auth rules.

```cypher
GRANT ALTER AUTH RULE ON DBMS TO authRuleModifier
```

Grant the privilege to modify auth rules.

```cypher
REVOKE RENAME AUTH RULE ON DBMS FROM authRuleRenamer
```

Revoke the privilege to rename auth rules.

```cypher
DENY DROP AUTH RULE ON DBMS TO authRuleDropper
```

Deny the privilege to drop auth rules.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_database_management_privileges)[ON DBMS - DATABASE MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-database-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT DATABASE MANAGEMENT
ON DBMS TO role_name
```

Grant `DATABASE MANAGEMENT` privilege to manage databases to the specified role.

-   Allow creating standard databases - (`GRANT CREATE DATABASE`).

-   Allow deleting standard databases - (`GRANT DROP DATABASE`).

-   Allow modifying standard databases - (`GRANT ALTER DATABASE`).

-   Allow managing composite databases - (`GRANT COMPOSITE DATABASE MANAGEMENT`).


```cypher
GRANT CREATE DATABASE
ON DBMS TO role_name
```

Grant `CREATE DATABASE` privilege to create standard databases to the specified role.

```cypher
GRANT DROP DATABASE
ON DBMS TO role_name
```

Grant `DROP DATABASE` privilege to delete standard databases to the specified role.

```cypher
GRANT ALTER DATABASE
ON DBMS TO role_name
```

Grant `ALTER DATABASE` privilege to alter standard databases the specified role.

-   Allow modifying access mode for standard databases - (`GRANT SET DATABASE ACCESS`).

-   Allow modifying topology settings for standard databases.


```cypher
GRANT SET DATABASE ACCESS
ON DBMS TO role_name
```

Grant `SET DATABASE ACCESS` privilege to set database access mode for standard databases to the specified role.

```cypher
GRANT COMPOSITE DATABASE MANAGEMENT
ON DBMS TO role_name
```

Grant all privileges to manage composite databases to the specified role.

-   Allow creating composite databases - (`CREATE COMPOSITE DATABASE`).

-   Allow deleting composite databases - (`DROP COMPOSITE DATABASE`).


```cypher
DENY CREATE COMPOSITE DATABASE
ON DBMS TO role_name
```

Denies the specified role the privilege to create composite databases.

```cypher
REVOKE DROP COMPOSITE DATABASE
ON DBMS FROM role_name
```

Revokes the granted and denied privileges to delete composite databases from the specified role.

```cypher
GRANT SERVER MANAGEMENT
ON DBMS TO role_name
```

Enables the specified role to show, enable, rename, alter, reallocate, deallocate, and drop servers.

```cypher
DENY SHOW SERVERS
ON DBMS TO role_name
```

Denies the specified role the privilege to show information about the serves.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_alias_management_privileges)[ON DBMS - ALIAS MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-alias-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ALIAS MANAGEMENT
ON DBMS TO role_name
```

Grant `ALIAS MANAGEMENT` privilege to manage aliases to the specified role.

-   Allow creating aliases - (`GRANT CREATE ALIAS`).

-   Allow deleting aliases - (`GRANT DROP ALIAS`).

-   Allow modifying aliases - (`GRANT ALTER ALIAS`).

-   Allow listing aliases - (`GRANT SHOW ALIAS`).


```cypher
GRANT CREATE ALIAS
ON DBMS TO role_name
```

Grant `CREATE ALIAS` privilege to create aliases to the specified role.

```cypher
GRANT DROP ALIAS
ON DBMS TO role_name
```

Grant `DROP ALIAS` privilege to delete aliases to the specified role.

```cypher
GRANT ALTER ALIAS
ON DBMS TO role_name
```

Grant `ALTER ALIAS` privilege to alter aliases to the specified role.

```cypher
GRANT SHOW ALIAS
ON DBMS TO role_name
```

Grant `SHOW ALIAS` privilege to list aliases to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_role_management_privileges_2)[ON DBMS - ROLE MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-role-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT ROLE MANAGEMENT
ON DBMS TO role_name
```

Grant `ROLE MANAGEMENT` privilege to manage roles to the specified role.

-   Allow creating roles - (`GRANT CREATE ROLE`).

-   Allow renaming roles - (`GRANT RENAME ROLE`).

-   Allow deleting roles - (`GRANT DROP ROLE`).

-   Allow assigning (`GRANT`) roles to a user - (`GRANT ASSIGN ROLE`).

-   Allow removing (`REVOKE`) roles from a user - (`GRANT REMOVE ROLE`).

-   Allow listing roles - (`GRANT SHOW ROLE`).


```cypher
GRANT CREATE ROLE
ON DBMS TO role_name
```

Grant `CREATE ROLE` privilege to create roles to the specified role.

```cypher
GRANT RENAME ROLE
ON DBMS TO role_name
```

Grant `RENAME ROLE` privilege to rename roles to the specified role.

```cypher
DENY DROP ROLE
ON DBMS TO role_name
```

Deny `DROP ROLE` privilege to delete roles to the specified role.

```cypher
GRANT ASSIGN ROLE
ON DBMS TO role_name
```

Grant `ASSIGN ROLE` privilege to assign roles to users to the specified role.

```cypher
DENY REMOVE ROLE
ON DBMS TO role_name
```

Deny `REMOVE ROLE` privilege to remove roles from users to the specified role.

```cypher
GRANT SHOW ROLE
ON DBMS TO role_name
```

Grant `SHOW ROLE` privilege to list roles to the specified role.

### [](https://neo4j.com/docs/cypher-manual/current/cheat-sheet/#_on_dbms_privilege_management_privileges)[ON DBMS - PRIVILEGE MANAGEMENT Privileges](https://neo4j.com/docs/operations-manual/current/authentication-authorization/dbms-administration/dbms-privilege-management-privileges/)

AuraDB Business CriticalAuraDB Virtual Dedicated CloudEnterprise Edition

```cypher
GRANT PRIVILEGE MANAGEMENT
ON DBMS TO role_name
```

Grant `PRIVILEGE MANAGEMENT` privilege to manage privileges for the Neo4j DBMS to the specified role.

-   Allow assigning (`GRANT|DENY`) privileges for a role - (`GRANT ASSIGN PRIVILEGE`).

-   Allow removing (`REVOKE`) privileges for a role - (`GRANT REMOVE PRIVILEGE`).

-   Allow listing privileges - (`GRANT SHOW PRIVILEGE`).


```cypher
GRANT ASSIGN PRIVILEGE
ON DBMS TO role_name
```

Grant `ASSIGN PRIVILEGE` privilege, allows the specified role to assign privileges for roles.

```cypher
GRANT REMOVE PRIVILEGE
ON DBMS TO role_name
```

Grant `REMOVE PRIVILEGE` privilege, allows the specified role to remove privileges for roles.

```cypher
GRANT SHOW PRIVILEGE
ON DBMS TO role_name
```

Grant `SHOW PRIVILEGE` privilege to list privileges to the specified role.
