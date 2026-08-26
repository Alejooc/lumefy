"use client";

import type { CSSProperties } from "react";

const ALLOWED_TAGS = new Set([
  "a",
  "abbr",
  "b",
  "blockquote",
  "br",
  "code",
  "div",
  "em",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "i",
  "img",
  "li",
  "ol",
  "p",
  "pre",
  "small",
  "span",
  "strong",
  "sub",
  "sup",
  "u",
  "ul",
]);

const VOID_TAGS = new Set(["br", "hr", "img"]);
const GLOBAL_ATTRIBUTES = new Set(["aria-label", "class", "id", "role", "title"]);
const TAG_ATTRIBUTES: Record<string, Set<string>> = {
  a: new Set(["href", "rel", "target"]),
  img: new Set(["alt", "height", "loading", "src", "width"]),
};
const URL_ATTRIBUTES = new Set(["href", "src"]);
const BLOCKED_TAGS = "script|style|iframe|object|embed|form";

function escapeAttribute(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function safeContentUrl(value: string, allowMailto = false): string {
  const candidate = value.trim();
  if (!candidate || candidate.startsWith("//")) return "";
  if (candidate.startsWith("/") || candidate.startsWith("#") || candidate.startsWith("?")) return candidate;

  try {
    const url = new URL(candidate);
    if ((url.protocol === "http:" || url.protocol === "https:") && !url.username && !url.password) {
      return candidate;
    }
    if (allowMailto && url.protocol === "mailto:" && url.pathname) return candidate;
  } catch {
    return "";
  }
  return "";
}

function safeEmbedUrl(value: unknown): string {
  const candidate = typeof value === "string" ? value.trim() : "";
  if (!candidate) return "";
  try {
    const url = new URL(candidate);
    if (!url.hostname || url.username || url.password) return "";
    if (url.protocol === "https:") return candidate;
    if (url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname.toLowerCase())) {
      return candidate;
    }
  } catch {
    return "";
  }
  return "";
}

function safeAttributes(tag: string, source: string): string {
  const tagAttributes = TAG_ATTRIBUTES[tag];
  const attributes: string[] = [];
  const pattern = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(source))) {
    const name = match[1].toLowerCase();
    const value = match[2] ?? match[3] ?? match[4] ?? "";
    if ((!GLOBAL_ATTRIBUTES.has(name) && !tagAttributes?.has(name)) || !value || name.startsWith("on") || name === "style") continue;
    const safeValue = URL_ATTRIBUTES.has(name) ? safeContentUrl(value, tag === "a" && name === "href") : value;
    if (!safeValue) continue;
    attributes.push(` ${name}="${escapeAttribute(safeValue)}"`);
  }

  if (tag === "a" && attributes.some((attribute) => attribute === ' target="_blank"') && !attributes.some((attribute) => attribute.startsWith(" rel="))) {
    attributes.push(' rel="noopener noreferrer"');
  }
  return attributes.join("");
}

function sanitizeCustomHtml(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) return "";
  let markup = value.slice(0, 20_000);
  markup = markup
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(new RegExp(`<\\s*(${BLOCKED_TAGS})\\b[^>]*>[\\s\\S]*?(?:<\\s*\\/\\s*\\1\\s*>|$)`, "gi"), "")
    .replace(new RegExp(`<\\s*\\/?\\s*(?:${BLOCKED_TAGS})\\b[^>]*>`, "gi"), "")
    .replace(/<!doctype[^>]*>/gi, "");

  return markup.replace(/<\s*(\/?)\s*([a-z][a-z0-9-]*)([^>]*)>/gi, (_match, closing: string, rawTag: string, rawAttributes: string) => {
    const tag = rawTag.toLowerCase();
    if (!ALLOWED_TAGS.has(tag)) return "";
    if (closing) return VOID_TAGS.has(tag) ? "" : `</${tag}>`;
    const attributes = safeAttributes(tag, rawAttributes);
    return VOID_TAGS.has(tag) ? `<${tag}${attributes} />` : `<${tag}${attributes}>`;
  }).trim();
}

function boundedHeight(value: unknown): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(240, Math.min(900, numeric)) : 420;
}

function choice(value: unknown, allowed: readonly string[], fallback: string): string {
  return typeof value === "string" && allowed.includes(value) ? value : fallback;
}

export default function CustomEmbed({ settings }: { settings: Record<string, unknown> }) {
  const mode = settings["mode"] === "iframe" ? "iframe" : "html";
  const maxWidth = choice(settings["max_width"], ["narrow", "content", "wide", "full"], "content");
  const alignment = choice(settings["alignment"], ["left", "center", "right"], "center");
  const wrapperClassName = `custom-embed custom-embed--${maxWidth} custom-embed--align-${alignment}`;

  if (mode === "iframe") {
    const src = safeEmbedUrl(settings["iframe_url"]);
    if (!src) return null;
    const iframeStyle = { height: `${boundedHeight(settings["iframe_height"])}px` } satisfies CSSProperties;
    return (
      <div className={wrapperClassName}>
        <iframe
          className="custom-embed__frame"
          src={src}
          title={typeof settings["iframe_title"] === "string" && settings["iframe_title"].trim() ? settings["iframe_title"] : "Contenido integrado"}
          loading="lazy"
          sandbox="allow-scripts allow-forms allow-popups allow-presentation"
          referrerPolicy="strict-origin-when-cross-origin"
          style={iframeStyle}
        />
      </div>
    );
  }

  const markup = sanitizeCustomHtml(settings["content"]);
  if (!markup) return null;
  return (
    <div className={wrapperClassName}>
      <div className="custom-embed__html" dangerouslySetInnerHTML={{ __html: markup }} />
    </div>
  );
}
