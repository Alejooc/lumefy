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
  RocketOutline
} from '@ant-design/icons-angular/icons';
import { NgScrollbarModule } from 'ngx-scrollbar';
import { PermissionService } from '../../../../../core/services/permission.service';
import { AuthService } from '../../../../../core/services/auth.service';

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
        RocketOutline
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
      this.navigations = this.filterNavigation(NavigationItems);
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

  private filterNavigation(items: NavigationItem[]): NavigationItem[] {
    const user = this.authService.currentUserValue;
    const isSuperUser = user?.is_superuser;

    return items.reduce((acc, item) => {
      // Top-level group filtering (only for groups, NOT their children)
      if (item.type === 'group') {
        // Superuser: only show Admin group
        if (isSuperUser && item.id !== 'admin') {
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
        if (newItem.children.length === 0 && (newItem.type === 'group' || newItem.type === 'collapse')) {
          return acc;
        }
      }

      acc.push(newItem);
      return acc;
    }, [] as NavigationItem[]);
  }
}
