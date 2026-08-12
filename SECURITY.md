# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainers directly (create a private security advisory on GitHub)
3. Or use GitHub's [Security Advisory](https://github.com/u9401066/zotero-keeper/security/advisories/new) feature

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Depends on severity
  - Critical: ASAP (aim for 24-48 hours)
  - High: Within 1 week
  - Medium: Within 2 weeks
  - Low: Next release

## Security Best Practices

When using Zotero Keeper:

### Network Security

1. **Keep Zotero local interfaces on loopback**: Local API reads and Connector
   endpoints are local interfaces. Zotero 10+ writes require runtime approval,
   but the resulting key is intentionally unscoped.
   - Run Zotero Keeper on the same trusted host as Zotero Desktop.
   - Keep `ZOTERO_HOST=localhost` (or `127.0.0.1`).
   - Never expose or forward port `23119` to a LAN or the Internet.

2. **Use an authenticated remote interface**: For a genuinely remote library,
   use Zotero's authenticated HTTPS Web API or a purpose-built service with TLS,
   authorization, auditing, and explicit network access controls.

### Configuration Security

1. **Environment Variables**: Store sensitive config in `.env` files
   - Never commit `.env` to git
   - Use `.env.example` as template

2. **API Keys**: If using NCBI API key
   - Keep it in environment variables
   - Never hardcode in source

3. **Zotero Local API key**: Keeper obtains it only from Zotero's runtime
   authorization dialog
   - The key remains in process memory and must never appear in MCP arguments,
     results, logs, URLs, or workspace files
   - Reauthorize explicitly after a process restart, invalid key, or database
     Server-ID change
   - Multi-step file uploads require the user to choose Always Allow
   - Obtain response-bound identity before preview; every preview and confirmed
     mutation carries that same `expected_server_id`
   - If authorization returns another identity, discard the proposal and repeat
     the read, preview, and approval. Never supplement identity only after review

### MCP Security

1. **Trusted MCP Clients Only**: Only use with trusted AI agents
2. **Review Actions**: MCP tools can write to Zotero - review what the AI suggests
3. **Confirm Destinations**: Select a collection before importing. Writing to My
   Library root requires explicit confirmation and `allow_library_root=true`.

## Security Features

- Zotero Local/Connector access defaults to loopback
- Collection-aware imports fail closed when no destination is confirmed
- My Library root writes require explicit authorization
- MCP SDK v2 typed tool schemas and input validation
- Zotero 10+ writes are response-bound Server-ID, loopback-only, and
  confirmation-gated. Metadata updates use exact-item object versions;
  full-text writes use response-bound library cursors with bulk
  `POST /api/users/0/fulltext`
- NCBI credentials are read from environment/configuration rather than hardcoded

## Known Limitations

1. **Unscoped local authorization**: Zotero 10+ authenticates Local API writes,
   but a granted key is not restricted to individual libraries or operations.
   Local reads and Connector endpoints also retain a same-machine trust
   boundary, so port 23119 must remain on loopback.

2. **Trusted-agent boundary**: An authorized MCP client can invoke write tools.
   Review proposed imports, collection choices, and root-library confirmations.

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.
