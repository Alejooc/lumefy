export type CartTemplateSectionType =
  | "cart_header"
  | "cart_items"
  | "cart_summary"
  | "cart_empty";

export type CartTemplateSection = {
  id: string;
  type: CartTemplateSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type CartTemplateContent = {
  breadcrumb_title: string;
  title: string;
  clear_cart_label: string;
  product_label: string;
  price_label: string;
  quantity_label: string;
  subtotal_label: string;
  action_label: string;
  summary_title: string;
  total_label: string;
  checkout_label: string;
  empty_title: string;
  empty_description: string;
  continue_shopping_label: string;
};

export type CartTemplateDocument = {
  template?: string;
  settings?: Record<string, unknown>;
  sections?: CartTemplateSection[];
};

const defaultContent: CartTemplateContent = {
  breadcrumb_title: "Carrito",
  title: "Tu carrito",
  clear_cart_label: "Vaciar carrito",
  product_label: "Producto",
  price_label: "Precio",
  quantity_label: "Cantidad",
  subtotal_label: "Subtotal",
  action_label: "Acción",
  summary_title: "Resumen del pedido",
  total_label: "Total",
  checkout_label: "Ir al checkout",
  empty_title: "Tu carrito está vacío",
  empty_description: "Agrega productos para continuar con tu compra.",
  continue_shopping_label: "Seguir comprando",
};

const defaultSections: CartTemplateSection[] = [
  { id: "cart_header", type: "cart_header", enabled: true, settings: {} },
  { id: "cart_items", type: "cart_items", enabled: true, settings: {} },
  { id: "cart_summary", type: "cart_summary", enabled: true, settings: {} },
  { id: "cart_empty", type: "cart_empty", enabled: true, settings: {} },
];

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function normalizeCartTemplate(value: unknown): Required<CartTemplateDocument> {
  const document = objectValue(value);
  const settings = objectValue(document["settings"]);
  const content = objectValue(settings["content"]);
  const configuredSections = Array.isArray(document["sections"])
    ? document["sections"]
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
      .map((section, index) => ({
        id: stringValue(section["id"], `cart-section-${index + 1}`),
        type: section["type"] as CartTemplateSectionType,
        enabled: section["enabled"] !== false,
        settings: objectValue(section["settings"]),
      }))
      .filter((section) => defaultSections.some((item) => item.type === section.type))
    : [];

  return {
    template: "cart",
    settings: {
      ...settings,
      content: {
        ...defaultContent,
        ...Object.fromEntries(
          Object.keys(defaultContent).map((key) => [
            key,
            stringValue(content[key], defaultContent[key as keyof CartTemplateContent]),
          ]),
        ),
      },
    },
    sections: configuredSections.length ? configuredSections : defaultSections,
  };
}

export function cartTemplateContent(value: unknown): CartTemplateContent {
  return normalizeCartTemplate(value).settings["content"] as CartTemplateContent;
}

export function cartTemplateSection(value: unknown, type: CartTemplateSectionType): CartTemplateSection {
  const document = normalizeCartTemplate(value);
  return document.sections.find((section) => section.type === type) || {
    id: type,
    type,
    enabled: true,
    settings: {},
  };
}

export function cartTemplateSectionEnabled(value: unknown, type: CartTemplateSectionType): boolean {
  return cartTemplateSection(value, type).enabled;
}
