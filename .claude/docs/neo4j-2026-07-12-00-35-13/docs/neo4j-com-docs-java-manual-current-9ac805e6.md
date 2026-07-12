---
title: "Build applications with Neo4j and Java"
source_url: "https://neo4j.com/docs/java-manual/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.992Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/docs-drivers/issues/new/?title=Docs%20Feedback%20java-manual/modules/ROOT/pages/index.adoc%20\(ref:%206.x\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Build applications with Neo4j and Java

The Neo4j Java driver is the official library to interact with a Neo4j instance through a Java application.

At the hearth of Neo4j lies [Cypher](https://neo4j.com/docs/java-manual/current/#Cypher), the query language to interact with a Neo4j database. Although this guide does not *require* you to be a seasoned Cypher querier, it’s easier to focus on the Java-specific bits if you know some Cypher already. You will also get a *gentle* introduction to Cypher in these pages, but check out [Getting started → Cypher](https://neo4j.com/docs/getting-started/cypher/) for a more detailed walkthrough of graph databases modelling and querying if this is your first approach.

## [](https://neo4j.com/docs/java-manual/current/#install)Install

Add the Neo4j Java driver to the list of dependencies in the `pom.xml` of your Maven project:

```xml
<dependency>
    <groupId>org.neo4j.driver</groupId>
    <artifactId>neo4j-java-driver</artifactId>
    <version>6.1.0</version>
</dependency>
```

[More info on installing the driver](https://neo4j.com/docs/java-manual/current/install/)

## [](https://neo4j.com/docs/java-manual/current/#connect)Connect to the database

Connect to a database by creating a `Driver` object and providing a URL and an authentication token. Once you have a `Driver` instance, use the `.verifyConnectivity()` method to ensure that a working connection can be established.

```java
package demo;

import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.GraphDatabase;

public class App {

    public static void main(String... args) {

        // URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
        final String dbUri = "<database-uri>";
        final String dbUser = "<username>";
        final String dbPassword = "<password>";

        try (var driver = GraphDatabase.driver(dbUri, AuthTokens.basic(dbUser, dbPassword))) {
            driver.verifyConnectivity();
            System.out.println("Connection established.");
        }
    }
}
```

[More info on connecting to a database](https://neo4j.com/docs/java-manual/current/connect/)

## [](https://neo4j.com/docs/java-manual/current/#create-graph)Create an example graph

Run a Cypher query with the method `Driver.executableQuery()`. Do not hardcode or concatenate parameters: use placeholders and specify the parameters as a map through the `.withParameters()` method.

Create two `Person` nodes and a `KNOWS` relationship between them

```java
// import java.util.Map;
// import java.util.concurrent.TimeUnit;
// import org.neo4j.driver.QueryConfig;

var result = driver.executableQuery("""
    CREATE (a:Person {name: $name})
    CREATE (b:Person {name: $friendName})
    CREATE (a)-[:KNOWS]->(b)
    """)
    .withParameters(Map.of("name", "Alice", "friendName", "David"))
    .withConfig(QueryConfig.builder().withDatabase("<database-name>").build())
    .execute();

// Summary information
var summary = result.summary();
System.out.printf("Created %d records in %d ms.%n",
    summary.counters().nodesCreated(),
    summary.resultAvailableAfter(TimeUnit.MILLISECONDS));
```

[More info on querying the database](https://neo4j.com/docs/java-manual/current/query-simple/)

## [](https://neo4j.com/docs/java-manual/current/#query-graph)Query a graph

To retrieve information from the database, use the Cypher clause `MATCH`:

Retrieve all `Person` nodes who know other persons

```java
// import java.util.concurrent.TimeUnit;
// import org.neo4j.driver.QueryConfig;

var result = driver.executableQuery("""
    MATCH (p:Person)-[:KNOWS]->(:Person)
    RETURN p.name AS name
    """)
    .withConfig(QueryConfig.builder().withDatabase("<database-name>").build())
    .execute();

// Loop through results and do something with them
var records = result.records();
records.forEach(r -> {
    System.out.println(r);  // or r.get("name").asString()
});

// Summary information
var summary = result.summary();
System.out.printf("The query %s returned %d records in %d ms.%n",
    summary.query(), records.size(),
    summary.resultAvailableAfter(TimeUnit.MILLISECONDS));
```

[More info on querying the database](https://neo4j.com/docs/java-manual/current/query-simple/)

## [](https://neo4j.com/docs/java-manual/current/#close)Close connections and sessions

Unless you created them with `try-with-resources` statements, call the `.close()` method on all `Driver` and `Session` instances to release any resources still held by them.

```java
session.close();
driver.close();
```

## Glossary

LTS

A *Long Term Support* release is one guaranteed to be supported for a number of years. Neo4j 4.4 and 5.26 are LTS versions.

Aura

[Aura](https://neo4j.com/product/auradb/) is Neo4j’s fully managed cloud service. It comes with both free and paid plans.

Cypher

[Cypher](https://neo4j.com/docs/cypher-manual/current/introduction/cypher-overview/) is Neo4j’s graph query language that lets you retrieve data from the database. It is like SQL, but for graphs.

APOC

[Awesome Procedures On Cypher (APOC)](https://neo4j.com/docs/apoc/current/) is a library of (many) functions that can not be easily expressed in Cypher itself.

Bolt

[Bolt](https://neo4j.com/docs/bolt/current/) is the protocol used for interaction between Neo4j instances and drivers. It listens on port 7687 by default.

ACID

Atomicity, Consistency, Isolation, Durability (ACID) are properties guaranteeing that database transactions are processed reliably. An ACID-compliant DBMS ensures that the data in the database remains accurate and consistent despite failures.

eventual consistency

A database is eventually consistent if it provides the guarantee that all cluster members will, *at some point in time*, store the latest version of the data.

causal consistency

A database is causally consistent if read and write queries are seen by every member of the cluster in the same order. This is stronger than *eventual consistency*.

NULL

The null marker is not a type but a placeholder for absence of value. For more information, see [Cypher → Working with `null`](https://neo4j.com/docs/cypher-manual/current/values-and-types/working-with-null/).

transaction

A transaction is a unit of work that is either *committed* in its entirety or *rolled back* on failure. An example is a bank transfer: it involves multiple steps, but they must *all* succeed or be reverted, to avoid money being subtracted from one account but not added to the other.

backpressure

Backpressure is a force opposing the flow of data. It ensures that the client is not being overwhelmed by data faster than it can handle.

bookmark

A *bookmark* is a token representing some state of the database. By passing one or multiple bookmarks along with a query, the server will make sure that the query does not get executed before the represented state(s) have been established.

transaction function

A transaction function is a callback executed by an `executeRead` or `executeWrite` call. The driver automatically re-executes the callback in case of server failure.

Driver

A [`Driver`](https://neo4j.com/docs/api/java-driver/current/org.neo4j.driver/org/neo4j/driver/Driver.html) object holds the details required to establish connections with a Neo4j database.
