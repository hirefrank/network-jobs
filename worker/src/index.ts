/**
 * Hosted Network Jobs retirement worker.
 * See SUNSET.md for ops context.
 */

const MIGRATION_JSON = {
  retired: true,
  message:
    'The hosted Network Jobs service was retired. It is replaced by network-jobs: free, open-source, runs locally on your own machine. Install it with the command below, then tell your agent "set up network jobs from my resume".',
  install: "npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto",
  docs: 'https://hirefrank.com/network-jobs/',
  github: 'https://github.com/hirefrank/network-jobs',
} as const

const SUNSET_HTML = `<!doctype html><html><head><meta charset="utf-8">
<title>Network Jobs has moved</title></head><body style="font-family:system-ui;max-width:38rem;margin:4rem auto;padding:0 1rem">
<h1>Network Jobs has moved</h1>
<p>The hosted version of Network Jobs is retired. The new version runs
on <em>your</em> machine — your connections, your compute, your data
never leaves your computer.</p>
<pre style="background:#f4f4f4;padding:1rem;overflow-x:auto">npx --yes 'github:hirefrank/network-jobs#main' setup --agent auto</pre>
<p><a href="https://hirefrank.com/network-jobs/">Setup guide</a> ·
<a href="https://github.com/hirefrank/network-jobs">GitHub</a></p>
</body></html>`

function wantsHtml(request: Request): boolean {
  const accept = request.headers.get('accept') ?? ''
  if (accept.includes('application/json')) {
    return false
  }
  if (accept.includes('text/html')) {
    return true
  }
  const path = new URL(request.url).pathname
  if (path.endsWith('.json') || path.startsWith('/api/')) {
    return false
  }
  return accept.includes('text/html')
}

export default {
  fetch(request: Request): Response {
    if (wantsHtml(request)) {
      return new Response(SUNSET_HTML, {
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      })
    }
    return Response.json(MIGRATION_JSON, { status: 410 })
  },
}
