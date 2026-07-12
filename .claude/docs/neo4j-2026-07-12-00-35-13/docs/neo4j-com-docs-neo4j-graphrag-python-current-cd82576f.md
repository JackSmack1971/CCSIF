---
title: "GraphRAG for Python¶"
source_url: "https://neo4j.com/docs/neo4j-graphrag-python/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.415Z"
---
# GraphRAG for Python[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#graphrag-for-python "Link to this heading")

This package contains the official Neo4j GraphRAG features for Python.

The purpose of this package is to provide a first party package to developers, where Neo4j can guarantee long term commitment and maintenance as well as being fast to ship new features and high performing patterns and methods.

⚠️ This package is a renamed continuation of neo4j-genai. The package neo4j-genai is deprecated and will no longer be maintained. We encourage all users to migrate to this new package to continue receiving updates and support.

Neo4j versions supported:

-   Neo4j >=5.18.1

-   Neo4j Aura >=5.18.0

-   Neo4j 2026.01+ (enables SEARCH clause with in-index filtering)


Python versions supported:

-   Python 3.14

-   Python 3.13

-   Python 3.12

-   Python 3.11

-   Python 3.10


## Topics[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#topics "Link to this heading")

-   [User Guide: RAG](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html#user-guide-rag)

-   [User Guide: Knowledge Graph Builder](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html#user-guide-kg-builder)

-   [User Guide: Pipeline](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_pipeline.html#user-guide-pipeline)

-   [API Documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/api.html#api-documentation)

-   [Types](https://neo4j.com/docs/neo4j-graphrag-python/current/types.html#types-documentation)


# Usage[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#usage "Link to this heading")

## Installation[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#installation "Link to this heading")

This package requires Python (>=3.10).

To install the latest stable version, use:

pip install neo4j-graphrag

Note

It is always recommended to install python packages for user space in a virtual environment.

## Optional Dependencies[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#optional-dependencies "Link to this heading")

Extra dependencies can be installed with:

pip install "neo4j-graphrag\[openai\]"

List of extra dependencies:

-   LLM providers (at least one is required for RAG and KG Builder Pipeline):

    -   **ollama**: LLMs from Ollama

    -   **openai**: LLMs from OpenAI (including AzureOpenAI)

    -   **google**: LLMs from Vertex AI

    -   **cohere**: LLMs from Cohere

    -   **anthropic**: LLMs from Anthropic

    -   **mistralai**: LLMs from MistralAI


-   **sentence-transformers** : to use embeddings from the sentence-transformers Python package

-   Vector database (to use [External Retrievers](https://neo4j.com/docs/neo4j-graphrag-python/current/api.html#external-retrievers)):

    -   **weaviate**: store vectors in Weaviate

    -   **pinecone**: store vectors in Pinecone

    -   **qdrant**: store vectors in Qdrant


-   **experimental**: experimental features mainly from the Knowledge Graph creation pipelines.

-   **nlp**: installs spaCy for nlp pipelines, used by SpaCySemanticMatchResolver component from the Knowledge Graph creation pipelines.

-   **fuzzy-matching**: installs **rapidfuzz** to fuzzy matching using string similarity, used by FuzzyMatchResolver component from the Knowledge Graph creation pipelines.


Note

The **\`nlp\`** extra (spaCy) is currently **not supported on Python 3.14** due to an upstream spaCy import-time issue (see [spaCy #13895](https://github.com/explosion/spaCy/issues/13895)). Use Python **3.13 or earlier** for spaCy-based features until that is resolved upstream.

## Examples[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#examples "Link to this heading")

### Creating a vector index[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#creating-a-vector-index "Link to this heading")

When creating a vector index, make sure you match the number of dimensions in the index with the number of dimensions the embeddings have.

See [the API documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/api.html#create-vector-index) for more details.

from neo4j import GraphDatabase
from neo4j\_graphrag.indexes import create\_vector\_index

URI \= "neo4j://localhost:7687"
AUTH \= ("neo4j", "password")

INDEX\_NAME \= "vector-index-name"

\# Connect to Neo4j database
driver \= GraphDatabase.driver(URI, auth\=AUTH)

\# Creating the index
create\_vector\_index(
    driver,
    INDEX\_NAME,
    label\="Document",
    embedding\_property\="vectorProperty",
    dimensions\=1536,
    similarity\_fn\="euclidean",
)

Note

Assumed Neo4j is running

On Neo4j 2026.01+, you can also specify `filterable_properties` to enable in-index filtering with the `SEARCH` clause. See [Create a Vector Index with Filterable Properties](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html#filterable-index-creation) for details.

### Populating the Neo4j Vector Index[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#populating-the-neo4j-vector-index "Link to this heading")

Note that the below example is not the only way you can upsert data into your Neo4j database. For example, you could also leverage [the Neo4j Python driver](https://github.com/neo4j/neo4j-python-driver).

from neo4j import GraphDatabase
from neo4j\_graphrag.indexes import upsert\_vectors
from neo4j\_graphrag.types import EntityType

URI \= "neo4j://localhost:7687"
AUTH \= ("neo4j", "password")

\# Connect to Neo4j database
driver \= GraphDatabase.driver(URI, auth\=AUTH)

\# Upsert the vector
vector \= ...
upsert\_vectors(
    driver,
    ids\=\["1234"\],
    embedding\_property\="vectorProperty",
    embeddings\=\[vector\],
    entity\_type\=EntityType.NODE,
)

Note

Assumed Neo4j is running with a defined vector index

### Performing a similarity search[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#performing-a-similarity-search "Link to this heading")

While the library has more retrievers than shown here, the following examples should be able to get you started.

from neo4j import GraphDatabase
from neo4j\_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j\_graphrag.retrievers import VectorRetriever

URI \= "neo4j://localhost:7687"
AUTH \= ("neo4j", "password")

INDEX\_NAME \= "vector-index-name"

\# Connect to Neo4j database
driver \= GraphDatabase.driver(URI, auth\=AUTH)

\# Create Embedder object
\# Note: An OPENAI\_API\_KEY environment variable is required here
embedder \= OpenAIEmbeddings(model\="text-embedding-3-large")

\# Initialize the retriever
retriever \= VectorRetriever(driver, INDEX\_NAME, embedder)

\# Run the similarity search
query\_text \= "How do I do similarity search in Neo4j?"
response \= retriever.search(query\_text\=query\_text, top\_k\=5)

Note

Assumed Neo4j is running with populated vector index in place.

## Limitations[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#limitations "Link to this heading")

The query over the vector index is an *approximate* nearest neighbor search and may not give exact results. [See this reference for more details](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#limitations-and-issues).

# Development[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#development "Link to this heading")

## Install dependencies[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#install-dependencies "Link to this heading")

uv sync \--all-extras

## Getting started[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#getting-started "Link to this heading")

### Issues[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#issues "Link to this heading")

If you have a bug to report or feature to request, first [search to see if an issue already exists](https://docs.github.com/en/github/searching-for-information-on-github/searching-on-github/searching-issues-and-pull-requests#search-by-the-title-body-or-comments). If a related issue doesn’t exist, please raise a new issue using the relevant [issue form](https://github.com/neo4j/neo4j-graphrag-python/issues/new/choose).

If you’re a Neo4j Enterprise customer, you can also reach out to [Customer Support](http://support.neo4j.com/).

If you don’t have a bug to report or feature request, but you need a hand with the library; community support is available via [Neo4j Online Community](https://community.neo4j.com/) and/or [Discord](https://discord.gg/neo4j).

### Make changes[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#make-changes "Link to this heading")

1.  Fork the repository.

2.  Install Python and uv.

3.  Create a working branch from main and start with your changes!


### Pull request[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#pull-request "Link to this heading")

When you’re finished with your changes, create a pull request, also known as a PR.

-   Ensure that you have [signed the CLA](https://neo4j.com/developer/contributing-code/#sign-cla).

-   Ensure that the base of your PR is set to main.

-   Don’t forget to [link your PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) if you are solving one.

-   Enable the checkbox to [allow maintainer edits](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/allowing-changes-to-a-pull-request-branch-created-from-a-fork) so that maintainers can make any necessary tweaks and update your branch for merge.

-   Reviewers may ask for changes to be made before a PR can be merged, either using [suggested changes](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request) or normal pull request comments. You can apply suggested changes directly through the UI, and any other changes can be made in your fork and committed to the PR branch.

-   As you update your PR and apply changes, mark each conversation as [resolved](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/commenting-on-a-pull-request#resolving-conversations).


## Run tests[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#run-tests "Link to this heading")

Run the tests using uv.

uv run pytest

### Unit tests[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#unit-tests "Link to this heading")

This should run out of the box once the dependencies are installed.

uv run pytest tests/unit

### E2E tests[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#e2e-tests "Link to this heading")

To run e2e tests you’d need to have some services running locally:

-   neo4j

-   weaviate

-   weaviate-text2vec-transformers


The easiest way to get it up and running is via Docker compose:

docker compose \-f tests/e2e/docker-compose.yml up

Note

If you suspect something in the databases are cached, run docker compose -f tests/e2e/docker-compose.yml down to remove them completely

Once the services are running, execute the following command to run the e2e tests.

uv run pytest tests/e2e

## Further information[¶](https://neo4j.com/docs/neo4j-graphrag-python/current/#further-information "Link to this heading")

-   [The official Neo4j Python driver](https://github.com/neo4j/neo4j-python-driver)

-   [Neo4j GenAI integrations](https://neo4j.com/docs/cypher-manual/current/genai-integrations/)
