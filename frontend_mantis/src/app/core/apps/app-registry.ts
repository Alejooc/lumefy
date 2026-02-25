import { InstalledApp } from '../services/app-marketplace.service';

export interface AppNavigationRule {
  appSlug: string;
  navIds: string[];
  requireEnabled?: boolean;
}

export const APP_NAVIGATION_RULES: AppNavigationRule[] = [
  {
    appSlug: 'pos_module',
    navIds: ['pos'],
    requireEnabled: true
  }
];

export function getVisibleNavIds(installed: InstalledApp[]): Set<string> {
  const visible = new Set<string>();
  const installedBySlug = new Map(installed.map((app) => [app.slug, app]));

  APP_NAVIGATION_RULES.forEach((rule) => {
    const install = installedBySlug.get(rule.appSlug);
    const isVisible = !!install && (!rule.requireEnabled || install.is_enabled);
    if (isVisible) {
      rule.navIds.forEach((navId) => visible.add(navId));
    }
  });

  return visible;
}
