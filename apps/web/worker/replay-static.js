/** Cloudflare Worker entry point for the static recorded-run build. */
const replayStaticWorker = {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    if (response.status !== 404 || request.method !== "GET") return response;

    const url = new URL(request.url);
    if (url.pathname.includes(".")) return response;

    const fallback = new URL("/index.html", url);
    return env.ASSETS.fetch(new Request(fallback, request));
  },
};

export default replayStaticWorker;
