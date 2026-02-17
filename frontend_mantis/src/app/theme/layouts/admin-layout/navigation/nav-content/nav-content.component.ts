// Angular import
import { Component, OnInit, inject, output } from '@angular/core';
import { CommonModule, Location, LocationStrategy } from '@angular/common';
import { RouterModule } from '@angular/router';

// project import
import { NavigationItem, NavigationItems } from '../navigation';
import { environment } from 'src/environments/environment';

import { NavGroupComponent } from './nav-group/nav-group.component';

// icon
import { IconService } from '@ant-design/icons-angular';
import {
  DashboardOutline,
  CreditCardOutline,
  LoginOutline,
  QuestionOutline,
  ChromeOutline,
  FontSizeOutline,
  ProfileOutline,
  BgColorsOutline,
  AntDesignOutline,
  FileTextOutline,
  ShopOutline,
  AppstoreOutline,
  SettingOutline,
  ShoppingCartOutline,
  GoldOutline,
  DatabaseOutline,
  TeamOutline,
  TagsOutline,
  CalculatorOutline,
  SolutionOutline,
  BarChartOutline,
  UserOutline,
  AuditOutline,
  BankOutline,
  ColumnWidthOutline,
  RocketOutline,
  SafetyCertificateOutline,
  BellOutline
} from '@ant-design/icons-angular/icons';
import { NgScrollbarModule } from 'ngx-scrollbar';
import { PermissionService } from '../../../../../core/services/permission.service';
import { AuthService } from '../../../../../core/services/auth.service';
import { AppMarketplaceService } from 'src/app/core/services/app-marketplace.service';

@Component({
  selector: 'app-nav-content',
  imports: [CommonModule, RouterModule, NavGroupComponent, NgScrollbarModule],
  templateUrl: './nav-content.component.html',
  styleUrls: ['./nav-content.component.scss']
})
export class NavContentComponent implements OnInit {
  private location = inject(Location);
  private locationStrategy = inject(LocationStrategy);
  private iconService = inject(IconService);
  private permissionService = inject(PermissionService);
  private authService = inject(AuthService);
  private appsService = inject(AppMarketplaceService);

  // public props
  NavCollapsedMob = output();

  navigations: NavigationItem[];

  // version
  title = 'Lumefy';
  currentApplicationVersion = environment.appVersion;

  navigation = NavigationItems;
  windowWidth = window.innerWidth;

  // Constructor
  constructor() {
    this.iconService.addIcon(
      ...[
        DashboardOutline,
        CreditCardOutline,
        FontSizeOutline,
        LoginOutline,
        ProfileOutline,
        BgColorsOutline,
        AntDesignOutline,
        ChromeOutline,
        QuestionOutline,
        FileTextOutline,
        ShopOutline,
        AppstoreOutline,
        SettingOutline,
        ShoppingCartOutline,
        GoldOutline,
        DatabaseOutline,
        TeamOutline,
        TagsOutline,
        CalculatorOutline,
        SolutionOutline,
        BarChartOutline,
        UserOutline,
        AuditOutline,
        BankOutline,
        ColumnWidthOutline,
        RocketOutline,
        SafetyCertificateOutline,
        BellOutline
      ]
    );
    this.navigations = [];
  }

  // Life cycle events
  ngOnInit() {
    if (this.windowWidth < 1025) {
      (document.querySelector('.coded-navbar') as HTMLDivElement)?.classList.add('menupos-static');
    }

    // Subscribe to user changes to update navigation
    this.authService.currentUser.subscribe(() => {
      this.buildNavigation();
    });

    this.appsService.installedChanged$.subscribe(() => {
      this.buildNavigation();
    });
  }

  fireOutClick() {
    let current_url = this.location.path();
    const baseHref = this.locationStrategy.getBaseHref();
    if (baseHref) {
      current_url = baseHref + this.location.path();
    }
    const link = "a.nav-link[ href='" + current_url + "' ]";
    const ele = document.querySelector(link);
    if (ele !== null && ele !== undefined) {
      const parent = ele.parentElement;
      const up_parent = parent?.parentElement?.parentElement;
      const last_parent = up_parent?.parentElement;
      if (parent?.classList.contains('coded-hasmenu')) {
        parent.classList.add('coded-trigger');
        parent.classList.add('active');
      } else if (up_parent?.classList.contains('coded-hasmenu')) {
        up_parent.classList.add('coded-trigger');
        up_parent.classList.add('active');
      } else if (last_parent?.classList.contains('coded-hasmenu')) {
        last_parent.classList.add('coded-trigger');
        last_parent.classList.add('active');
      }
    }
  }

  navMob() {
    if (this.windowWidth < 1025 && document.querySelector('app-navigation.coded-navbar').classList.contains('mob-open')) {
      this.NavCollapsedMob.emit();
    }
  }

  private buildNavigation(): void {
    const base = this.filterNavigation(NavigationItems);
    const user = this.authService.currentUserValue;

    if (!user || user.is_superuser || !this.permissionService.hasPermission('manage_company')) {
      this.navigations = base;
      return;
    }

    this.appsService.getInstalled().subscribe({
      next: (installed) => {
        this.navigations = this.attachInstalledApps(base, installed);
      },
      error: () => {
        this.navigations = base;
      }
    });
  }

  private attachInstalledApps(items: NavigationItem[], installed: { slug: string; name: string; is_enabled: boolean }[]): NavigationItem[] {
    return items.map((item) => {
      if (item.id === 'apps-platform') {
        const children = [...(item.children || [])];
        const index = children.findIndex((child) => child.id === 'apps-installed');
        const installedChildren = installed
          .filter((app) => app.is_enabled)
          .map((app) => ({
            id: `app-installed-${app.slug}`,
            title: app.name,
            type: 'item' as const,
            url: `/apps/installed/${app.slug}`,
            classes: 'nav-item',
            icon: 'appstore',
            breadcrumbs: false,
            permissions: ['manage_company']
          }));

        if (index >= 0) {
          children[index] = {
            ...children[index],
            children: installedChildren
          };
        } else {
          children.push({
            id: 'apps-installed',
            title: 'Apps Instaladas',
            type: 'collapse',
            icon: 'appstore',
            children: installedChildren
          });
        }
        return { ...item, children };
      }
      if (item.children) {
        return { ...item, children: this.attachInstalledApps(item.children, installed) };
      }
      return item;
    });
  }

  private filterNavigation(items: NavigationItem[]): NavigationItem[] {
    const user = this.authService.currentUserValue;
    const isSuperUser = user?.is_superuser;

    return items.reduce((acc, item) => {
      if (isSuperUser && item.id === 'apps-store') {
        return acc;
      }

      // Top-level group filtering (only for groups, NOT their children)
      if (item.type === 'group') {
        // Superuser: only show Admin + Apps groups
        if (isSuperUser && !['admin', 'apps-platform'].includes(item.id)) {
          return acc;
        }
        // Non-superuser: hide admin group
        if (!isSuperUser && item.id === 'admin') {
          return acc;
        }
      }

      // Check item permission
      if (item.permissions && !this.permissionService.hasAnyPermission(item.permissions)) {
        return acc;
      }

      // Process children
      let newItem = { ...item };
      if (newItem.children) {
        newItem.children = this.filterNavigation(newItem.children);
        if (
          newItem.children.length === 0 &&
          (newItem.type === 'group' || newItem.type === 'collapse') &&
          newItem.id !== 'apps-installed'
        ) {
          return acc;
        }
      }

      acc.push(newItem);
      return acc;
    }, [] as NavigationItem[]);
  }
}
