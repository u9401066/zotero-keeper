# Connect to Zotero

The extension communicates with **Zotero 7** running on your computer.

## Requirements

1. **Zotero 7** must be installed and running
2. The built-in API server must be enabled (default: port 23119)

## Download Zotero

If you don't have Zotero installed:

👉 [Download Zotero 7](https://www.zotero.org/download/)

## Check Connection

1. Open Zotero on your computer
2. Click "Check Connection" above
3. You should see "✅ Zotero is running"

## Troubleshooting

### "Cannot connect to Zotero"

- Make sure Zotero is open
- Check firewall settings (allow port 23119)
- Verify in Zotero: Edit → Settings → Advanced → Allow other applications...

### Remote Zotero

If Zotero runs on a different machine:

1. Set `zoteroMcp.zoteroHost` to the machine's IP
2. Set up port forwarding if needed
