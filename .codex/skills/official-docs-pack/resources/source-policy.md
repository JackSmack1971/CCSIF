# Official Docs Source Policy

The skill must be stricter than a normal web fetcher. It can use broad discovery, but it can only package verified documentation sources.

## Accepted Source Classes

A source can be packaged when it satisfies at least one acceptance class and no rejection rule.

1. **First-party documentation domain**
   - Hostname or path is controlled by the project owner.
   - Examples: `docs.example.com`, `developer.example.com`, `example.com/docs`, `example.com/documentation`, `example.com/reference`, `example.com/api`.

2. **Known official documentation domain**
   - Recognized official docs host for a language, framework, SDK, platform, or API.
   - Examples include `docs.python.org`, `doc.rust-lang.org`, `pkg.go.dev`, `developer.mozilla.org`, `docs.github.com`, `docs.docker.com`, `kubernetes.io/docs`, `docs.anthropic.com`, and `platform.openai.com/docs`.

3. **Official generated API docs**
   - Registry-backed or project-backed generated docs for package ecosystems.
   - Examples: `docs.rs` for Rust crates, `pkg.go.dev` for Go packages, official TypeDoc/Sphinx/MkDocs/Rustdoc sites linked from project metadata.

4. **Official repository documentation**
   - A project-owned repository path containing docs when no separate docs site exists.
   - Allowed only for `README`, `/docs`, `/documentation`, `/guides`, `/examples` when the repository is identified as the official project repository.

5. **Package metadata documentation URL**
   - A documentation link from registry metadata (`npm`, `PyPI`, crates, etc.) when it points to a docs-like host/path and does not violate rejection rules.

## Rejected Source Classes

Never package these as docs:

- Stack Overflow, Reddit, Quora, Medium, Dev.to, Hacker News, Discord, forums, blogs, and newsletters.
- SEO/tutorial aggregators, content farms, scraped mirrors, GitBook copies not linked by the official project, and unofficial translations.
- General homepages with no docs/reference/guide/manual/API/documentation section.
- Pages requiring login, auth tokens, cookies, CAPTCHA, payment, private repos, or browser-only JavaScript rendering.
- Binary-first resources such as PDF, images, videos, archives, and downloads unless the user explicitly asks for a separate extraction workflow.

## Crawl Boundary Rules

- Crawl within the verified docs host and docs path when possible.
- Do not follow links to unrelated hosts unless the host is independently accepted as official docs for the same project.
- Strip fragments and tracking parameters before de-duplication.
- Skip asset paths, feeds, login/signup pages, issue trackers, marketing pages, pricing pages, blog pages, and community pages.
- Record skipped/rejected URLs in `manifest.json`; do not include them under `docs/`.

## Ambiguity Rule

If official ownership cannot be verified with available metadata and URL signals, exclude the source. A smaller official pack is better than a larger contaminated pack.
