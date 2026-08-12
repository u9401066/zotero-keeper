# Connect to Zotero

The extension communicates with **Zotero** (7, 8, 9, or 10+) running on your computer.

## Requirements

1. **Zotero 7, 8, 9, or 10+** must be installed and running
2. The built-in API server must be enabled (default: port 23119)
3. Zotero 10+ is required for Local API write tools such as collection
   creation, existing-item organization, and existing-item file attachment

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

Do not expose or forward Zotero's Local/Connector API port. Zotero 10+ asks for
runtime approval before Local API writes, but the resulting key has no
fine-grained scope. Run Keeper beside Zotero Desktop on the same trusted host.
For a genuinely remote library, use Zotero's authenticated HTTPS Web API or a
purpose-built service with TLS, authorization, and explicit access controls.

### Authorize Zotero 10+ writes

1. Ask the assistant to call `authorize_local_writes`.
2. Before a stored-file upload, call
   `authorize_local_writes(require_remembered=true)` and choose **Always
   Allow** so all three upload phases remain authorized.
3. Review each proposed mutation; call it again with `confirm=true` only after
   the exact item/collection and change are correct.

The authorization key never appears in MCP output or workspace settings.
