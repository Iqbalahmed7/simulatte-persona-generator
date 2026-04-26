/**
 * auth.config.ts — Edge-safe Auth.js v5 config (NO adapter, NO pg).
 *
 * This file is imported by middleware.ts (Edge runtime). It must never
 * import pg, @auth/pg-adapter, or any other Node-only module.
 *
 * auth.ts imports this and adds the pg adapter for the Node runtime.
 */
import type { NextAuthConfig } from "next-auth";
import Google from "next-auth/providers/google";
import Resend from "next-auth/providers/resend";

export const authConfig: NextAuthConfig = {
  pages: {
    signIn: "/sign-in",
    verifyRequest: "/sign-in?verify=1",
  },
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    Resend({
      apiKey: process.env.AUTH_RESEND_KEY!,
      from: process.env.EMAIL_FROM ?? "noreply@mind.simulatte.io",
      name: "The Mind",
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isProtected =
        nextUrl.pathname.startsWith("/generate") ||
        nextUrl.pathname.startsWith("/persona/") ||
        nextUrl.pathname.startsWith("/probe/");
      if (isProtected && !isLoggedIn) return false; // triggers redirect to signIn
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id;
        token.email = user.email ?? token.email;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.sub && session.user) {
        (session.user as typeof session.user & { id: string }).id = token.sub;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};
