import { NextRequest, NextResponse } from "next/server";

const PREVIEW_TOKEN_COOKIE = "lumefy_preview_token";

/**
 * Carry a short-lived preview session from the editor URL into server
 * components and media requests without exposing an admin access token.
 */
export function proxy(request: NextRequest) {
  const previewToken = request.nextUrl.searchParams.get("preview_token");
  if (!previewToken || previewToken.length > 4096) {
    return NextResponse.next();
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-lumefy-preview-token", previewToken);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.cookies.set(PREVIEW_TOKEN_COOKIE, previewToken, {
    maxAge: 15 * 60,
    path: "/",
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
  });
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
