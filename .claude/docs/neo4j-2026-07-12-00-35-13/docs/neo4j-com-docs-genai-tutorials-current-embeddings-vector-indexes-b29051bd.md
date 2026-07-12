---
title: "Introduction"
source_url: "https://neo4j.com/docs/genai/tutorials/current/embeddings-vector-indexes/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.490Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/docs-genai-tutorials/issues/new/?title=Docs%20Feedback%20modules/embeddings-vector-indexes/pages/index.adoc%20\(ref:%20dev\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Introduction

Humans do great with natural language and struggle with numbers; computers do great with numbers and struggle with natural language. How can we use computers for tasks that require understanding of natural language, then? Given a Neo4j database with movies, how can we query it to know what movies best match your interest, if that is expressed in words? For example, what movies are about `an exploration of italian mafias in america`? What movies relate to `a criminal is changed through love`? What movies are similar to one another?

**Neo4j’s vector indexes allow you to retrieve nodes and relationships that are similar to other nodes and relationships, or that relate to a given text prompt.** Vector indexes don’t work on texts expressed in natural language though: they need the texts to be turned into lists of numbers. These lists are called *embeddings*, and they attempt to encode the meaning of a text numerically. With a vector index, the database can quickly match graph entities based on their embeddings.

For example, the picture below shows the title and plot for the movie `Despicable Me` and its corresponding embedding.

![despicable embedding](https://neo4j.com/docs/genai/tutorials/current/embeddings-vector-indexes/_images/despicable-embedding.png)

This tutorial uses the [recommendations dataset](https://github.com/neo4j-graph-examples/recommendations/tree/main), which contains movies and people who have directed or acted in those movies.

![recommendations model](https://neo4j.com/docs/genai/tutorials/current/embeddings-vector-indexes/_images/recommendations-model.svg)

You will learn how to set up the environment, create embeddings on the movie nodes (both with free and open source libraries, and with external AI providers), create a vector index, and query the database for movies given a loose description or a similar movie.

## [](https://neo4j.com/docs/genai/tutorials/current/embeddings-vector-indexes/#_requirements)Requirements

This guide has the following requirements:

-   A running instance of Neo4j >= 2026.01 and Cypher 25 — If you don’t have one, [install Neo4j locally](https://neo4j.com/docs/operations-manual/current/installation/) or sign up for an [Aura cloud instance](https://neo4j.com/cloud/platform/aura-graph-database/).

-   Some familiarity with [Cypher](https://neo4j.com/docs/genai/tutorials/current/embeddings-vector-indexes/#Cypher) — If you are new to it, check out [Getting started → Cypher](https://neo4j.com/docs/getting-started/cypher/).

-   `python` and some familiarity with it.

-   (Optional) An API key to one of the external AI providers, if you intend to generate embeddings with them.


<table><tbody><tr><td class="icon"><i class="fa icon-tip" title="Tip"></i></td><td class="content">If your database is running Cypher 5, check out <a href="https://neo4j.com/docs/genai/tutorials/5/embeddings-vector-indexes/">the corresponding version of this tutorial</a>.</td></tr></tbody></table>

## Glossary

Aura

[Aura](https://neo4j.com/cloud/platform/aura-graph-database/) is Neo4j’s fully managed cloud service. It comes with both free and paid plans.

Cypher

[Cypher](https://neo4j.com/docs/getting-started/cypher/) is Neo4j’s graph query language that lets you retrieve data from the database. It is like SQL, but for graphs.
