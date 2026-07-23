import { Menu } from "@/types/Menu";
import { PublicCollection, PublicStoreNavigationItem } from "@/types/storefront";

function resolveMenuPath(
  item: PublicStoreNavigationItem,
  collectionById: Map<string, PublicCollection>,
): string {
  if (item.item_type === "collection" && item.reference_id) {
    const collection = collectionById.get(item.reference_id);
    return collection ? `/collections/${encodeURIComponent(collection.slug)}` : "/products";
  }

  if (item.item_type === "url" && item.url) {
    return item.url;
  }

  if (item.item_type === "category") {
    return "/products";
  }

  if (item.item_type === "page" && item.url) {
    return item.url;
  }

  return "/";
}

export function buildHeaderMenu(
  items: PublicStoreNavigationItem[],
  collections: PublicCollection[],
): Menu[] {
  const collectionById = new Map(
    collections.map((collection) => [collection.id, collection]),
  );
  const sortedItems = items
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order);
  const childrenByParentId = new Map<string, PublicStoreNavigationItem[]>();

  for (const item of sortedItems) {
    if (!item.parent_id) {
      continue;
    }

    const siblings = childrenByParentId.get(item.parent_id) ?? [];
    siblings.push(item);
    childrenByParentId.set(item.parent_id, siblings);
  }

  return sortedItems
    .filter((item) => !item.parent_id)
    .map((item, index) => {
      const submenuItems = (childrenByParentId.get(item.id) ?? []).map(
        (child, childIndex) => ({
          id: Number(`${index + 1}${childIndex + 1}`),
          title: child.label,
          path: resolveMenuPath(child, collectionById),
          newTab: false,
        }),
      );

      return {
        id: index + 1,
        title: item.label,
        path: resolveMenuPath(item, collectionById),
        newTab: false,
        submenu: submenuItems.length ? submenuItems : undefined,
      };
    });
}
