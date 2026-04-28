/**
 * GET /api/community/personas — same-origin proxy + cache for the
 * community wall.
 *
 * WallTicker, PersonaPicker, and the community page all hit
 * `${API}/community/personas?limit=N` cross-origin (Brave Shields
 * blocks them) AND with `cache: "no-store"`, meaning every dashboard
 * load fires a fresh Railway round-trip even though the wall changes
 * roughly never within a 60s window.
 *
 * This proxy:
 *   1. Defeats Brave Shields (same-origin)
 *   2. Caches in the browser for 60s (Cache-Control)
 *   3. Caches at Vercel's edge for 60s (s-maxage)
 *
 * Public endpoint — no auth required, same as upstream.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001").trim();

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "30";
  const upstream = await fetch(
    `${API}/community/personas?limit=${encodeURIComponent(limit)}`,
    { cache: "no-store" },
  );
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      // Browser cache 60s; Vercel edge cache 60s with 5min stale-while-revalidate.
      // Wall content is essentially read-mostly — new personas appear
      // a few times an hour at peak.
      "cache-control": "public, max-age=60, s-maxage=60, stale-while-revalidate=300",
    },
  });
}
