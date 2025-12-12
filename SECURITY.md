# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.6.x   | :white_check_mark: |
| 1.5.x   | :white_check_mark: |
| < 1.5   | :x:                |

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

1. **Local API Access**: Zotero's Local API has no authentication
   - Only expose on trusted networks
   - Use firewall rules to restrict access
   - Consider VPN for remote access

2. **Port Proxy**: If using Windows port proxy
   - Bind to specific IPs, not `0.0.0.0` in production
   - Use firewall rules

### Configuration Security

1. **Environment Variables**: Store sensitive config in `.env` files
   - Never commit `.env` to git
   - Use `.env.example` as template

2. **API Keys**: If using NCBI API key
   - Keep it in environment variables
   - Never hardcode in source

### MCP Security

1. **Trusted MCP Clients Only**: Only use with trusted AI agents
2. **Review Actions**: MCP tools can write to Zotero - review what the AI suggests

## Security Features

- No cloud dependencies - all local
- No authentication storage
- Stateless operation
- Input validation on all MCP tools

## Known Limitations

1. **No Authentication**: Zotero Local API has no auth mechanism
   - This is a Zotero design decision
   - Security relies on network access control

2. **Local Network Exposure**: When using remote Zotero
   - Data travels over local network unencrypted
   - Use trusted networks only

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.
