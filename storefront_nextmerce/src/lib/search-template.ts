export type SearchTemplateSectionType =
  | "search_header"
  | "search_filters"
  | "search_grid";

export type SearchTemplateSection = {
  id: string;
  type: SearchTemplateSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type SearchTemplateContent = {
  breadcrumb_title: string;
  products_label: string;
  filters_label: string;
  sort_label: string;
  clear_filters_label: string;
  empty_title: string;
  empty_description: string;
};

export type SearchTemplateDocument = {
  template?: string;
  settings?: Record<string, unknown>;
  sections?: SearchTemplateSection[];
};

const defaultContent: SearchTemplateContent = {
  breadcrumb_title: "Resultados de búsqueda",
  products_label: "resultados",
  filters_label: "Filtros",
  sort_label: "Ordenar por",
  clear_filters_label: "Limpiar filtros",
  empty_title: "No encontramos resultados",
  empty_description: "Prueba con otra búsqueda o ajusta los filtros.",
};

const defaultSections: SearchTemplateSection[] = [
  { id: "search_header", type: "search_header", enabled: true, settings: {} },
  { id: "search_filters", type: "search_filters", enabled: true, settings: {} },
  { id: "search_grid", type: "search_grid", enabled: true, settings: {} },
];

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function normalizeSearchTemplate(value: unknown): Required<SearchTemplateDocument> {
  const document = objectValue(value);
  const settings = objectValue(document["settings"]);
  const content = objectValue(settings["content"]);
  const configuredSections = Array.isArray(document["sections"])
    ? document["sections"]
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
      .map((section, index) => ({
        id: stringValue(section["id"], `search-section-${index + 1}`),
        type: section["type"] as SearchTemplateSectionType,
        enabled: section["enabled"] !== false,
        settings: objectValue(section["settings"]),
      }))
      .filter((section) => defaultSections.some((item) => item.type === section.type))
    : [];

  return {
    template: "search",
    settings: {
      ...settings,
      content: {
        ...defaultContent,
        ...Object.fromEntries(
          Object.keys(defaultContent).map((key) => [key, stringValue(content[key], defaultContent[key as keyof SearchTemplateContent])]),
        ),
      },
    },
    sections: configuredSections.length ? configuredSections : defaultSections,
  };
}

export function searchTemplateContent(value: unknown): SearchTemplateContent {
  return normalizeSearchTemplate(value).settings["content"] as SearchTemplateContent;
}

export function searchTemplateSection(value: unknown, type: SearchTemplateSectionType): SearchTemplateSection {
  const document = normalizeSearchTemplate(value);
  return document.sections.find((section) => section.type === type) || {
    id: type,
    type,
    enabled: true,
    settings: {},
  };
}

export function searchTemplateSectionEnabled(value: unknown, type: SearchTemplateSectionType): boolean {
  return searchTemplateSection(value, type).enabled;
}
