#!/usr/bin/env bun

type Options = {
  url: string;
  includeSelector?: string;
  excludeSelector?: string;
  domain?: string;
  timeoutMs: number;
  json: boolean;
  debug: boolean;
  maxChars?: number;
  noImages: boolean;
};

type SiteRule = {
  host: string;
  include: string;
  exclude?: string;
};

// Per-host selector rules. Subdomain matching is automatic (e.g. python-requests.readthedocs.io).
// Rules are checked in order; the first host match wins.
const SITE_RULES: SiteRule[] = [
  // Anthropic / Claude
  { host: "platform.claude.com",   include: "#content-container",        exclude: "nav,header,footer" },
  { host: "docs.anthropic.com",    include: "#content-container",        exclude: "nav,header,footer" },
  { host: "console.anthropic.com", include: "main",                      exclude: "nav,header,footer,.sidebar" },
  // Mozilla
  { host: "developer.mozilla.org", include: "article",                   exclude: "nav,header,footer" },
  // GitHub
  { host: "github.com",            include: "article",                   exclude: "nav,.sidebar,header,footer" },
  { host: "gist.github.com",       include: ".blob-wrapper,article",     exclude: "nav,header,footer" },
  // Python ecosystem
  { host: "docs.python.org",       include: "div.body",                  exclude: "nav,header,footer,.sphinxsidebar" },
  { host: "pypi.org",              include: "main",                      exclude: "nav,header,footer" },
  // npm
  { host: "npmjs.com",             include: "main",                      exclude: "nav,header,footer" },
  // Rust
  { host: "doc.rust-lang.org",     include: "main",                      exclude: "nav,header,footer" },
  { host: "docs.rs",               include: "main",                      exclude: "nav,header,footer" },
  // Go
  { host: "pkg.go.dev",            include: "main",                      exclude: "nav,header,footer" },
  // Read the Docs (matches *.readthedocs.io subdomains)
  { host: "readthedocs.io",        include: "div.document,.rst-content", exclude: "nav,.wy-nav-side,header,footer" },
  // Stack Overflow
  { host: "stackoverflow.com",     include: "#question,.question",       exclude: "nav,header,footer,.sidebar" },
  // Dev.to
  { host: "dev.to",                include: "article#article-body",      exclude: "nav,header,footer" },
];

const DEFAULT_INCLUDE = "article,main,[role=main]";
const DEFAULT_EXCLUDE = "script,style,noscript,template,svg,nav,header,footer";

// Minimum content text length (chars) to prefer a matched selector over the full body.
// Raised from 120 to 200 to reduce false positives on near-empty containers.
const MIN_CONTENT_CHARS = 200;

function usage(): string {
  return `Usage: bun fetch.ts <url> [options]

Fetch an http/https page and print clean Markdown.

Options:
  --include-selector <css>   Keep only matching elements.
  --exclude-selector <css>   Remove matching elements.
  --domain <url>             Base URL for relative links.
  --timeout-ms <number>      Fetch timeout in milliseconds. Default: 15000.
  --max-chars <number>       Truncate output at N characters; appends a note. Min: 100.
  --no-images                Strip image Markdown (![alt](src)) from output.
  --json                     Emit a JSON object with metadata and markdown.
  --debug                    Print selector diagnostics to stderr.
  -h, --help                 Show this help.

Exit codes:
  0  success
  2  invalid CLI usage
  10 invalid or unsupported URL
  20 fetch/network/HTTP error
  30 empty or unusable content
  40 HTML parse/Markdown conversion error
  50 missing runtime dependency; run: bun install
`;
}

function fail(exitCode: number, message: string, details: Record<string, unknown> = {}): never {
  console.error(JSON.stringify({ status: "error", exitCode, message, ...details }, null, 2));
  process.exit(exitCode);
}

