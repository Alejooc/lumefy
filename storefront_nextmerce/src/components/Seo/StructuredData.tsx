import type { JsonLdDocument } from "@/lib/structured-data";
import { serializeJsonLd } from "@/lib/structured-data";

export default function StructuredData({ data }: { data: JsonLdDocument }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: serializeJsonLd(data) }}
    />
  );
}
