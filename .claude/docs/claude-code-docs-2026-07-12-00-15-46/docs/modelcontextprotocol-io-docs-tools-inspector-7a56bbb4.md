---
title: "MCP Inspector - Model Context Protocol"
source_url: "https://modelcontextprotocol.io/docs/tools/inspector"
host: "modelcontextprotocol.io"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:42.256Z"
---
The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is an interactive developer tool for testing and debugging MCP servers. While the [Debugging Guide](https://modelcontextprotocol.io/docs/tools/debugging) covers the Inspector as part of the overall debugging toolkit, this document provides a detailed exploration of the Inspector’s features and capabilities.

##

[​

](https://modelcontextprotocol.io/docs/tools/inspector#getting-started)

Getting started

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#installation-and-basic-usage)

Installation and basic usage

The Inspector runs directly through `npx` without requiring installation:

```
npx @modelcontextprotocol/inspector <command>
```

```
npx @modelcontextprotocol/inspector <command> <arg1> <arg2>
```

####

[​

](https://modelcontextprotocol.io/docs/tools/inspector#inspecting-servers-from-npm-or-pypi)

Inspecting servers from npm or PyPI

A common way to start server packages from [npm](https://npmjs.com/) or [PyPI](https://pypi.org/).

-   npm package

-   PyPI package


```
npx -y @modelcontextprotocol/inspector npx <package-name> <args>
# For example
npx -y @modelcontextprotocol/inspector npx @modelcontextprotocol/server-filesystem /Users/username/Desktop
```

```
npx @modelcontextprotocol/inspector uvx <package-name> <args>
# For example
npx @modelcontextprotocol/inspector uvx mcp-server-git --repository ~/code/mcp/servers.git
```

####

[​

](https://modelcontextprotocol.io/docs/tools/inspector#inspecting-locally-developed-servers)

Inspecting locally developed servers

To inspect servers locally developed or downloaded as a repository, the most common way is:

-   TypeScript

-   Python


```
npx @modelcontextprotocol/inspector node path/to/server/index.js args...
```

```
npx @modelcontextprotocol/inspector \
  uv \
  --directory path/to/server \
  run \
  package-name \
  args...
```

Please carefully read any attached README for the most accurate instructions.

##

[​

](https://modelcontextprotocol.io/docs/tools/inspector#feature-overview)

Feature overview

![](https://mintcdn.com/mcp/4ZXF1PrDkEaJvXpn/images/mcp-inspector.png?fit=max&auto=format&n=4ZXF1PrDkEaJvXpn&q=85&s=83b12e2a457c96ef4ad17c7357236290)

The Inspector provides several features for interacting with your MCP server:

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#server-connection-pane)

Server connection pane

-   Allows selecting the [transport](https://modelcontextprotocol.io/specification/latest/basic/transports) for connecting to the server
-   For local servers, supports customizing the command-line arguments and environment

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#resources-tab)

Resources tab

-   Lists all available resources
-   Shows resource metadata (MIME types, descriptions)
-   Allows resource content inspection
-   Supports subscription testing

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#prompts-tab)

Prompts tab

-   Displays available prompt templates
-   Shows prompt arguments and descriptions
-   Enables prompt testing with custom arguments
-   Previews generated messages

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#tools-tab)

Tools tab

-   Lists available tools
-   Shows tool schemas and descriptions
-   Enables tool testing with custom inputs
-   Displays tool execution results

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#notifications-pane)

Notifications pane

-   Presents all logs recorded from the server
-   Shows notifications received from the server

##

[​

](https://modelcontextprotocol.io/docs/tools/inspector#best-practices)

Best practices

###

[​

](https://modelcontextprotocol.io/docs/tools/inspector#development-workflow)

Development workflow

1.  Start Development
    -   Launch Inspector with your server
    -   Verify basic connectivity
    -   Check capability negotiation
2.  Iterative testing
    -   Make server changes
    -   Rebuild the server
    -   Reconnect the Inspector
    -   Test affected features
    -   Monitor messages
3.  Test edge cases
    -   Invalid inputs
    -   Missing prompt arguments
    -   Concurrent operations
    -   Verify error handling and error responses

##

[​

](https://modelcontextprotocol.io/docs/tools/inspector#next-steps)

Next steps

## Inspector Repository

Check out the MCP Inspector source code

## Debugging Guide

Learn about broader debugging strategies

Was this page helpful?

YesNo

[Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)[Debugging](https://modelcontextprotocol.io/docs/tools/debugging)

⌘I
