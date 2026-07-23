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
  // ──────────────────── Dashboard ────────────────────
  {
    id: 'dashboard',
    title: 'Dashboard',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'default',
        title: 'Resumen',
        type: 'item',
        classes: 'nav-item',
        url: '/dashboard/default',
        icon: 'dashboard',
        breadcrumbs: false
      }
    ]
  },

  // ──────────────────── Super Admin ────────────────────
  {
    id: 'admin',
    title: 'Super Admin',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['manage_saas'],
    children: [
      {
        id: 'admin-dashboard',
        title: 'Resumen SaaS',
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
      },
      {
        id: 'landing-cms',
        title: 'Landing pública',
        type: 'item',
        url: '/admin/landing-cms',
        classes: 'nav-item',
        icon: 'layout'
      },
      {
        id: 'global-users',
        title: 'Usuarios Globales',
        type: 'item',
        url: '/admin/users',
        classes: 'nav-item',
        icon: 'team'
      },
      {
        id: 'system-health-admin',
        title: 'Estado del sistema',
        type: 'item',
        url: '/settings/health',
        classes: 'nav-item',
        icon: 'safety-certificate'
      },
      {
        id: 'database-stats',
        title: 'Base de datos',
        type: 'item',
        url: '/settings/database',
        classes: 'nav-item',
        icon: 'database'
      },
      {
        id: 'notifications-admin',
        title: 'Notificaciones',
        type: 'collapse',
        icon: 'bell',
        children: [
          {
            id: 'templates',
            title: 'Plantillas',
            type: 'item',
            url: '/admin/notifications/templates'
          },
          {
            id: 'send-manual',
            title: 'Envío Manual',
            type: 'item',
            url: '/admin/notifications/send'
          }
        ]
      }
    ]
  },

  // ──────────────────── Catálogo (product master data) ────────────────────
  {
    id: 'catalog',
    title: 'Catálogo',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['view_products'],
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
        id: 'catalog-configuration',
        title: 'Configuración de catálogo',
        type: 'collapse',
        icon: 'setting',
        permissions: ['manage_inventory'],
        children: [
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
            title: 'Unidades de medida',
            type: 'item',
            classes: 'nav-item',
            url: '/units-of-measure',
            icon: 'column-width',
            breadcrumbs: true,
            permissions: ['view_products']
          }
        ]
      }
    ]
  },

  // ──────────────────── Inventario (warehouse operations) ────────────────────
  {
    id: 'inventory',
    title: 'Inventario',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['view_inventory'],
    children: [
      {
        id: 'stock',
        title: 'Stock',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory',
        icon: 'database',
        breadcrumbs: true,
        permissions: ['view_inventory']
      },
      {
        id: 'inventory-lots',
        title: 'Lotes y Seriales',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory/lots',
        icon: 'barcode',
        breadcrumbs: true,
        permissions: ['view_inventory']
      },
      {
        id: 'inventory-warehouses',
        title: 'Bodegas',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory/warehouses',
        icon: 'home',
        breadcrumbs: true,
        permissions: ['manage_inventory']
      },
      {
        id: 'stock-take',
        title: 'Toma de Inventario',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory/stock-take',
        icon: 'file-search',
        breadcrumbs: true,
        permissions: ['manage_inventory']
      }
    ]
  },

  // ──────────────────── Compras ────────────────────
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
        id: 'purchase-requests',
        title: 'Solicitudes y Cotizaciones',
        type: 'item',
        classes: 'nav-item',
        url: '/purchasing/requests',
        icon: 'clipboard-list',
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

  // ──────────────────── Ventas ────────────────────
  {
    id: 'manufacturing', title: 'Producción', type: 'group', icon: 'icon-navigation', permissions: ['manage_inventory'], children: [
      { id: 'manufacturing-orders', title: 'Fabricación', type: 'item', classes: 'nav-item', url: '/manufacturing', icon: 'tool', breadcrumbs: false, permissions: ['manage_inventory'] }
    ]
  },

  // ──────────────────── Ventas ────────────────────
  {
    id: 'sales',
    title: 'Ventas',
    type: 'group',
    icon: 'icon-navigation',
    // A sales representative may manage orders without operating the POS.
    // Groups use "any" permission, so include every capability exposed below.
    permissions: ['pos_access', 'view_sales', 'manage_sales', 'manage_inventory'],
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
        id: 'returns-list',
        title: 'Devoluciones',
        type: 'item',
        classes: 'nav-item',
        url: '/returns',
        icon: 'rollback',
        permissions: ['manage_sales']
      },
      {
        id: 'invoices',
        title: 'Facturas y Cartera',
        type: 'item',
        classes: 'nav-item',
        url: '/invoices',
        icon: 'file-invoice',
        permissions: ['manage_sales', 'manage_inventory']
      },
    ]
  },

  // ──────────────────── Logística (fulfillment) ────────────────────
  {
    id: 'logistics',
    title: 'Logística',
    type: 'group',
    icon: 'icon-navigation',
    permissions: ['view_sales'],
    children: [
      {
        id: 'logistics-board',
        title: 'Tablero Fulfillment',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory/logistics-board',
        icon: 'layout',
        breadcrumbs: true,
        permissions: ['view_sales']
      },
      {
        id: 'picking',
        title: 'Picking',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory/picking',
        icon: 'carry-out',
        breadcrumbs: true,
        permissions: ['manage_sales']
      },
      {
        id: 'package-types',
        title: 'Tipos de Empaque',
        type: 'item',
        classes: 'nav-item',
        url: '/logistics/package-types',
        icon: 'container',
        breadcrumbs: true,
        permissions: ['manage_sales']
      }
    ]
  },

  // ──────────────────── Reportes ────────────────────
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

  // ──────────────────── Canales de venta ────────────────────
  {
    id: 'sales-channels',
    title: 'Canales de venta',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'apps-ecommerce',
        title: 'Comercio electrónico',
        type: 'collapse',
        icon: 'shop',
        url: '/commerce',
        permissions: ['manage_company'],
        children: [
          { id: 'commerce-overview', title: 'Resumen', type: 'item', classes: 'nav-item', url: '/commerce', icon: 'dashboard', breadcrumbs: false, permissions: ['manage_company'] },
          { id: 'commerce-store', title: 'Tienda', type: 'item', classes: 'nav-item', url: '/commerce/store', icon: 'shop', breadcrumbs: false, permissions: ['manage_company'] },
          { id: 'commerce-catalog', title: 'Catálogo publicado', type: 'item', classes: 'nav-item', url: '/products', icon: 'shopping-cart', breadcrumbs: false, permissions: ['view_products'] },
          { id: 'commerce-collections', title: 'Colecciones', type: 'item', classes: 'nav-item', url: '/commerce/collections', icon: 'tags', breadcrumbs: false, permissions: ['manage_company'] },
          { id: 'commerce-content', title: 'Contenido', type: 'collapse', icon: 'layout', permissions: ['manage_company'], children: [
            { id: 'commerce-branding', title: 'Marca', type: 'item', url: '/commerce/branding', breadcrumbs: false, permissions: ['manage_company'] },
            { id: 'commerce-design', title: 'Inicio y banners', type: 'item', url: '/commerce/design', breadcrumbs: false, permissions: ['manage_company'] },
            { id: 'commerce-menu', title: 'Menú de tienda', type: 'item', url: '/commerce/navigation', breadcrumbs: false, permissions: ['manage_company'] },
            { id: 'commerce-seo', title: 'SEO', type: 'item', url: '/commerce/seo', breadcrumbs: false, permissions: ['manage_company'] }
          ]},
          { id: 'commerce-checkout', title: 'Checkout y pagos', type: 'collapse', icon: 'credit-card', permissions: ['manage_company'], children: [
            { id: 'commerce-checkout-rules', title: 'Reglas de checkout', type: 'item', url: '/commerce/checkout', breadcrumbs: false, permissions: ['manage_company'] },
            { id: 'commerce-payments', title: 'Métodos de pago', type: 'item', url: '/commerce/payments', breadcrumbs: false, permissions: ['manage_company'] }
          ]},
          { id: 'commerce-orders', title: 'Pedidos online', type: 'item', classes: 'nav-item', url: '/sales', icon: 'solution', breadcrumbs: false, permissions: ['view_sales'] },
          { id: 'commerce-fulfillment', title: 'Preparación y envío', type: 'item', classes: 'nav-item', url: '/inventory/logistics-board', icon: 'carry-out', breadcrumbs: false, permissions: ['manage_sales'] }
        ]
      }
    ]
  },

  // ──────────────────── Tienda de Apps ────────────────────
  {
    id: 'apps-platform',
    title: 'Tienda de Apps',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'apps-store',
        title: 'Marketplace',
        type: 'item',
        classes: 'nav-item',
        url: '/apps/store',
        icon: 'appstore',
        breadcrumbs: false,
        permissions: ['manage_company']
      },
      {
        id: 'apps-installed',
        title: 'Apps Instaladas',
        type: 'collapse',
        icon: 'appstore',
        children: []
      },
      {
        id: 'apps-admin-catalog',
        title: 'Catálogo global',
        type: 'item',
        classes: 'nav-item',
        url: '/apps/admin',
        icon: 'setting',
        breadcrumbs: false,
        permissions: ['manage_saas']
      }
    ]
  },

  // ──────────────────── Gestión ────────────────────
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
        id: 'crm',
        title: 'CRM comercial',
        type: 'item',
        classes: 'nav-item',
        url: '/crm',
        icon: 'chart-line',
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
        id: 'roles',
        title: 'Roles y Permisos',
        type: 'item',
        classes: 'nav-item',
        url: '/users/roles',
        icon: 'safety-certificate',
        breadcrumbs: false,
        permissions: ['manage_company']
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
        id: 'branches',
        title: 'Sucursales',
        type: 'item',
        classes: 'nav-item',
        url: '/branches',
        icon: 'bank',
        breadcrumbs: false,
        permissions: ['manage_settings']
      },
      {
        id: 'audit',
        title: 'Auditoría',
        type: 'item',
        classes: 'nav-item',
        url: '/audit',
        icon: 'audit',
        breadcrumbs: false,
        permissions: ['view_reports']
      }
    ]
  }
];
