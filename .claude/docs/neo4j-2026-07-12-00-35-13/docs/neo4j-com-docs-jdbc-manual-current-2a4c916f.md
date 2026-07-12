---
title: "Neo4j JDBC Driver"
source_url: "https://neo4j.com/docs/jdbc-manual/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:13.047Z"
---
[](https://neo4j.com/docs)

# Neo4j JDBC Driver

© 2023-2025

## [](https://neo4j.com/docs/jdbc-manual/current/#_abstract)Abstract

This is the manual for the official Neo4j JDBC Driver.

This driver is officially supported and endorsed by Neo4j. It is a standalone driver, independent of and **not** built on top of the [common Neo4j Java Driver](https://github.com/neo4j/neo4j-java-driver). While the latter provides a Neo4j-idiomatic way to access Neo4j from Java, the JDBC driver adheres to [JDBC 4.3](https://docs.oracle.com/en/java/javase/17/docs/api/java.sql/java/sql/package-summary.html).

<table><tbody><tr><td class="icon"><i class="fa icon-note" title="Note"></i></td><td class="content">This documentation refers to <strong>this</strong> driver as the <em>Neo4j JDBC Driver</em> and to the idiomatic Neo4j driver as the <em>common Neo4j Java Driver</em>.</td></tr></tbody></table>

## [](https://neo4j.com/docs/jdbc-manual/current/#_introduction)Introduction

JDBC stands for "Java Database Connectivity" and is thus not bound exclusively to relational databases. Nevertheless, JDBC’s terms, definitions, and behavior are highly influenced by SQL and relational databases. As Neo4j is a graph database with quite a different paradigm than relational and a non-standardized behaviour in some areas, there might be some details that don’t map 100% in each place, and we make sure to educate you about these in this documentation.

This documentation focuses on install, use, and configure the Neo4j JDBC Driver, as well as discussing the driver’s design choices. While we do provide runnable examples showing how to use JDBC with Neo4j, this is not a documentation about how to correctly use JDBC as an API.

<table><tbody><tr><td class="icon"><i class="fa icon-note" title="Note"></i></td><td class="content">The Neo4j JDBC Driver requires JDK 17 on the client side and Neo4j 5.5+ on the server side. To use it with a Neo4j cluster, server-side routing must be enabled on the cluster.</td></tr></tbody></table>

### [](https://neo4j.com/docs/jdbc-manual/current/#_features)Features

-   Fully supports the Java module system

-   Adheres to JDBC 4.3

-   Can run any Cypher® statement

-   Implements `DatabaseMetaData` and `ResultSetMetaData` as fully as possible with a nearly schemaless database and general very flexible result sets, allowing for automatic metadata retrieval from ETL and ELT tools

-   Provides an [SPI](https://en.wikipedia.org/wiki/Service_provider_interface) to hook in translators from SQL to Cypher

-   Provides an optional default implementation to translate many SQL statements into semantically similar Cypher statements

-   Supports client-side Cypher-backed views

-   Can be safely used with JDBC connection pools as opposed to the common Neo4j Java Driver or any JDBC driver based on that, as it doesn’t do internal connection pooling and transaction management otherwise than dictated by the JDBC Spec

-   Built-in token based authentication, including reauthentication on token expiration plus an optiona Keycloak based SSO module

-   Built-in JSON based Object mapping


The absence of any connection pooling and transaction management is an advantage of the Neo4j JDBC Driver over the common Neo4j Java Driver. It allows to pick and choose any database connection pooling system such as [HikariCP](https://github.com/brettwooldridge/HikariCP) and transaction management such as [Jakarta Transactions](https://jakarta.ee/specifications/transactions/).

### [](https://neo4j.com/docs/jdbc-manual/current/#_limitations)Limitations

-   The database metadata is retrieved using Neo4j’s schema methods, such as `db.labels`, `db.schema.nodeTypeProperties()`, which may not always be accurate

-   While single label nodes map naturally to table names, nodes with multiple labels don’t

-   There is no reliable way to always determine the datatype for properties on nodes, as it would require reading all of them (which this driver does not do)

-   Some JDBC features are not supported yet (such as the `CallableStatement`); some feature will never be supported

-   The SQL to Cypher translator supports only a limited subset of clauses and SQL constructs that can be equivalently translated to Cypher (See [Supported statements](https://neo4j.com/docs/jdbc-manual/current/sql2cypher/#s2c_supported_statements))

-   There is no "right" way to map `JOIN` statements to relationships, so your mileage may vary


### [](https://neo4j.com/docs/jdbc-manual/current/#_when_to_use_the_neo4j_jdbc_driver)When to use the Neo4j JDBC Driver?

-   Integration with ETL and ELT tools that don’t offer an integration based on the common Neo4j Java driver

-   An easier on-ramp towards Neo4j for people familiar with JDBC, who want to keep using that API, but with Cypher and Neo4j

-   Integration for ecosystems like Jakarta EE whose transaction management directly supports any JDBC-compliant driver

-   Integration with database migration tools such as Flyway


**There is no need to redesign an application that is built on the common Neo4j Java Driver to migrate to this driver.** If your ecosystem already provides a higher-level integration based on the common Neo4j Java Driver, such as [Spring Data Neo4j (SDN)](https://github.com/spring-projects/spring-data-neo4j) for [Spring](https://spring.io/projects/spring-boot/), there is no need to switch to something else. In case of [Quarkus](https://quarkus.io/), the Neo4j JDBC Driver is an option to consider: although we do provide an integration for the [common Neo4j Java Driver](https://github.com/quarkiverse/quarkus-neo4j), this integration does not support Quarkus' transaction systems in contrast to this driver.

As there is little incentive to use this driver with Hibernate ([Neo4j-OGM](https://github.com/neo4j/neo4j-ogm) or SDN are the best alternatives for Neo4j), it might be worth giving [Spring Data JDBC](https://spring.io/projects/spring-data-jdbc/) a try.

### [](https://neo4j.com/docs/jdbc-manual/current/#_differences_with_the_previous_versions_of_this_driver_and_other_jdbc_drivers_for_neo4j)Differences with the previous versions of this driver and other JDBC drivers for Neo4j

Several other JDBC drivers exists for Neo4j, most notably the previous versions 4 and 5 of this driver. Most (if not all) of them wrap the common Neo4j Java Driver and implement the JDBC spec on top of that. This comes with a number of issues:

-   You end up with a *pool of connection pools*, because the common Neo4j Java Driver manages a connection pool, whereas JDBC drivers delegate this task to dedicated pooling solutions.

-   The transaction management of the common Neo4j Java Driver is not aligned with the way JDBC manages transactions.

-   Older versions of the Neo4j JDBC driver shade a few dependencies, such as `Jackson` as well as additional logging frameworks. This takes a toll on the classpath and, in case of logging, it leads to runtime problems.

-   Existing drivers with an SQL-to-Cypher translation layer are "read-only" and don’t support write statements, so they cannot be used for ETL use-cases aiming to ingest data into Neo4j.


<table><tbody><tr><td class="icon"><i class="fa icon-warning" title="Warning"></i></td><td class="content">This driver does not support automatic reshaping or flattening of the result sets, as the previous versions do. If you query for nodes, relationships, paths, or maps, you should use <code>getObject</code> on the result sets and cast them to the appropriate type (you find all of them inside the package <code>org.neo4j.jdbc.values</code>). However, the default SQL-to-Cypher translator will (when connected to a database) figure out what properties nodes have and turn the asterisk (<code>*</code>) into individual columns of nodes and relationships, just like what you would expect when running a <code>SELECT *</code> statement.</td></tr></tbody></table>

For information on upgrade/migration from other drivers to this one, see [Migrating from older versions or other JDBC drivers for Neo4j](https://neo4j.com/docs/jdbc-manual/current/migrating/).
