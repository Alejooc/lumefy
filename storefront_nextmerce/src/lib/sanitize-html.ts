import DOMPurify from "isomorphic-dompurify";

const PRODUCT_DESCRIPTION_TAGS = [
  "a",
  "blockquote",
  "br",
  "caption",
  "code",
  "dd",
  "del",
  "div",
  "dl",
  "dt",
  "em",
  "figcaption",
  "figure",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "img",
  "ins",
  "li",
  "ol",
  "p",
  "pre",
  "s",
  "small",
  "span",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "th",
  "thead",
  "tr",
  "u",
  "ul",
];

const PRODUCT_DESCRIPTION_ATTRIBUTES = [
  "alt",
  "class",
  "colspan",
  "height",
  "href",
  "loading",
  "rel",
  "rowspan",
  "src",
  "srcset",
  "sizes",
  "title",
  "width",
];

/**
 * Render provider-authored product HTML without allowing scripts, event
 * handlers, unsafe URLs, or embedded executable content into the storefront.
 */
export function sanitizeProductDescription(value?: string | null): string {
  if (!value?.trim()) return "";

  return DOMPurify.sanitize(value, {
    ALLOWED_TAGS: PRODUCT_DESCRIPTION_TAGS,
    ALLOWED_ATTR: PRODUCT_DESCRIPTION_ATTRIBUTES,
    FORBID_ATTR: ["style"],
    RETURN_TRUSTED_TYPE: false,
  });
}
