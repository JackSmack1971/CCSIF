---
title: "Introduction"
source_url: "https://neo4j.com/docs/graphql/current/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:13.285Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/docs-graphql/issues/new/?title=Docs%20Feedback%20modules/ROOT/pages/index.adoc%20\(ref:%207.x\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Introduction

<table><tbody><tr><td class="icon"><i class="fa icon-note" title="Note"></i></td><td class="content"><div class="paragraph"><p>This is the documentation of the GraphQL Library version 7. For the long-term support (LTS) version 5, refer to <a href="https://neo4j.com/docs/graphql/5/">GraphQL Library version 5 LTS</a>.</p></div></td></tr></tbody></table>

The Neo4j GraphQL Library is a highly flexible, low-code, open source JavaScript library that enables rapid API development for cross-platform and mobile applications by tapping into the power of connected data.

## [](https://neo4j.com/docs/graphql/current/#_how_it_works)How it works

The Neo4j GraphQL Library requires a set of type definitions that describes the shape of your graph data and creates an API layer to communicate with the data.

It generates an entire executable schema with all additional types needed to execute queries and mutations to interact with your Neo4j database.

For example, consider these type definitions:

```graphql
type Product @node {
    productName: String
    category: [Category!]! @relationship(type: "PART_OF", direction: OUT)
}

type Category @node {
    categoryName: String
    products: [Product!]! @relationship(type: "PART_OF", direction: IN)
}
```

Based on these type definitions, the library generates query and mutation templates to create new instances of the types as well as query existing instances.

The following mutation creates a new product as well as a new category:

```graphql
mutation {
  createProducts(
    input: [
      {
        productName: "New Product"
        category: { create: [{ node: { categoryName: "New Category" } }] }
      }
    ]
  ) {
    products {
      productName
      category {
        categoryName
      }
    }
  }
}
```

Here is an example of how you can query existing data:

```graphql
query {
  products {
    productName
    category {
      categoryName
    }
  }
}
```

The response looks like this:

```json
{
  "data": {
    "products": [
      {
        "productName": "New Product",
        "category": [
          {
            "categoryName": "New Category"
          }
        ]
      }
    ]
  }
}
```

For every query and mutation that is executed against this generated schema, the Neo4j GraphQL Library generates a single Cypher query which is executed against the database. This eliminates the [N+1 Problem](https://www.google.com/search?q=graphql+n%2B1), which can make GraphQL implementations slow and inefficient.

See [Integrating the library](https://neo4j.com/docs/graphql/current/integrating-the-library/) to learn how to use the GraphQL Library in your technology stack. Check out [Creating a new project](https://neo4j.com/docs/graphql/current/getting-started/) to create a new project, either based on Neo4j Aura or self-hosted.

## [](https://neo4j.com/docs/graphql/current/#_library_features)Library features

-   Automatic generation of [Queries](https://neo4j.com/docs/graphql/current/queries-aggregations/queries/) and [Mutations](https://neo4j.com/docs/graphql/current/mutations/) for CRUD interactions.

-   [Types](https://neo4j.com/docs/graphql/current/types/), including temporal and spatial.

-   Support for both node and relationship properties.

-   Extensive [Filtering](https://neo4j.com/docs/graphql/current/filtering/), [Sorting](https://neo4j.com/docs/graphql/current/queries-aggregations/sorting/) and [Pagination](https://neo4j.com/docs/graphql/current/queries-aggregations/pagination/) options.

-   [Security options](https://neo4j.com/docs/graphql/current/security/) and additional [Schema Configuration](https://neo4j.com/docs/graphql/current/directives/schema-configuration/).

-   [Subscriptions](https://neo4j.com/docs/graphql/current/subscriptions/) to server events.

-   [Apollo federation integration](https://neo4j.com/docs/graphql/current/integrations/apollo-federation/).

-   Extensibility through the [`@cypher` directive](https://neo4j.com/docs/graphql/current/directives/custom-logic/#_cypher) and/or [Custom Resolvers](https://neo4j.com/docs/graphql/current/directives/custom-logic/#_customresolver).

-   A [Toolbox](https://neo4j.com/docs/graphql/current/getting-started/toolbox/) (UI) to experiment with your Neo4j GraphQL API on Neo4j Desktop.


## [](https://neo4j.com/docs/graphql/current/#_resources)Resources

1.  [GitHub](https://github.com/neo4j/graphql)

2.  [Issue Tracker](https://github.com/neo4j/graphql/issues)

3.  [npm package](https://www.npmjs.com/package/@neo4j/graphql)


## [](https://neo4j.com/docs/graphql/current/#_license)License

Documentation license: [Creative Commons 4.0](https://neo4j.com/docs/license/)

Source: [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)

Get hands-on with the [GraphQL course on GraphAcademy](https://graphacademy.neo4j.com/courses/graphql-basics/?ref=promo-graphql-basics).
