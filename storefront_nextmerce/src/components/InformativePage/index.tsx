"use client";

import React, { useEffect, useMemo, useState } from "react";
import Breadcrumb from "../Common/Breadcrumb";
import Contact from "../Contact";
import { isTrustedPreviewMessage } from "@/lib/preview";
import {
  informationalPageContent,
  normalizePagesTemplate,
  pagesTemplateSection,
  type PagesTemplateDocument,
  type PagesTemplateSection,
  type PagesTemplateSectionType,
} from "@/lib/pages-template";

function sectionOrder(sections: PagesTemplateSection[], type: PagesTemplateSectionType): number {
  const index = sections.findIndex((section) => section.type === type);
  return index < 0 ? 99 : index;
}

function pageParagraphs(body: string): string[] {
  return body.split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean);
}

const InformativePage = ({
  pageSlug: initialPageSlug,
  pageTemplate = {},
}: {
  pageSlug: string;
  pageTemplate?: PagesTemplateDocument | Record<string, unknown>;
}) => {
  const [previewTemplate, setPreviewTemplate] = useState<unknown>(pageTemplate);
  const [pageSlug, setPageSlug] = useState(initialPageSlug);
  const [previewMode, setPreviewMode] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState("");

  const normalizedTemplate = useMemo(() => normalizePagesTemplate(previewTemplate), [previewTemplate]);
  const page = useMemo(() => informationalPageContent(normalizedTemplate, pageSlug), [normalizedTemplate, pageSlug]);
  const headerSection = useMemo(() => pagesTemplateSection(normalizedTemplate, "page_header"), [normalizedTemplate]);
  const contentSection = useMemo(() => pagesTemplateSection(normalizedTemplate, "page_content"), [normalizedTemplate]);
  const contactSection = useMemo(() => pagesTemplateSection(normalizedTemplate, "page_contact_form"), [normalizedTemplate]);
  const paragraphs = useMemo(() => pageParagraphs(page.body), [page.body]);

  useEffect(() => {
    setPreviewTemplate(pageTemplate);
  }, [pageTemplate]);

  useEffect(() => {
    const handlePreviewMessage = (event: MessageEvent) => {
      if (!isTrustedPreviewMessage(event)) return;
      const message = event.data;
      if (!message || message.type !== "lumefy:preview:apply" || message.template !== "pages") return;

      setPreviewMode(true);
      if (message.document && typeof message.document === "object") setPreviewTemplate(message.document);
      if (typeof message.pageSlug === "string") setPageSlug(message.pageSlug);
      if (typeof message.selectedSectionId === "string") setSelectedSectionId(message.selectedSectionId);
      if (typeof message.selectionMode === "boolean") setSelectionMode(message.selectionMode);
      window.parent.postMessage(
        { type: "lumefy:preview:ack", requestId: message.requestId || null },
        event.origin || "*",
      );
    };

    setPreviewMode(window.parent !== window);
    window.addEventListener("message", handlePreviewMessage);
    if (window.parent !== window) window.parent.postMessage({ type: "lumefy:preview:ready" }, "*");
    return () => window.removeEventListener("message", handlePreviewMessage);
  }, []);

  const handlePreviewSectionClick = (event: React.MouseEvent<HTMLElement>) => {
    if (!previewMode) return;
    const target = event.target as HTMLElement;
    const section = target.closest<HTMLElement>("[data-lumefy-pages-section]");
    if (!section) return;
    if (!selectionMode && target.closest("a,button,input,textarea,select")) return;
    const sectionId = section.dataset.lumefyPagesSection;
    if (!sectionId) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedSectionId(sectionId);
    window.parent.postMessage({ type: "lumefy:preview:select", sectionId }, "*");
  };

  const sectionClass = (section: PagesTemplateSection) =>
    `lumefy-pages-preview-section ${previewMode && selectedSectionId === section.id ? "lumefy-pages-preview-section--selected" : ""}`;
  const contactPageVisible = pageSlug === "contact" && contactSection.enabled;

  return (
    <div className={previewMode && selectionMode ? "lumefy-preview--selecting" : undefined}>
      <section className="overflow-hidden bg-gray-2 pb-20 pt-5 lg:pt-16">
        <div className="max-w-[920px] w-full mx-auto px-4 sm:px-8 xl:px-0">
          <div className="pages-template-sections flex flex-col gap-7.5">
            <div
              className={sectionClass(headerSection)}
              data-lumefy-pages-section="page_header"
              onClick={handlePreviewSectionClick}
              style={{ display: headerSection.enabled ? undefined : "none", order: sectionOrder(normalizedTemplate.sections, "page_header") }}
            >
              <Breadcrumb title={page.title} pages={[page.title]} />
              <div className="mt-7.5 rounded-[18px] bg-white px-6 py-10 shadow-1 sm:px-10 sm:py-14">
                <span className="mb-4 inline-flex rounded-full bg-blue-light-5 px-3.5 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-blue">
                  {page.eyebrow}
                </span>
                <h1 className="max-w-3xl text-3xl font-semibold leading-tight text-dark sm:text-5xl">{page.title}</h1>
                <p className="mt-5 max-w-2xl text-lg leading-8 text-dark-3">{page.description}</p>
              </div>
            </div>

            <article
              className={sectionClass(contentSection)}
              data-lumefy-pages-section="page_content"
              onClick={handlePreviewSectionClick}
              style={{ display: contentSection.enabled ? undefined : "none", order: sectionOrder(normalizedTemplate.sections, "page_content") }}
            >
              <div className="rounded-[18px] bg-white px-6 py-8 shadow-1 sm:px-10 sm:py-10">
                <div className="prose prose-slate max-w-none text-[16px] leading-8 text-dark-3">
                  {paragraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 16)}-${index}`} className="mb-5 last:mb-0">{paragraph}</p>)}
                </div>
              </div>
            </article>

            <div
              className={sectionClass(contactSection)}
              data-lumefy-pages-section="page_contact_form"
              onClick={handlePreviewSectionClick}
              style={{ display: contactPageVisible ? undefined : "none", order: sectionOrder(normalizedTemplate.sections, "page_contact_form") }}
            >
              <Contact embedded />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default InformativePage;
