/** Only navigate to the public source systems that NeuroMesh indexes. */
const sourceHosts = new Set([
  'openalex.org',
  'doi.org',
  'arxiv.org',
  'pubmed.ncbi.nlm.nih.gov',
  'github.com',
  'huggingface.co',
  'reporter.nih.gov',
]);

export function safeSourceUrl(value: string): string | undefined {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || !sourceHosts.has(url.hostname)) return undefined;
    return url.href;
  } catch {
    return undefined;
  }
}
