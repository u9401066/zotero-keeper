# Connect to Zotero

The extension communicates with **Zotero** (7, 8, or 9) running on your computer.

## Requirements

1. **Zotero 7, 8, or 9** must be installed and running
2. The built-in API server must be enabled (default: port 23119)

## Download Zotero

If you don't have Zotero installed:

👉 [Download Zotero](https://www.zotero.org/download/)

## Check Connection

1. Open Zotero on your computer
2. Click "Check Connection" above
3. You should see "✅ Zotero is running"

## Troubleshooting

### "Cannot connect to Zotero"

- Make sure Zotero is open
- Check that local security software allows loopback traffic
- Verify in Zotero: Edit → Settings → Advanced → Allow other applications...

### Remote Zotero

Do not expose or forward Zotero's unauthenticated Local/Connector API port. Run
Keeper beside Zotero Desktop on the same trusted host. For a genuinely remote
library, use Zotero's authenticated HTTPS Web API or a purpose-built service
with TLS, authorization, and explicit network access controls.
