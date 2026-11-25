export const PUBMED_SEARCH_FIXED_COMMIT = 'eb7b2eeb01c0fc73c1dfd9dab36534542c2d2bb6'; // pragma: allowlist secret
export const PUBMED_SEARCH_VERSION = '0.11.0';
export const PUBMED_SEARCH_ENTRYPOINT = 'pubmed_search.presentation.mcp_server';
export const PUBMED_WORKSPACE_DIR_ENV = 'PUBMED_WORKSPACE_DIR';
export const PUBMED_SEARCH_SOURCE_URL =
    `https://github.com/u9401066/pubmed-search-mcp/archive/${PUBMED_SEARCH_FIXED_COMMIT}.tar.gz`;
export const PUBMED_SEARCH_PACKAGE =
    `pubmed-search-mcp @ ${PUBMED_SEARCH_SOURCE_URL}`;

export function compareDottedVersions(actual: string, expected: string): number {
    // Non-numeric segments count as 0 so a malformed version can never compare as "equal or newer".
    const toParts = (version: string): number[] => version.split('.').map(part => {
        const parsed = Number.parseInt(part, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
    });
    const actualParts = toParts(actual);
    const expectedParts = toParts(expected);
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
