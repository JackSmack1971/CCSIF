---
title: "Claude Code GitHub Actions - Claude Code Docs"
source_url: "https://code.claude.com/docs/en/github-actions"
host: "code.claude.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:15:36.547Z"
---
Claude Code GitHub Actions brings AI-powered automation to your GitHub workflow. With a simple `@claude` mention in any PR or issue, Claude can analyze your code, create pull requests, implement features, and fix bugs - all while following your project’s standards. For automatic reviews posted on every PR without a trigger, see [GitHub Code Review](https://code.claude.com/docs/en/code-review).

Claude Code GitHub Actions is built on top of the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview), which enables programmatic integration of Claude Code into your applications. You can use the SDK to build custom automation workflows beyond GitHub Actions.

##

[​

](https://code.claude.com/docs/en/github-actions#why-use-claude-code-github-actions)

Why use Claude Code GitHub Actions?

-   **Instant PR creation**: Describe what you need, and Claude creates a complete PR with all necessary changes
-   **Automated code implementation**: Turn issues into working code with a single command
-   **Follows your standards**: Claude respects your `CLAUDE.md` guidelines and existing code patterns
-   **Simple setup**: Get started in minutes with our installer and API key
-   **Secure by default**: Your code stays on Github’s runners

##

[​

](https://code.claude.com/docs/en/github-actions#what-can-claude-do)

What can Claude do?

Claude Code provides a powerful GitHub Action that transforms how you work with code:

###

[​

](https://code.claude.com/docs/en/github-actions#claude-code-action)

Claude Code Action

This GitHub Action allows you to run Claude Code within your GitHub Actions workflows. You can use this to build any custom workflow on top of Claude Code. [View repository →](https://github.com/anthropics/claude-code-action)

##

[​

](https://code.claude.com/docs/en/github-actions#setup)

Setup

##

[​

](https://code.claude.com/docs/en/github-actions#quick-setup)

Quick setup

Run `/install-github-app` in the Claude Code terminal to set up the integration interactively. The command installs the Claude GitHub App on your repository and then walks you through adding the GitHub Actions workflows and the API key secret. After the GitHub App is installed, the command asks whether to continue with GitHub Actions setup. In Claude Code v2.1.187 and later you can choose **Skip for now** to stop with only the App installed and return to the workflow and secret steps by running `/install-github-app` again. Earlier versions proceed straight to workflow selection.

-   You must be a repository admin to install the GitHub app and add secrets
-   The GitHub app will request read & write permissions for Contents, Issues, and Pull requests
-   This quickstart method is only available for direct Claude API users. If you’re using Amazon Bedrock or Google Cloud’s Agent Platform, see the [Using with Amazon Bedrock and Google Cloud](https://code.claude.com/docs/en/github-actions#using-with-amazon-bedrock-and-google-cloud) section.

##

[​

](https://code.claude.com/docs/en/github-actions#manual-setup)

Manual setup

If the `/install-github-app` command fails or you prefer manual setup, please follow these manual setup instructions:

1.  **Install the Claude GitHub app** to your repository: [https://github.com/apps/claude](https://github.com/apps/claude) The Claude GitHub app requires the following repository permissions:

    -   **Contents**: Read & write (to modify repository files)
    -   **Issues**: Read & write (to respond to issues)
    -   **Pull requests**: Read & write (to create PRs and push changes)

    For more details on security and permissions, see the [security documentation](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md).
2.  **Add ANTHROPIC\_API\_KEY** to your repository secrets ([Learn how to use secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions))
3.  **Copy the workflow file** from [examples/claude.yml](https://github.com/anthropics/claude-code-action/blob/main/examples/claude.yml) into your repository’s `.github/workflows/`

After completing either the quickstart or manual setup, test the action by tagging `@claude` in an issue or PR comment.

##

[​

](https://code.claude.com/docs/en/github-actions#upgrading-from-beta)

Upgrading from Beta

Claude Code GitHub Actions v1.0 introduces breaking changes that require updating your workflow files in order to upgrade to v1.0 from the beta version.

If you’re currently using the beta version of Claude Code GitHub Actions, we recommend that you update your workflows to use the GA version. The new version simplifies configuration while adding powerful new features like automatic mode detection.

###

[​

](https://code.claude.com/docs/en/github-actions#essential-changes)

Essential changes

All beta users must make these changes to their workflow files in order to upgrade:

1.  **Update the action version**: Change `@beta` to `@v1`
2.  **Remove mode configuration**: Delete `mode: "tag"` or `mode: "agent"` (now auto-detected)
3.  **Update prompt inputs**: Replace `direct_prompt` with `prompt`
4.  **Move CLI options**: Convert `max_turns`, `model`, `custom_instructions`, etc. to `claude_args`

###

[​

](https://code.claude.com/docs/en/github-actions#breaking-changes-reference)

Breaking Changes Reference

| Old Beta Input | New v1.0 Input |
| --- | --- |
| `mode` | *(Removed - auto-detected)* |
| `direct_prompt` | `prompt` |
| `override_prompt` | `prompt` with GitHub variables |
| `custom_instructions` | `claude_args: --append-system-prompt` |
| `max_turns` | `claude_args: --max-turns` |
| `model` | `claude_args: --model` |
| `allowed_tools` | `claude_args: --allowedTools` |
| `disallowed_tools` | `claude_args: --disallowedTools` |
| `claude_env` | `settings` JSON format |

###

[​

](https://code.claude.com/docs/en/github-actions#before-and-after-example)

Before and After Example

**Beta version:**

```
- uses: anthropics/claude-code-action@beta
  with:
    mode: "tag"
    direct_prompt: "Review this PR for security issues"
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    custom_instructions: "Follow our coding standards"
    max_turns: "10"
    model: "claude-sonnet-5"
```

**GA version (v1.0):**

```
- uses: anthropics/claude-code-action@v1
  with:
    prompt: "Review this PR for security issues"
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude_args: |
      --append-system-prompt "Follow our coding standards"
      --max-turns 10
      --model claude-sonnet-5
```

The action now automatically detects whether to run in interactive mode (responds to `@claude` mentions) or automation mode (runs immediately with a prompt) based on your configuration.

##

[​

](https://code.claude.com/docs/en/github-actions#example-use-cases)

Example use cases

Claude Code GitHub Actions can help you with a variety of tasks. The [examples directory](https://github.com/anthropics/claude-code-action/tree/main/examples) contains ready-to-use workflows for different scenarios.

###

[​

](https://code.claude.com/docs/en/github-actions#basic-workflow)

Basic workflow

```
name: Claude Code
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
jobs:
  claude:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          # Responds to @claude mentions in comments
```

###

[​

](https://code.claude.com/docs/en/github-actions#using-skills)

Using skills

The `prompt` input accepts a [skill](https://code.claude.com/docs/en/skills) invocation as well as plain text:

-   For a skill in your repository’s `.claude/skills/` directory, run `actions/checkout` before the action step and pass `/skill-name`.
-   For a skill packaged in a plugin, install the plugin with the `plugin_marketplaces` and `plugins` inputs and pass the namespaced `/plugin-name:skill-name`.

The following workflow installs the `code-review` plugin and runs its skill on each new or updated pull request:

```
name: Code Review
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
```

###

[​

](https://code.claude.com/docs/en/github-actions#custom-automation-with-prompts)

Custom automation with prompts

```
name: Daily Report
on:
  schedule:
    - cron: "0 9 * * *"
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Generate a summary of yesterday's commits and open issues"
          claude_args: "--model opus"
```

###

[​

](https://code.claude.com/docs/en/github-actions#common-use-cases)

Common use cases

In issue or PR comments:

```
@claude implement this feature based on the issue description
@claude how should I implement user authentication for this endpoint?
@claude fix the TypeError in the user dashboard component
```

Claude will automatically analyze the context and respond appropriately.

##

[​

](https://code.claude.com/docs/en/github-actions#best-practices)

Best practices

###

[​

](https://code.claude.com/docs/en/github-actions#claude-md-configuration)

CLAUDE.md configuration

Create a `CLAUDE.md` file in your repository root to define code style guidelines, review criteria, project-specific rules, and preferred patterns. This file guides Claude’s understanding of your project standards.

###

[​

](https://code.claude.com/docs/en/github-actions#security-considerations)

Security considerations

Never commit API keys directly to your repository.

For comprehensive security guidance including permissions, authentication, and best practices, see the [Claude Code Action security documentation](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md). Always use GitHub Secrets for API keys:

-   Add your API key as a repository secret named `ANTHROPIC_API_KEY`
-   Reference it in workflows: `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}`
-   Limit action permissions to only what’s necessary
-   Review Claude’s suggestions before merging

Always use GitHub Secrets (for example, `${{ secrets.ANTHROPIC_API_KEY }}`) rather than hardcoding API keys directly in your workflow files.

###

[​

](https://code.claude.com/docs/en/github-actions#optimizing-performance)

Optimizing performance

Use issue templates to provide context, keep your `CLAUDE.md` concise and focused, and configure appropriate timeouts for your workflows.

###

[​

](https://code.claude.com/docs/en/github-actions#ci-costs)

CI costs

When using Claude Code GitHub Actions, be aware of the associated costs: **GitHub Actions costs:**

-   Claude Code runs on GitHub-hosted runners, which consume your GitHub Actions minutes
-   See [GitHub’s billing documentation](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions) for detailed pricing and minute limits

**API costs:**

-   Each Claude interaction consumes API tokens based on the length of prompts and responses
-   Token usage varies by task complexity and codebase size
-   See [Claude’s pricing page](https://claude.com/platform/api) for current token rates

**Cost optimization tips:**

-   Use specific `@claude` commands to reduce unnecessary API calls
-   Configure appropriate `--max-turns` in `claude_args` to prevent excessive iterations
-   Set workflow-level timeouts to avoid runaway jobs
-   Consider using GitHub’s concurrency controls to limit parallel runs

##

[​

](https://code.claude.com/docs/en/github-actions#configuration-examples)

Configuration examples

The Claude Code Action v1 simplifies configuration with unified parameters:

```
- uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: "Your instructions here" # Optional
    claude_args: "--max-turns 5" # Optional CLI arguments
```

Key features:

-   **Unified prompt interface** - Use `prompt` for all instructions
-   **Skills** - Invoke installed [skills](https://code.claude.com/docs/en/skills) directly from the prompt
-   **CLI passthrough** - Any Claude Code CLI argument via `claude_args`
-   **Flexible triggers** - Works with any GitHub event

Visit the [examples directory](https://github.com/anthropics/claude-code-action/tree/main/examples) for complete workflow files.

When responding to issue or PR comments, Claude automatically responds to @claude mentions. For other events, use the `prompt` parameter to provide instructions.

##

[​

](https://code.claude.com/docs/en/github-actions#using-with-amazon-bedrock-and-google-cloud)

Using with Amazon Bedrock and Google Cloud

For enterprise environments, you can use Claude Code GitHub Actions with your own cloud infrastructure. This approach gives you control over data residency and billing while maintaining the same functionality.

###

[​

](https://code.claude.com/docs/en/github-actions#prerequisites)

Prerequisites

Before setting up Claude Code GitHub Actions with cloud providers, you need:

####

[​

](https://code.claude.com/docs/en/github-actions#for-google-cloud%E2%80%99s-agent-platform)

For Google Cloud’s Agent Platform:

1.  A Google Cloud Project with Google Cloud’s Agent Platform enabled
2.  Workload Identity Federation configured for GitHub Actions
3.  A service account with the required permissions
4.  A GitHub App (recommended) or use the default GITHUB\_TOKEN

####

[​

](https://code.claude.com/docs/en/github-actions#for-amazon-bedrock)

For Amazon Bedrock:

1.  An AWS account with Amazon Bedrock enabled
2.  GitHub OIDC Identity Provider configured in AWS
3.  An IAM role with Amazon Bedrock permissions
4.  A GitHub App (recommended) or use the default GITHUB\_TOKEN

1

[

](https://code.claude.com/docs/en/github-actions#)

Create a custom GitHub App (Recommended for 3P Providers)

For best control and security when using 3P providers like Google Cloud’s Agent Platform or Amazon Bedrock, we recommend creating your own GitHub App:

1.  Go to [https://github.com/settings/apps/new](https://github.com/settings/apps/new)
2.  Fill in the basic information:
    -   **GitHub App name**: Choose a unique name (e.g., “YourOrg Claude Assistant”)
    -   **Homepage URL**: Your organization’s website or the repository URL
3.  Configure the app settings:
    -   **Webhooks**: Uncheck “Active” (not needed for this integration)
4.  Set the required permissions:
    -   **Repository permissions**:
        -   Contents: Read & Write
        -   Issues: Read & Write
        -   Pull requests: Read & Write
5.  Click “Create GitHub App”
6.  After creation, click “Generate a private key” and save the downloaded `.pem` file
7.  Note your App ID from the app settings page
8.  Install the app to your repository:
    -   From your app’s settings page, click “Install App” in the left sidebar
    -   Select your account or organization
    -   Choose “Only select repositories” and select the specific repository
    -   Click “Install”
9.  Add the private key as a secret to your repository:
    -   Go to your repository’s Settings → Secrets and variables → Actions
    -   Create a new secret named `APP_PRIVATE_KEY` with the contents of the `.pem` file
10.  Add the App ID as a secret:

-   Create a new secret named `APP_ID` with your GitHub App’s ID

This app will be used with the [actions/create-github-app-token](https://github.com/actions/create-github-app-token) action to generate authentication tokens in your workflows.

**Alternative for Claude API or if you don’t want to setup your own Github app**: Use the official Anthropic app:

1.  Install from: [https://github.com/apps/claude](https://github.com/apps/claude)
2.  No additional configuration needed for authentication

2

[

](https://code.claude.com/docs/en/github-actions#)

Configure cloud provider authentication

Choose your cloud provider and set up secure authentication:

Amazon Bedrock

**Configure AWS to allow GitHub Actions to authenticate securely without storing credentials.**

> **Security Note**: Use repository-specific configurations and grant only the minimum required permissions.

**Required Setup**:

1.  **Enable Amazon Bedrock**:
    -   Request access to Claude models in Amazon Bedrock
    -   For cross-region models, request access in all required regions
2.  **Set up GitHub OIDC Identity Provider**:
    -   Provider URL: `https://token.actions.githubusercontent.com`
    -   Audience: `sts.amazonaws.com`
3.  **Create IAM Role for GitHub Actions**:
    -   Trusted entity type: Web identity
    -   Identity provider: `token.actions.githubusercontent.com`
    -   Permissions: `AmazonBedrockFullAccess` policy
    -   Configure trust policy for your specific repository

**Required Values**:After setup, you’ll need:

-   **AWS\_ROLE\_TO\_ASSUME**: The ARN of the IAM role you created

OIDC is more secure than using static AWS access keys because credentials are temporary and automatically rotated.

See [AWS documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html) for detailed OIDC setup instructions.

Google Cloud's Agent Platform

**Configure Google Cloud to allow GitHub Actions to authenticate securely without storing credentials.**

> **Security Note**: Use repository-specific configurations and grant only the minimum required permissions.

**Required Setup**:

1.  **Enable APIs** in your Google Cloud project:
    -   IAM Credentials API
    -   Security Token Service (STS) API
    -   Google Cloud’s Agent Platform API
2.  **Create Workload Identity Federation resources**:
    -   Create a Workload Identity Pool
    -   Add a GitHub OIDC provider with:
        -   Issuer: `https://token.actions.githubusercontent.com`
        -   Attribute mappings for repository and owner
        -   **Security recommendation**: Use repository-specific attribute conditions
3.  **Create a Service Account**:
    -   Grant only `Vertex AI User` role
    -   **Security recommendation**: Create a dedicated service account per repository
4.  **Configure IAM bindings**:
    -   Allow the Workload Identity Pool to impersonate the service account
    -   **Security recommendation**: Use repository-specific principal sets

**Required Values**:After setup, you’ll need:

-   **GCP\_WORKLOAD\_IDENTITY\_PROVIDER**: The full provider resource name
-   **GCP\_SERVICE\_ACCOUNT**: The service account email address

Workload Identity Federation eliminates the need for downloadable service account keys, improving security.

For detailed setup instructions, consult the [Google Cloud Workload Identity Federation documentation](https://cloud.google.com/iam/docs/workload-identity-federation).

3

[

](https://code.claude.com/docs/en/github-actions#)

Add Required Secrets

Add the following secrets to your repository (Settings → Secrets and variables → Actions):

####

[​

](https://code.claude.com/docs/en/github-actions#for-claude-api-direct-)

For Claude API (Direct):

1.  **For API Authentication**:
    -   `ANTHROPIC_API_KEY`: Your Claude API key from [console.anthropic.com](https://console.anthropic.com/)
2.  **For GitHub App (if using your own app)**:
    -   `APP_ID`: Your GitHub App’s ID
    -   `APP_PRIVATE_KEY`: The private key (.pem) content

####

[​

](https://code.claude.com/docs/en/github-actions#for-google-cloud%E2%80%99s-agent-platform)

For Google Cloud’s Agent Platform

1.  **For GCP Authentication**:
    -   `GCP_WORKLOAD_IDENTITY_PROVIDER`
    -   `GCP_SERVICE_ACCOUNT`
2.  **For GitHub App (if using your own app)**:
    -   `APP_ID`: Your GitHub App’s ID
    -   `APP_PRIVATE_KEY`: The private key (.pem) content

####

[​

](https://code.claude.com/docs/en/github-actions#for-amazon-bedrock)

For Amazon Bedrock

1.  **For AWS Authentication**:
    -   `AWS_ROLE_TO_ASSUME`
2.  **For GitHub App (if using your own app)**:
    -   `APP_ID`: Your GitHub App’s ID
    -   `APP_PRIVATE_KEY`: The private key (.pem) content

4

[

](https://code.claude.com/docs/en/github-actions#)

Create workflow files

Create GitHub Actions workflow files that integrate with your cloud provider. The examples below show complete configurations for both Amazon Bedrock and Google Cloud’s Agent Platform:

Amazon Bedrock workflow

**Prerequisites:**

-   Amazon Bedrock access enabled with Claude model permissions
-   GitHub configured as an OIDC identity provider in AWS
-   IAM role with Amazon Bedrock permissions that trusts GitHub Actions

**Required GitHub secrets:**

| Secret Name | Description |
| --- | --- |
| `AWS_ROLE_TO_ASSUME` | ARN of the IAM role for Amazon Bedrock access |
| `APP_ID` | Your GitHub App ID (from app settings) |
| `APP_PRIVATE_KEY` | The private key you generated for your GitHub App |

```
name: Claude PR Action

permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]

jobs:
  claude-pr:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@claude'))
    runs-on: ubuntu-latest
    env:
      AWS_REGION: us-west-2
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate GitHub App token
        id: app-token
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - name: Configure AWS Credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: us-west-2

      - uses: anthropics/claude-code-action@v1
        with:
          github_token: ${{ steps.app-token.outputs.token }}
          use_bedrock: "true"
          claude_args: '--model us.anthropic.claude-sonnet-4-6 --max-turns 10'
```

The model ID format for Amazon Bedrock includes a region prefix (for example, `us.anthropic.claude-sonnet-4-6`).

Google Cloud's Agent Platform workflow

**Prerequisites:**

-   Google Cloud’s Agent Platform API enabled in your GCP project
-   Workload Identity Federation configured for GitHub
-   Service account with Google Cloud’s Agent Platform permissions

**Required GitHub secrets:**

| Secret Name | Description |
| --- | --- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload identity provider resource name |
| `GCP_SERVICE_ACCOUNT` | Service account email with Google Cloud’s Agent Platform access |
| `APP_ID` | Your GitHub App ID (from app settings) |
| `APP_PRIVATE_KEY` | The private key you generated for your GitHub App |

```
name: Claude PR Action

permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]

jobs:
  claude-pr:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@claude'))
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate GitHub App token
        id: app-token
        uses: actions/create-github-app-token@v2
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - uses: anthropics/claude-code-action@v1
        with:
          github_token: ${{ steps.app-token.outputs.token }}
          trigger_phrase: "@claude"
          use_vertex: "true"
          claude_args: '--model claude-sonnet-4-5@20250929 --max-turns 10'
        env:
          ANTHROPIC_VERTEX_PROJECT_ID: ${{ steps.auth.outputs.project_id }}
          CLOUD_ML_REGION: us-east5
          VERTEX_REGION_CLAUDE_4_5_SONNET: us-east5
```

The project ID is automatically retrieved from the Google Cloud authentication step, so you don’t need to hardcode it.

##

[​

](https://code.claude.com/docs/en/github-actions#troubleshooting)

Troubleshooting

###

[​

](https://code.claude.com/docs/en/github-actions#claude-not-responding-to-@claude-commands)

Claude not responding to @claude commands

Verify the GitHub App is installed correctly, check that workflows are enabled, ensure API key is set in repository secrets, and confirm the comment contains `@claude` (not `/claude`).

###

[​

](https://code.claude.com/docs/en/github-actions#ci-not-running-on-claude%E2%80%99s-commits)

CI not running on Claude’s commits

Ensure you’re using the GitHub App or custom app (not Actions user), check workflow triggers include the necessary events, and verify app permissions include CI triggers.

###

[​

](https://code.claude.com/docs/en/github-actions#authentication-errors)

Authentication errors

Confirm API key is valid and has sufficient permissions. For Amazon Bedrock or Google Cloud’s Agent Platform, check credentials configuration and ensure secrets are named correctly in workflows.

##

[​

](https://code.claude.com/docs/en/github-actions#advanced-configuration)

Advanced configuration

###

[​

](https://code.claude.com/docs/en/github-actions#action-parameters)

Action parameters

The Claude Code Action v1 uses a simplified configuration:

| Parameter | Description | Required |
| --- | --- | --- |
| `prompt` | Instructions for Claude (plain text or a [skill](https://code.claude.com/docs/en/skills) name) | No\* |
| `claude_args` | CLI arguments passed to Claude Code | No |
| `plugin_marketplaces` | Newline-separated list of plugin marketplace Git URLs | No |
| `plugins` | Newline-separated list of plugin names to install before execution | No |
| `anthropic_api_key` | Claude API key | Yes\*\* |
| `github_token` | GitHub token for API access | No |
| `trigger_phrase` | Custom trigger phrase (default: “@claude”) | No |
| `use_bedrock` | Use Amazon Bedrock instead of Claude API | No |
| `use_vertex` | Use Google Cloud’s Agent Platform instead of Claude API | No |

\*Prompt is optional - when omitted for issue/PR comments, Claude responds to trigger phrase
\*\*Required for direct Claude API, not for Amazon Bedrock or Google Cloud’s Agent Platform

####

[​

](https://code.claude.com/docs/en/github-actions#pass-cli-arguments)

Pass CLI arguments

The `claude_args` parameter accepts any Claude Code CLI arguments:

```
claude_args: "--max-turns 5 --model claude-sonnet-5 --mcp-config /path/to/config.json"
```

Common arguments:

-   `--max-turns`: Maximum conversation turns (default: 10)
-   `--model`: Model to use (for example, `claude-sonnet-5`)
-   `--mcp-config`: Path to MCP configuration
-   `--allowedTools`: Comma-separated list of allowed tools. The `--allowed-tools` alias also works.
-   `--debug`: Enable debug output

###

[​

](https://code.claude.com/docs/en/github-actions#alternative-integration-methods)

Alternative integration methods

While the `/install-github-app` command is the recommended approach, you can also:

-   **Custom GitHub App**: For organizations needing branded usernames or custom authentication flows. Create your own GitHub App with required permissions (contents, issues, pull requests) and use the actions/create-github-app-token action to generate tokens in your workflows.
-   **Manual GitHub Actions**: Direct workflow configuration for maximum flexibility
-   **MCP Configuration**: Dynamic loading of Model Context Protocol servers

See the [Claude Code Action documentation](https://github.com/anthropics/claude-code-action/blob/main/docs) for detailed guides on authentication, security, and advanced configuration.

###

[​

](https://code.claude.com/docs/en/github-actions#customizing-claude%E2%80%99s-behavior)

Customizing Claude’s behavior

You can configure Claude’s behavior in two ways:

1.  **CLAUDE.md**: Define coding standards, review criteria, and project-specific rules in a `CLAUDE.md` file at the root of your repository. Claude will follow these guidelines when creating PRs and responding to requests. Check out our [Memory documentation](https://code.claude.com/docs/en/memory) for more details.
2.  **Custom prompts**: Use the `prompt` parameter in the workflow file to provide workflow-specific instructions. This allows you to customize Claude’s behavior for different workflows or tasks.

Claude will follow these guidelines when creating PRs and responding to requests.

Was this page helpful?

YesNo

[Code Review](https://code.claude.com/docs/en/code-review)[GitHub Enterprise Server](https://code.claude.com/docs/en/github-enterprise-server)

⌘I
