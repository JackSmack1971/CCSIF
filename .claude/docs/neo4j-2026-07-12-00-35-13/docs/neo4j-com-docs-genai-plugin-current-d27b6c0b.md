---
title: "Introduction"
source_url: "https://neo4j.com/docs/genai/plugin/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.546Z"
---
[](https://neo4j.com/docs/genai)

[Raise an issue](https://github.com/neo4j/docs-genai-plugin/issues/new/?title=Docs%20Feedback%20modules/ROOT/pages/index.adoc%20\(ref:%20cypher-25\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Introduction

Neo4j’s GenAI plugin provides functions and procedures to interact with external AI providers through Cypher, such as for creating vector embeddings and generating text.

<table><tbody><tr><td class="icon"><i class="fa icon-note" title="Note"></i></td><td class="content">To use the plugin’s features, you need an account and API credentials from one of the supported external AI providers: (OpenAI, Azure OpenAI, VertexAI, Amazon Bedrock).</td></tr></tbody></table>

## [](https://neo4j.com/docs/genai/plugin/current/#installation)Installation

**In [Neo4j Aura](https://neo4j.com/product/auradb/)**, the GenAI plugin is enabled by default.

**On self-managed instances**, you install the plugin by moving the `neo4j-genai-plugin-<version>.jar` file from `<NEO4J_HOME>/products` to `<NEO4J_HOME>/plugins`, or, if you are using Docker, by starting the Docker container with the extra parameter `--env NEO4J_PLUGINS='["genai"]'`. For more information, see [Operations Manual → Configure plugins](https://neo4j.com/docs/operations-manual/current/configuration/plugins/).

<table><tbody><tr><td class="icon"><i class="fa icon-important" title="Important"></i></td><td class="content">Most GenAI features are available only in Cypher 25. If your database’s default language is Cypher 5, prepend the query with <code>CYPHER 25</code> to override the default for that query (see <a href="https://neo4j.com/docs/cypher-manual/current/queries/select-version/">Cypher → Select Cypher version</a>).</td></tr></tbody></table>

## [](https://neo4j.com/docs/genai/plugin/current/#setup)Environment setup

The examples in this manual use the [Neo4j movie recommendations](https://github.com/neo4j-graph-examples/recommendations) dataset, mostly focusing on the `plot` and `title` properties of `Movie` nodes. There are 9083 `Movie` nodes with a `plot` and `title` property.

![Example graph connecting person and actor nodes with a movie node via acted in and directed relationships](https://neo4j.com/docs/genai/plugin/current/_images/genai-graph.svg)

To follow the examples in this manual, you need to import a dump file. The file to import depends on the edition/deployment of Neo4j you are using and which [storage format](https://neo4j.com/docs/operations-manual/current/database-internals/store-formats/#store-format-overview) is available:

-   Enterprise Edition or any Aura instance — Import the [dump file](https://github.com/neo4j-graph-examples/recommendations/raw/main/data/recommendations-5.26-block.dump) in block format.

-   Community Edition — Import the [dump file](https://github.com/neo4j-graph-examples/recommendations/raw/main/data/recommendations-5.26.dump) in aligned format.


For instructions on importing dump files, see [Aura → Backup, export, restore, and upload](https://neo4j.com/docs/aura/managing-instances/backup-restore-export/#restore-backup) or [Operations manual → Restore a database dump](https://neo4j.com/docs/operations-manual/current/backup-restore/restore-dump/).
