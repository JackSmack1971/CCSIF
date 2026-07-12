---
title: "Introduction"
source_url: "https://neo4j.com/docs/status-codes/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:11.014Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/docs-status-codes/issues/new/?title=Docs%20Feedback%20modules/ROOT/pages/index.adoc%20\(ref:%20main\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Introduction

This manual covers all status codes for errors and notifications that a Neo4j server may return to indicate the result of a Cypher request.

Starting from 5.23 for notifications and 5.25 for errors, Neo4j supports the GQL standard.
GQL is the new [ISO](https://www.iso.org/home.html) International Standard query language for graph databases. Cypher®, Neo4j’s query language, supports most mandatory and a substantial portion of the optional GQL features (as defined by the [ISO/IEC 39075:2024(en) - Information technology - Database languages - GQL Standard](https://www.iso.org/standard/76120.html)). For more information, see [Cypher Manual → GQL conformance](https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/).

As part of this GQL compliance, Cypher also includes status codes that a GQL-compliant DBMS returns to indicate the outcome of a request. For more information on the GQL-status object framework for notifications and errors, see [Server notifications](https://neo4j.com/docs/status-codes/current/notifications/) and [Server errors](https://neo4j.com/docs/status-codes/current/errors/).

License: [Creative Commons 4.0](https://neo4j.com/docs/license/)
