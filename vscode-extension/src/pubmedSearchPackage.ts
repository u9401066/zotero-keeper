export const PUBMED_SEARCH_FIXED_COMMIT = 'a849f2ae01d85ba73c1fe219a36bcfb7fb4742d4';
export const PUBMED_SEARCH_VERSION = '0.5.4';
export const PUBMED_SEARCH_ENTRYPOINT = 'pubmed_search.presentation.mcp_server';
export const PUBMED_WORKSPACE_DIR_ENV = 'PUBMED_WORKSPACE_DIR';
export const PUBMED_SEARCH_PACKAGE =
    `pubmed-search-mcp @ https://github.com/u9401066/pubmed-search-mcp/archive/${PUBMED_SEARCH_FIXED_COMMIT}.tar.gz`;

export function compareDottedVersions(actual: string, expected: string): number {
    const actualParts = actual.split('.').map(part => Number.parseInt(part, 10));
    const expectedParts = expected.split('.').map(part => Number.parseInt(part, 10));
    const maxLength = Math.max(actualParts.length, expectedParts.length);

    for (let index = 0; index < maxLength; index++) {
        const actualPart = actualParts[index] ?? 0;
        const expectedPart = expectedParts[index] ?? 0;
        if (actualPart > expectedPart) {
            return 1;
        }
        if (actualPart < expectedPart) {
            return -1;
        }
    }

    return 0;
}
