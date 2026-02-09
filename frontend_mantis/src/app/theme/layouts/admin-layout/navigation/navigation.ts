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
    id: 'inventory',
    title: 'Catálogo',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'products',
        title: 'Productos',
        type: 'item',
        classes: 'nav-item',
        url: '/products',
        icon: 'shopping',
      },
      {
        id: 'categories',
        title: 'Categorías',
        type: 'item',
        classes: 'nav-item',
        url: '/categories',
        icon: 'gold',
        breadcrumbs: true
      },
      {
        id: 'stock',
        title: 'Inventario',
        type: 'item',
        classes: 'nav-item',
        url: '/inventory',
        icon: 'box',
        breadcrumbs: true
      }
    ]
  },
  {
    id: 'sales',
    title: 'Ventas',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'pos',
        title: 'Punto de Venta',
        type: 'item',
        classes: 'nav-item',
        url: '/pos',
        icon: 'calculator',
        breadcrumbs: false
      }
    ]
  },
  {
    id: 'reports',
    title: 'Reportes',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'sales-report',
        title: 'Ranking & Ventas',
        type: 'item',
        classes: 'nav-item',
        url: '/reports',
        icon: 'bar-chart',
        breadcrumbs: false
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
        icon: 'users',
        breadcrumbs: false
      },
      {
        id: 'users',
        title: 'Usuarios',
        type: 'item',
        classes: 'nav-item',
        url: '/users',
        icon: 'user',
        breadcrumbs: false
      }
    ]
  },
  {
    id: 'authentication',
    title: 'Authentication',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'login',
        title: 'Login',
        type: 'item',
        classes: 'nav-item',
        url: '/login',
        icon: 'login',
        target: true,
        breadcrumbs: false
      },
      {
        id: 'register',
        title: 'Register',
        type: 'item',
        classes: 'nav-item',
        url: '/register',
        icon: 'profile',
        target: true,
        breadcrumbs: false
      }
    ]
  },
  {
    id: 'utilities',
    title: 'UI Components',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'typography',
        title: 'Typography',
        type: 'item',
        classes: 'nav-item',
        url: '/typography',
        icon: 'font-size'
      },
      {
        id: 'color',
        title: 'Colors',
        type: 'item',
        classes: 'nav-item',
        url: '/color',
        icon: 'bg-colors'
      },
      {
        id: 'ant-icons',
        title: 'Ant Icons',
        type: 'item',
        classes: 'nav-item',
        url: 'https://ant.design/components/icon',
        icon: 'ant-design',
        target: true,
        external: true
      }
    ]
  },

  {
    id: 'other',
    title: 'Other',
    type: 'group',
    icon: 'icon-navigation',
    children: [
      {
        id: 'sample-page',
        title: 'Sample Page',
        type: 'item',
        url: '/sample-page',
        classes: 'nav-item',
        icon: 'chrome'
      },
      {
        id: 'document',
        title: 'Document',
        type: 'item',
        classes: 'nav-item',
        url: 'https://jacode.varyago.com/',
        icon: 'question',
        target: true,
        external: true
      }
    ]
  }
];
