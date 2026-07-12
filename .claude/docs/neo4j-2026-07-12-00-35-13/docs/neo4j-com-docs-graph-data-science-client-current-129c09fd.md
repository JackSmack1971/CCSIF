---
title: "Neo4j Graph Data Science Python Client"
source_url: "https://neo4j.com/docs/graph-data-science-client/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:11.663Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/graph-data-science-client/issues/new/?title=Docs%20Feedback%20doc/modules/ROOT/pages/index.adoc%20\(ref:%201.22\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Neo4j Graph Data Science Python Client

To help users of [Neo4j Graph Data Science](https://neo4j.com/docs/graph-data-science/current/) who work with Python as their primary language and environment, we offer the official Graph Data Science (GDS) Python Client package called `graphdatascience`. It enables users to write pure Python code to project graphs, run algorithms, use machine learning pipelines, and train machine learning models with GDS. To avoid naming confusion with the server-side GDS library, we will here refer to the Neo4j Graph Data Science client as the *Python client*.

The Python client API is designed to mimic the GDS Cypher procedure API in Python code. It wraps and abstracts the necessary operations of the [Neo4j Python driver](https://neo4j.com/docs/python-manual/current/) to offer a simpler surface. For a high level explanation of how the Cypher API maps to the Python client API please see [Mapping between Cypher and Python](https://neo4j.com/docs/graph-data-science-client/current/getting-started/#getting-started-mapping).

Additionally, the client-specific graph, model, and pipeline objects offer convenient functions that heavily reduce the need to use Cypher to access and operate these GDS resources.

The source code of the GDS Python client is available at [GitHub](https://github.com/neo4j/graph-data-science-client). If you have a suggestion on how we can improve the library or want to report a problem, you can create a [new issue](https://github.com/neo4j/graph-data-science-client/issues/new).

© 2025

License: [Creative Commons 4.0](https://neo4j.com/docs/license/)
