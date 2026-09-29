interface Env {
  ASSETS: Fetcher;
}

// Serve the static designs. In production this worker sits behind
// hirefrank.com/network-jobs*, so strip that prefix before hitting assets.
// Locally (wrangler dev) paths arrive unprefixed and pass straight through.
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const prefix = "/network-jobs";

    if (url.pathname === prefix || url.pathname === prefix + "/") {
      return env.ASSETS.fetch(new Request(url.origin + "/", request));
    }
    if (url.pathname.startsWith(prefix + "/")) {
      url.pathname = url.pathname.slice(prefix.length);
      return env.ASSETS.fetch(new Request(url.toString(), request));
    }
    return env.ASSETS.fetch(request);
  },
};
