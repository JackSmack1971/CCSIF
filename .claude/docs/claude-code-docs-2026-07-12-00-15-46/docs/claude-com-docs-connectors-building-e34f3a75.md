---
title: "Building custom connectors - Claude.ai Documentation"
source_url: "https://claude.com/docs/connectors/building"
host: "claude.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:42.718Z"
---
##

[​

](https://claude.com/docs/connectors/building#getting-started)

Getting started

**Authentication is the most common stumbling block.** Before you build, read the [authentication reference](https://claude.com/docs/connectors/building/authentication)—Claude’s auth support differs from the generic MCP spec in a few important ways.

Not sure whether to build an MCP server, a plugin, or both? See [what to build](https://claude.com/docs/connectors/building/what-to-build).

**Build with Claude.** Install the official [`mcp-server-dev` plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/mcp-server-dev) in Claude Code—it walks you through building, testing, and packaging an MCP server interactively, using these docs as its reference.

###

[​

](https://claude.com/docs/connectors/building#key-resources)

Key resources

-   **SDK Examples**: [TypeScript](https://github.com/modelcontextprotocol/typescript-sdk) and [Python](https://github.com/modelcontextprotocol/python-sdk) SDKs contain server implementation examples
-   **Protocol Specification**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
-   **Hosting Solutions**: Platforms like Cloudflare offer remote MCP server hosting with autoscaling and OAuth management
-   **Auth Specifications**: Review the [authorization spec](https://modelcontextprotocol.io/specification/latest/basic/authorization) with emphasis on third-party service flows

##

[​

](https://claude.com/docs/connectors/building#transport-&-authentication)

Transport & authentication

###

[​

](https://claude.com/docs/connectors/building#supported-transports)

Supported transports

Claude supports both Streamable HTTP and the legacy HTTP+SSE transport. The legacy HTTP+SSE transport is being deprecated in favor of Streamable HTTP.

###

[​

](https://claude.com/docs/connectors/building#authentication-features)

Authentication features

-   Supports the [2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization), [2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization), and [2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization) auth specifications
-   Dynamic Client Registration (DCR) enabled
-   OAuth callback: `https://claude.ai/api/mcp/auth_callback` (hosted surfaces); loopback redirect for Claude Code — see [callback URLs](https://claude.com/docs/connectors/building/authentication#callback-urls)
-   Token refresh and expiry support
-   Custom credentials for non-DCR servers

##

[​

](https://claude.com/docs/connectors/building#protocol-features)

Protocol features

###

[​

](https://claude.com/docs/connectors/building#supported)

Supported

-   [Tools](https://modelcontextprotocol.io/specification/latest/server/tools), [prompts](https://modelcontextprotocol.io/specification/latest/server/prompts), and [resources](https://modelcontextprotocol.io/specification/latest/server/resources)
-   [Text](https://modelcontextprotocol.io/specification/latest/schema#textcontent) and [image-based](https://modelcontextprotocol.io/specification/latest/server/tools#image-content) tool results
-   [Text](https://modelcontextprotocol.io/specification/latest/schema#textresourcecontents) and [binary](https://modelcontextprotocol.io/specification/latest/schema#blobresourcecontents) resources

###

[​

](https://claude.com/docs/connectors/building#not-yet-supported)

Not yet supported

-   Resource subscriptions
-   Sampling
-   Advanced/draft capabilities

##

[​

](https://claude.com/docs/connectors/building#technical-specifications)

Technical specifications

| Constraint | Limit |
| --- | --- |
| Claude.ai/Desktop max tool result size | ~150,000 characters |
| Claude Code max tool result size | 25,000 tokens (configurable via `MAX_MCP_OUTPUT_TOKENS`) |
| Claude Code timeout | Configurable via `MCP_TOOL_TIMEOUT` |
| Claude.ai/Desktop timeout | 300 seconds (5 minutes) |
| Transport protocol | Streamable HTTP (legacy HTTP+SSE being deprecated) |

##

[​

](https://claude.com/docs/connectors/building#testing-your-server)

Testing your server

1.  Add directly to Claude via **Settings > Connectors**
2.  Use the [MCP inspector](https://modelcontextprotocol.io/docs/tools/inspector) to validate auth flows
3.  Add to Claude Code with `claude mcp add` and check `/mcp` for status. See the [Claude Code MCP quickstart](https://code.claude.com/docs/en/mcp-quickstart).

##

[​

](https://claude.com/docs/connectors/building#related-topics)

Related topics

## MCP Overview

Understanding the Model Context Protocol.

## Submit to Directory

Review requirements and submit your connector.

## Test in Claude Code

Connect and debug your server with the Claude Code CLI.

Was this page helpful?

YesNo

[Submit to directory](https://claude.com/docs/connectors/building/submission)[What to build](https://claude.com/docs/connectors/building/what-to-build)

⌘I
