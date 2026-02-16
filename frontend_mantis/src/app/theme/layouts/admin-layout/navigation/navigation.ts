export interface NavigationItem {
  id: string;
  title: string;
  type: 'item' | 'collapse' | 'group';
  translate?: string;
  icon?: string;
  hidden?: boolean;
  url?: string;
  classes?: string;
  groupClasses?: string;
  exactMatch?: boolean;
  external?: boolean;
  target?: boolean;
  breadcrumbs?: boolean;
  children?: NavigationItem[];
  link?: string;
  description?: string;
  path?: string;
  permissions?: string[];
}

export const NavigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'default',
        title: 'Default',
        type: 'item',
        classes: 'nav-item',
        url: '/dashboard/default',
        icon: 'dashboard',
        breadcrumbs: false
      }
    ]
  },
  {
    id: 'admin',
    title: 'Super Admin',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['manage_saas'],
    children: [
      {
        id: 'admin-dashboard',
        title: 'Dashboard',
        type: 'item',
        url: '/admin/dashboard',
        classes: 'nav-item',
        icon: 'dashboard'
      },
      {
        id: 'companies',
        title: 'Empresas',
        type: 'item',
        url: '/admin/companies',
        classes: 'nav-item',
        icon: 'shop'
      },
      {
        id: 'plans',
        title: 'Planes',
        type: 'item',
        url: '/admin/plans',
        classes: 'nav-item',
        icon: 'appstore'
      },
      {
        id: 'settings',
        title: 'Configuración',
        type: 'item',
        url: '/admin/settings',
        classes: 'nav-item',
        icon: 'setting'
      }
    ]
  },
  {
    id: 'inventory',
    title: 'Catálogo',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['view_inventory'],
    children: [
      {
        id: 'products',
        title: 'Productos',
        type: 'item',
        classes: 'nav-item',
        url: '/products',
        icon: 'shopping-cart',
        permissions: ['view_products']
      },
      {
        id: 'categories',
        title: 'Categorías',
        type: 'item',
        classes: 'nav-item',
        url: '/categories',
        icon: 'gold',
        breadcrumbs: true,
        permissions: ['view_products']
      },
      {
        id: 'stock',
        title: 'Inventario',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory',
        icon: 'database',
        breadcrumbs: true,
        permissions: ['view_inventory']
      },
      {
        id: 'brands',
        title: 'Marcas',
        type: 'item',
        classes: 'nav-item',
        url: '/brands',
        icon: 'tags',
        breadcrumbs: true,
        permissions: ['view_products']
      },
      {
        id: 'units-of-measure',
        title: 'Unidades de Medida',
        type: 'item',
        classes: 'nav-item',
        url: '/units-of-measure',
        icon: 'column-width',
        breadcrumbs: true,
        permissions: ['view_products']
      }
    ]
  },
  {
    id: 'purchasing',
    title: 'Compras',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['manage_inventory'],
    children: [
      {
        id: 'suppliers',
        title: 'Proveedores',
        type: 'item',
        classes: 'nav-item',
        url: '/purchasing/suppliers',
        icon: 'team',
        breadcrumbs: false,
        permissions: ['manage_inventory']
      },
      {
        id: 'orders',
        title: 'Órdenes de Compra',
        type: 'item',
        classes: 'nav-item',
        url: '/purchasing/orders',
        icon: 'file-text',
        breadcrumbs: false,
        permissions: ['manage_inventory']
      },
      {
        id: 'pricelists',
        title: 'Listas de Precios',
        type: 'item',
        classes: 'nav-item',
        url: '/purchasing/pricelists',
        icon: 'tags',
        breadcrumbs: false,
        permissions: ['manage_inventory']
      }
    ]
  },
  {
    id: 'sales',
    title: 'Ventas',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['pos_access'],
    children: [
      {
        id: 'pos',
        title: 'Punto de Venta',
        type: 'item',
        classes: 'nav-item',
        url: '/pos',
        icon: 'calculator',
        breadcrumbs: false,
        permissions: ['pos_access']
      },
      {
        id: 'sales-list',
        title: 'Pedidos / Cotizaciones',
        type: 'item',
        classes: 'nav-item',
        url: '/sales',
        icon: 'solution',
        permissions: ['view_sales']
      },
      {
        id: 'first-sale-wizard',
        title: 'Wizard Primera Venta',
        type: 'item',
        classes: 'nav-item',
        url: '/sales/first-sale-wizard',
        icon: 'rocket',
        permissions: ['manage_company']
      }
    ]
  },
  {
    id: 'reports',
    title: 'Reportes',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['view_reports'],
    children: [
      {
        id: 'sales-report',
        title: 'Ranking & Ventas',
        type: 'item',
        classes: 'nav-item',
        url: '/reports',
        icon: 'bar-chart',
        breadcrumbs: false,
        permissions: ['view_reports']
      }
    ]
  },
  {
    id: 'management',
    title: 'Gestión',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'clients',
        title: 'Clientes',
        type: 'item',
        classes: 'nav-item',
        url: '/clients',
        icon: 'user',
        breadcrumbs: false,
        permissions: ['view_clients']
      },
      {
        id: 'users',
        title: 'Usuarios',
        type: 'item',
        classes: 'nav-item',
        url: '/users',
        icon: 'team',
        breadcrumbs: false,
        permissions: ['manage_users']
      },
      {
        id: 'company-profile',
        title: 'Mi Empresa',
        type: 'item',
        classes: 'nav-item',
        url: '/company/profile',
        icon: 'shop',
        breadcrumbs: false,
        permissions: ['manage_company']
      },
      {
        id: 'audit',
        title: 'Audit Logs',
        type: 'item',
        classes: 'nav-item',
        url: '/audit',
        icon: 'audit',
        breadcrumbs: false,
        permissions: ['view_reports']
      },
      {
        id: 'branches',
        title: 'Sucursales',
        type: 'item',
        classes: 'nav-item',
        url: '/branches',
        icon: 'bank',
        breadcrumbs: false,
        permissions: ['manage_settings']
      }
    ]
  }
];
