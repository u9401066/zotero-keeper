# Configure PubMed Access

PubMed (NCBI) requests that users provide an email address for API access.

## Why Provide Email?

- NCBI can contact you if there's a problem with your queries
- Allows higher rate limits for searches
- Required for heavy usage

## Setting Your Email

Open VS Code settings and set:

```json
"zoteroMcp.ncbiEmail": "your.email@example.com"
```

Or click "Open Settings" above.

## Without Email

The extension still works without an email, but:
- Rate limits are more strict
- NCBI may block excessive requests

## Privacy

Your email is only sent to NCBI's servers and is not shared elsewhere.
See [NCBI's Privacy Policy](https://www.ncbi.nlm.nih.gov/home/about/policies/).
