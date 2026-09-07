import NextImage, { type ImageLoaderProps, type ImageProps } from "next/image";

const MAX_MEDIA_WIDTH = 2400;

function storefrontMediaLoader({ src, width, quality }: ImageLoaderProps): string {
  const safeWidth = Math.min(Math.max(Math.round(width), 16), MAX_MEDIA_WIDTH);
  const safeQuality = Math.min(Math.max(Math.round(quality || 75), 40), 85);
  const separator = src.includes("?") ? "&" : "?";
  return `${src}${separator}w=${safeWidth}&q=${safeQuality}`;
}

function isTenantMedia(src: ImageProps["src"]): boolean {
  return typeof src === "string" && src.startsWith("/media/");
}

/**
 * Use Next's optimizer for template assets and the tenant-aware media route
 * for uploads. The latter must stay browser-side so the request keeps the
 * storefront host used to resolve the tenant.
 */
export default function StorefrontImage(props: ImageProps) {
  if (isTenantMedia(props.src)) {
    return <NextImage {...props} loader={storefrontMediaLoader} unoptimized={false} />;
  }

  return <NextImage {...props} />;
}
