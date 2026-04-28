/**
 * /robots.txt — generated at build time by Next.
 *
 * Lets Google / LinkedIn / Twitter index public surfaces (landing,
 * persona share pages, community wall) so OG previews are crawled,
 * while keeping the authed app, admin tools, and API routes out.
 */
import type { MetadataRoute } from "next";

const SITE = "https://mind.simulatte.io";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/persona/", "/probe/", "/community", "/privacy", "/terms"],
        disallow: [
          "/dashboard",
          "/generate",
          "/admin",
          "/admin/",
          "/api/",
          "/welcome",
          "/sign-in",
          "/invite/",
        ],
      },
    ],
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
