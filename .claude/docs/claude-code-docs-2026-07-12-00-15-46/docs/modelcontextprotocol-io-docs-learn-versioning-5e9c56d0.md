---
title: "Versioning - Model Context Protocol"
source_url: "https://modelcontextprotocol.io/docs/learn/versioning"
host: "modelcontextprotocol.io"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:41.121Z"
---
The Model Context Protocol uses string-based version identifiers following the format `YYYY-MM-DD`, to indicate the last date backwards incompatible changes were made.

The protocol version will *not* be incremented when the protocol is updated, as long as the changes maintain backwards compatibility. This allows for incremental improvements while preserving interoperability.

##

[​

](https://modelcontextprotocol.io/docs/learn/versioning#revisions)

Revisions

Revisions may be marked as:

-   **Draft**: in-progress specifications, not yet ready for consumption.
-   **Current**: the current protocol version, which is ready for use and may continue to receive backwards compatible changes.
-   **Final**: past, complete specifications that will not be changed.

The **current** protocol version is [**2025-11-25**](https://modelcontextprotocol.io/specification/2025-11-25).

##

[​

](https://modelcontextprotocol.io/docs/learn/versioning#feature-states)

Feature States

Individual features of the specification may additionally be marked as **Deprecated** under the [feature lifecycle and deprecation policy](https://modelcontextprotocol.io/community/feature-lifecycle): the feature remains part of the specification, but is scheduled for removal. Deprecated features document a migration path (or state that none is required) and remain in the specification for at least twelve months, or at least ninety days under the policy’s [expedited-removal exception](https://modelcontextprotocol.io/community/feature-lifecycle#expedited-removal), before they become eligible for removal, after which they may be **Removed** in a future revision. Features that are currently Deprecated are listed in the [deprecated features registry](https://modelcontextprotocol.io/specification/draft/deprecated).

##

[​

](https://modelcontextprotocol.io/docs/learn/versioning#negotiation)

Negotiation

Version negotiation happens during [initialization](https://modelcontextprotocol.io/specification/latest/basic/lifecycle#initialization). Clients and servers **MAY** support multiple protocol versions simultaneously, but they **MUST** agree on a single version to use for the session. The protocol provides appropriate error handling if version negotiation fails, allowing clients to gracefully terminate connections when they cannot find a version compatible with the server.

Was this page helpful?

YesNo

[Clients](https://modelcontextprotocol.io/docs/learn/client-concepts)[Connect to local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers)

⌘I
