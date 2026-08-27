export type CollectionTemplateSectionType =
  | "collection_header"
  | "collection_filters"
  | "collection_grid";

export type CollectionTemplateSection = {
  id: string;
  type: CollectionTemplateSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type CollectionTemplateContent = {
  breadcrumb_title: string;
  products_label: string;
  filters_label: string;
  sort_label: string;
  clear_filters_label: string;
  empty_title: string;
  empty_description: string;
};

export type CollectionTemplateDocument = {
  template?: string;
  settings?: Record<string, unknown>;
  sections?: CollectionTemplateSection[];
};

const defaultContent: CollectionTemplateContent = {
  breadcrumb_title: "Colección",
  products_label: "productos",
  filters_label: "Filtros",
  sort_label: "Ordenar por",
  clear_filters_label: "Limpiar filtros",
  empty_title: "No encontramos productos",
  empty_description: "Prueba cambiar los filtros o explorar otra colección.",
};

const defaultSections: CollectionTemplateSection[] = [
  { id: "collection_header", type: "collection_header", enabled: true, settings: {} },
  { id: "collection_filters", type: "collection_filters", enabled: true, settings: {} },
  { id: "collection_grid", type: "collection_grid", enabled: true, settings: {} },
];

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function normalizeCollectionTemplate(value: unknown): Required<CollectionTemplateDocument> {
  const document = objectValue(value);
  const settings = objectValue(document["settings"]);
  const content = objectValue(settings["content"]);
  const configuredSections = Array.isArray(document["sections"])
    ? document["sections"]
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
      .map((section, index) => ({
        id: stringValue(section["id"], `collection-section-${index + 1}`),
        type: section["type"] as CollectionTemplateSectionType,
        enabled: section["enabled"] !== false,
        settings: objectValue(section["settings"]),
      }))
      .filter((section) => defaultSections.some((item) => item.type === section.type))
    : [];

  return {
    template: "collection",
    settings: {
      ...settings,
      content: {
        ...defaultContent,
        ...Object.fromEntries(
          Object.keys(defaultContent).map((key) => [key, stringValue(content[key], defaultContent[key as keyof CollectionTemplateContent])]),
        ),
      },
    },
    sections: configuredSections.length ? configuredSections : defaultSections,
  };
}

export function collectionTemplateContent(value: unknown): CollectionTemplateContent {
  return normalizeCollectionTemplate(value).settings["content"] as CollectionTemplateContent;
}

export function collectionTemplateSection(value: unknown, type: CollectionTemplateSectionType): CollectionTemplateSection {
  const document = normalizeCollectionTemplate(value);
  return document.sections.find((section) => section.type === type) || {
    id: type,
    type,
    enabled: true,
    settings: {},
  };
}

export function collectionTemplateSectionEnabled(value: unknown, type: CollectionTemplateSectionType): boolean {
  return collectionTemplateSection(value, type).enabled;
}
