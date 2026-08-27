export type InformationalPageSlug = "contact" | "about" | "shipping" | "returns" | "privacy" | "terms";

export type InformationalPageContent = {
  eyebrow: string;
  title: string;
  description: string;
  body: string;
};

export type PagesTemplateSectionType = "page_header" | "page_content" | "page_contact_form";

export type PagesTemplateSection = {
  id: string;
  type: PagesTemplateSectionType;
  enabled: boolean;
  settings: Record<string, unknown>;
};

export type PagesTemplateDocument = {
  template?: string;
  settings?: {
    pages?: Record<string, InformationalPageContent>;
    [key: string]: unknown;
  };
  sections?: PagesTemplateSection[];
};

const defaultPages: Record<InformationalPageSlug, InformationalPageContent> = {
  contact: {
    eyebrow: "Estamos para ayudarte",
    title: "Contacto",
    description: "Cuéntanos cómo podemos ayudarte y te responderemos lo antes posible.",
    body: "Nuestro equipo está disponible para resolver tus dudas sobre productos, pedidos y entregas.",
  },
  about: {
    eyebrow: "Conoce nuestra tienda",
    title: "Sobre nosotros",
    description: "Una experiencia de compra pensada para ti.",
    body: "Aquí puedes contar la historia de tu negocio, tus valores y lo que hace especial a tu marca.",
  },
  shipping: {
    eyebrow: "Compra con tranquilidad",
    title: "Envíos y entregas",
    description: "Información clara para recibir tu pedido.",
    body: "Agrega aquí las zonas de cobertura, tiempos estimados y condiciones de entrega de tu tienda.",
  },
  returns: {
    eyebrow: "Tu compra está respaldada",
    title: "Cambios y devoluciones",
    description: "Consulta las condiciones para solicitar un cambio o devolución.",
    body: "Describe aquí los plazos, requisitos y pasos que deben seguir tus clientes.",
  },
  privacy: {
    eyebrow: "Tu información importa",
    title: "Política de privacidad",
    description: "Conoce cómo cuidamos y utilizamos tus datos.",
    body: "Escribe aquí la política de privacidad de tu tienda y la forma en que gestionas la información de tus clientes.",
  },
  terms: {
    eyebrow: "Condiciones de uso",
    title: "Términos y condiciones",
    description: "Las reglas que aplican a las compras en esta tienda.",
    body: "Escribe aquí los términos y condiciones que deben conocer tus clientes antes de comprar.",
  },
};

const defaultSections: PagesTemplateSection[] = [
  { id: "page_header", type: "page_header", enabled: true, settings: {} },
  { id: "page_content", type: "page_content", enabled: true, settings: {} },
  { id: "page_contact_form", type: "page_contact_form", enabled: true, settings: {} },
];

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function isPageSlug(value: string): value is InformationalPageSlug {
  return Object.prototype.hasOwnProperty.call(defaultPages, value);
}

export function normalizePagesTemplate(value: unknown): Required<PagesTemplateDocument> {
  const document = objectValue(value);
  const settings = objectValue(document["settings"]);
  const rawPages = objectValue(settings["pages"]);
  const pages = Object.fromEntries(
    Object.entries(defaultPages).map(([slug, fallback]) => {
      const page = objectValue(rawPages[slug]);
      return [slug, {
        eyebrow: stringValue(page["eyebrow"], fallback.eyebrow),
        title: stringValue(page["title"], fallback.title),
        description: stringValue(page["description"], fallback.description),
        body: stringValue(page["body"], fallback.body),
      }];
    }),
  ) as Record<InformationalPageSlug, InformationalPageContent>;

  const configuredSections = Array.isArray(document["sections"])
    ? document["sections"]
      .filter((section): section is Record<string, unknown> => Boolean(section) && typeof section === "object")
      .map((section, index) => ({
        id: stringValue(section["id"], `page-section-${index + 1}`),
        type: section["type"] as PagesTemplateSectionType,
        enabled: section["enabled"] !== false,
        settings: objectValue(section["settings"]),
      }))
      .filter((section) => defaultSections.some((item) => item.type === section.type))
    : [];

  return {
    template: "pages",
    settings: { ...settings, pages },
    sections: configuredSections.length ? configuredSections : defaultSections,
  };
}

export function informationalPageContent(value: unknown, slug: string): InformationalPageContent {
  const pages = normalizePagesTemplate(value).settings.pages as Record<InformationalPageSlug, InformationalPageContent>;
  return pages[isPageSlug(slug) ? slug : "about"] || defaultPages.about;
}

export function pagesTemplateSection(value: unknown, type: PagesTemplateSectionType): PagesTemplateSection {
  const document = normalizePagesTemplate(value);
  return document.sections.find((section) => section.type === type) || {
    id: type,
    type,
    enabled: true,
    settings: {},
  };
}

export function pagesTemplateSectionEnabled(value: unknown, type: PagesTemplateSectionType): boolean {
  return pagesTemplateSection(value, type).enabled;
}

export const informationalPageOptions: Array<{ slug: InformationalPageSlug; label: string }> = [
  { slug: "contact", label: "Contacto" },
  { slug: "about", label: "Sobre nosotros" },
  { slug: "shipping", label: "Envíos y entregas" },
  { slug: "returns", label: "Cambios y devoluciones" },
  { slug: "privacy", label: "Política de privacidad" },
  { slug: "terms", label: "Términos y condiciones" },
];