function parseArgs(argv: string[]): Options {
  if (argv.includes("-h") || argv.includes("--help")) {
    console.log(usage());
    process.exit(0);
  }

  const positional: string[] = [];
  const opts: Partial<Options> = { timeoutMs: 15000, json: false, debug: false, noImages: false };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    switch (arg) {
      case "--include-selector":
        opts.includeSelector = requireValue(argv, ++i, arg);
        break;
      case "--exclude-selector":
        opts.excludeSelector = requireValue(argv, ++i, arg);
        break;
      case "--domain":
        opts.domain = requireValue(argv, ++i, arg);
        break;
      case "--timeout-ms": {
        const raw = requireValue(argv, ++i, arg);
        const value = Number.parseInt(raw, 10);
        if (!Number.isFinite(value) || value < 1000) fail(2, "--timeout-ms must be an integer >= 1000");
        opts.timeoutMs = value;
        break;
      }
      case "--max-chars": {
        const raw = requireValue(argv, ++i, arg);
        const value = Number.parseInt(raw, 10);
        if (!Number.isFinite(value) || value < 100) fail(2, "--max-chars must be an integer >= 100");
        opts.maxChars = value;
        break;
      }
      case "--no-images":
        opts.noImages = true;
        break;
      case "--json":
        opts.json = true;
        break;
      case "--debug":
        opts.debug = true;
        break;
      default:
        if (arg.startsWith("-")) fail(2, `Unknown option: ${arg}`);
        positional.push(arg);
    }
  }

  if (positional.length !== 1) fail(2, "Exactly one URL is required", { usage: usage() });

  const url = positional[0];
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    fail(10, "Invalid URL", { url });
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    fail(10, "Only http/https URLs are supported", { url });
  }

  if (opts.domain) {
    try {
      const domainUrl = new URL(opts.domain);
      if (!["http:", "https:"].includes(domainUrl.protocol)) fail(10, "--domain must be http/https", { domain: opts.domain });
    } catch {
      fail(10, "Invalid --domain URL", { domain: opts.domain });
    }
  }

  return {
    url,
    timeoutMs: opts.timeoutMs ?? 15000,
    json: !!opts.json,
    debug: !!opts.debug,
    noImages: !!opts.noImages,
    maxChars: opts.maxChars,
    includeSelector: opts.includeSelector,
    excludeSelector: opts.excludeSelector,
    domain: opts.domain,
  };
}

function requireValue(argv: string[], index: number, option: string): string {
  const value = argv[index];
  if (!value || value.startsWith("--")) fail(2, `${option} requires a value`);
  return value;
}

function matchingRule(url: URL): SiteRule | undefined {
  return SITE_RULES.find(
    (rule) => url.hostname === rule.host || url.hostname.endsWith(`.${rule.host}`)
  );
}

function isMarkdown(contentType: string, url: URL): boolean {
  const path = url.pathname.toLowerCase();
  return (
    contentType.includes("markdown") ||
    path.endsWith(".md") ||
    path.endsWith(".markdown")
  );
}

async function fetchText(
  opts: Options
): Promise<{ body: string; contentType: string; finalUrl: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs);
  try {
    const response = await fetch(opts.url, {
      redirect: "follow",
      signal: controller.signal,
      headers: {
        Accept: "text/markdown,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "claude-skill-web-fetch/1.1",
      },
    });
    const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
    const body = await response.text();
    if (!response.ok) {
      fail(20, `HTTP ${response.status} ${response.statusText}`, { url: opts.url, contentType });
    }
    if (!body.trim()) fail(30, "Fetched content is empty", { url: opts.url, contentType });
    return { body, contentType, finalUrl: response.url };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    fail(20, "Fetch failed", { url: opts.url, error: message });
  } finally {
    clearTimeout(timer);
  }
}

