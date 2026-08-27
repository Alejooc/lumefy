export type ProductTemplateSectionType =
  | "product_gallery"
  | "product_information"
  | "product_description"
  | "product_related";

export type ProductTemplateSection = {
  id: string;
  type: ProductTemplateSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type ProductTemplateContent = {
  breadcrumb_title: string;
  price_label: string;
  stock_in_label: string;
  stock_out_label: string;
  free_delivery_text: string;
  promo_text: string;
  description_tab_label: string;
  details_tab_label: string;
  reviews_tab_label: string;
  reviews_empty_title: string;
  reviews_empty_description: string;
  submit_review_label: string;
};

export type ProductTemplateDocument = {
  template?: string;
  settings?: Record<string, unknown>;
  sections?: ProductTemplateSection[];
};

const defaultContent: ProductTemplateContent = {
  breadcrumb_title: "Detalle del producto",
  price_label: "Precio",
  stock_in_label: "Disponible",
  stock_out_label: "Agotado",
  free_delivery_text: "Entrega disponible según cobertura",
  promo_text: "Compra segura y atención personalizada",
  description_tab_label: "Descripción",
  details_tab_label: "Información adicional",
  reviews_tab_label: "Reseñas",
  reviews_empty_title: "Reseñas próximamente",
  reviews_empty_description: "Aún no hay reseñas publicadas para este producto.",
  submit_review_label: "Escribir reseña",
};

const defaultSections: ProductTemplateSection[] = [
  { id: "product_gallery", type: "product_gallery", enabled: true, settings: {} },
  { id: "product_information", type: "product_information", enabled: true, settings: {} },
  { id: "product_description", type: "product_description", enabled: true, settings: {} },
  { id: "product_related", type: "product_related", enabled: true, settings: {} },
];

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function normalizeProductTemplate(value: unknown): Required<ProductTemplateDocument> {
  const document = objectValue(value);
  const settings = objectValue(document["settings"]);
  const content = objectValue(settings["content"]);
  const configuredSections = Array.isArray(document["sections"])
    ? document["sections"]
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
      .map((section, index) => ({
        id: stringValue(section["id"], `product-section-${index + 1}`),
        type: section["type"] as ProductTemplateSectionType,
        enabled: section["enabled"] !== false,
        settings: objectValue(section["settings"]),
      }))
      .filter((section) => defaultSections.some((item) => item.type === section.type))
    : [];

  return {
    template: "product",
    settings: {
      ...settings,
      content: {
        ...defaultContent,
        ...Object.fromEntries(
          Object.keys(defaultContent).map((key) => [key, stringValue(content[key], defaultContent[key as keyof ProductTemplateContent])]),
        ),
      },
    },
    sections: configuredSections.length ? configuredSections : defaultSections,
  };
}

export function productTemplateContent(value: unknown): ProductTemplateContent {
  return normalizeProductTemplate(value).settings["content"] as ProductTemplateContent;
}

export function productTemplateSection(value: unknown, type: ProductTemplateSectionType): ProductTemplateSection {
  const document = normalizeProductTemplate(value);
  return document.sections.find((section) => section.type === type) || {
    id: type,
    type,
    enabled: true,
    settings: {},
  };
}

export function productTemplateSectionEnabled(value: unknown, type: ProductTemplateSectionType): boolean {
  return productTemplateSection(value, type).enabled;
}
