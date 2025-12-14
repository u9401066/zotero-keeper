#!/usr/bin/env python3
"""Debug test for mapper collections."""

from zotero_mcp.infrastructure.mappers.pubmed_mapper import map_pubmed_to_zotero

article = {
    'pmid': '12345',
    'title': 'Test Article',
    'abstract': 'Test abstract',
    'journal': 'Test Journal'
}

# Test with collection_keys
result = map_pubmed_to_zotero(article, collection_keys=['MHT7CZ8U'])
print(f"collections field: {result.get('collections')}")
print(f"Full item keys: {list(result.keys())}")