async function loadDependencies() {
  try {
    const linkedom = await import("linkedom");
    const turndownModule = await import("turndown");
    const gfmModule = await import("turndown-plugin-gfm");
    return {
      parseHTML: linkedom.parseHTML,
      TurndownService: turndownModule.default,
      gfm: gfmModule.gfm,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    fail(50, "Missing fallback parser dependency. Run: bun install", { error: message });
  }
}

function removeElements(root: ParentNode, selector: string): void {
  if (!selector.trim()) return;
  for (const node of Array.from(root.querySelectorAll(selector))) {
    node.remove();
  }
}

function absolutizeLinks(root: ParentNode, base: string): void {
  for (const node of Array.from(root.querySelectorAll("a[href]"))) {
    const href = node.getAttribute("href");
    if (!href) continue;
    try {
      node.setAttribute("href", new URL(href, base).href);
    } catch {
      // ignore invalid hrefs
    }
  }
  for (const node of Array.from(root.querySelectorAll("img[src]"))) {
    const src = node.getAttribute("src");
    if (!src) continue;
    try {
      node.setAttribute("src", new URL(src, base).href);
    } catch {
      // ignore invalid srcs
    }
  }
}

function chooseContent(
  document: Document,
  includeSelector: string,
  debug: boolean
): { html: string; selector: string; textLength: number } {
  const candidates = Array.from(document.querySelectorAll(includeSelector));
  const ranked = candidates
    .map((node) => ({
      node,
      textLength: (node.textContent ?? "").replace(/\s+/g, " ").trim().length,
    }))
    .sort((a, b) => b.textLength - a.textLength);

  if (debug) {
    console.error(
      JSON.stringify({
        status: "debug",
        includeSelector,
        candidates: ranked.slice(0, 5).map((item) => item.textLength),
      })
    );
  }

  const best = ranked[0];
  if (best && best.textLength >= MIN_CONTENT_CHARS) {
    return {
      html: (best.node as Element).outerHTML,
      selector: includeSelector,
      textLength: best.textLength,
    };
  }

  const body = document.body;
  const fallbackTextLength = (body?.textContent ?? "").replace(/\s+/g, " ").trim().length;
  return {
    html: body?.innerHTML ?? document.documentElement.outerHTML,
    selector: "body",
    textLength: fallbackTextLength,
  };
}

function cleanMarkdown(
  markdown: string,
  maxChars?: number,
  noImages?: boolean
): string {
  let result = markdown
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{4,}/g, "\n\n\n")
    .trim();

  if (noImages) {
    // Remove image Markdown: ![alt text](url) and ![alt text](url "title")
    result = result.replace(/!\[[^\]]*\]\([^)]*(?:\s+"[^"]*")?\)/g, "");
    result = result.replace(/\n{3,}/g, "\n\n").trim();
  }

  if (maxChars !== undefined && result.length > maxChars) {
    result =
      result.slice(0, maxChars) + "\n\n[…output truncated at --max-chars limit]";
  }

  return result;
}

async function htmlToMarkdown(
  html: string,
  opts: Options,
  contentType: string,
  finalUrl: string
): Promise<{ markdown: string; selector: string; textLength: number }> {
  const { parseHTML, TurndownService, gfm } = await loadDependencies();
  const url = new URL(finalUrl || opts.url);
  const rule = matchingRule(url);
  const includeSelector = opts.includeSelector ?? rule?.include ?? DEFAULT_INCLUDE;
  const excludeSelector = [DEFAULT_EXCLUDE, rule?.exclude, opts.excludeSelector]
    .filter(Boolean)
    .join(",");
  const baseUrl = opts.domain ?? finalUrl ?? opts.url;

  try {
    const { document } = parseHTML(html);
    removeElements(document, excludeSelector);
    removeElements(document, "[hidden],[aria-hidden='true']");
    absolutizeLinks(document, baseUrl);

    const selected = chooseContent(document, includeSelector, opts.debug);
    const turndown = new TurndownService({
      headingStyle: "atx",
      codeBlockStyle: "fenced",
      bulletListMarker: "-",
      emDelimiter: "*",
    });
    turndown.use(gfm);

    const markdown = cleanMarkdown(
      turndown.turndown(selected.html),
      opts.maxChars,
      opts.noImages
    );

    if (markdown.length < 20) {
      fail(30, "Markdown output is empty or too short", {
        selector: selected.selector,
        contentType,
      });
    }
    return { markdown, selector: selected.selector, textLength: selected.textLength };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    fail(40, "HTML parsing or Markdown conversion failed", { error: message, contentType });
  }
}

async function main(): Promise<void> {
  const opts = parseArgs(Bun.argv.slice(2));
  const fetched = await fetchText(opts);
  const finalUrl = fetched.finalUrl || opts.url;
  const parsedUrl = new URL(finalUrl);

  if (isMarkdown(fetched.contentType, parsedUrl)) {
    const markdown = cleanMarkdown(fetched.body, opts.maxChars, opts.noImages);
    if (!markdown) {
      fail(30, "Markdown-native response was empty", { contentType: fetched.contentType });
    }
    if (opts.json) {
      console.log(
        JSON.stringify(
          {
            status: "ok",
            url: opts.url,
            finalUrl,
            contentType: fetched.contentType,
            method: "markdown-native",
            markdown,
          },
          null,
          2
        )
      );
    } else {
      console.log(markdown);
    }
    return;
  }

  const converted = await htmlToMarkdown(fetched.body, opts, fetched.contentType, finalUrl);
  if (opts.json) {
    console.log(
      JSON.stringify(
        {
          status: "ok",
          url: opts.url,
          finalUrl,
          contentType: fetched.contentType,
          method: "html-fallback",
          selector: converted.selector,
          textLength: converted.textLength,
          markdown: converted.markdown,
        },
        null,
        2
      )
    );
  } else {
    console.log(converted.markdown);
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  fail(40, "Unexpected parser failure", { error: message });
});
