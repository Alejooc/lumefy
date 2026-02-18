// angular import
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterModule } from '@angular/router';
import { Observable, Subject, forkJoin, fromEvent, merge, of } from 'rxjs';
import { catchError, filter, map, takeUntil } from 'rxjs/operators';
import { FormsModule } from '@angular/forms';
import { TourService, TourStep } from 'src/app/core/services/tour.service';

// project import
import { ApiService } from 'src/app/core/services/api.service';
import { AuthService } from 'src/app/core/services/auth.service';
import {
  DashboardCard,
  DashboardService,
  RecentOrder,
  TransactionHistory,
  ChartData
} from 'src/app/core/services/dashboard.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { MonthlyBarChartComponent } from 'src/app/theme/shared/apexchart/monthly-bar-chart/monthly-bar-chart.component';
import { IncomeOverviewChartComponent } from 'src/app/theme/shared/apexchart/income-overview-chart/income-overview-chart.component';
import { AnalyticsChartComponent } from 'src/app/theme/shared/apexchart/analytics-chart/analytics-chart.component';
import { SalesReportChartComponent } from 'src/app/theme/shared/apexchart/sales-report-chart/sales-report-chart.component';
import { CardComponent } from 'src/app/theme/shared/components/card/card.component';

// icons
import { IconService, IconDirective } from '@ant-design/icons-angular';
import { FallOutline, GiftOutline, MessageOutline, RiseOutline, SettingOutline } from '@ant-design/icons-angular/icons';

type StepAudience = 'superuser' | 'tenant';
type RouteOption = { route: string; permission?: string };
type OnboardingStep = {
  id: string;
  title: string;
  description: string;
  route: string;
  completed: boolean;
};
type OnboardingStepDefinition = {
  id: string;
  title: string;
  description: string;
  audience: StepAudience;
  routes: RouteOption[];
  autoCheck?: () => Observable<boolean>;
};

@Component({
  selector: 'app-default',
  imports: [
    CommonModule,
    RouterModule,
    CardComponent,
    IconDirective,
    MonthlyBarChartComponent,
    IncomeOverviewChartComponent,
    AnalyticsChartComponent,
    SalesReportChartComponent,
    FormsModule
  ],
  templateUrl: './default.component.html',
  styleUrls: ['./default.component.scss']
})
export class DefaultComponent implements OnInit, OnDestroy {
  private iconService = inject(IconService);
  private dashboardService = inject(DashboardService);
  private authService = inject(AuthService);
  private apiService = inject(ApiService);
  private permissionService = inject(PermissionService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  private tourService = inject(TourService);
  private destroy$ = new Subject<void>();

  AnalyticEcommerce: DashboardCard[] = [];
  recentOrder: RecentOrder[] = [];
  transaction: TransactionHistory[] = [];

  monthlySalesData: ChartData | null = null;
  incomeOverviewData: ChartData | null = null;
  salesReportData: ChartData | null = null;

  isLoading = true;
  errorMessage = '';
  onboardingSteps: OnboardingStep[] = [];
  onboardingCollapsed = false;
  showOnboardingAssistant = false;
  private onboardingAutoChecks: Record<string, () => Observable<boolean>> = {};

  // Filter properties
  dateFrom = '';
  dateTo = '';
  selectedBranchId = '';
  branches: any[] = [];

  constructor() {
    this.iconService.addIcon(...[RiseOutline, FallOutline, SettingOutline, GiftOutline, MessageOutline]);
  }

  get isSuperUser(): boolean {
    return !!this.authService.currentUserValue?.is_superuser;
  }

  ngOnInit() {
    this.showOnboardingAssistant =
      !!this.authService.currentUserValue?.is_superuser ||
      this.permissionService.hasAnyPermission(['manage_company', 'manage_users', 'manage_settings']);

    this.initializeOnboardingSteps();
    this.loadOnboardingProgress();
    this.loadOnboardingUiState();
    this.applyOnboardingAutoCompletion();
    this.setupOnboardingRefreshTriggers();

    this.loadBranches();
    this.loadDashboard();
  }

  loadBranches() {
    this.apiService.get<any[]>('/branches').subscribe({
      next: (data) => {
        this.branches = data;
        this.cdr.detectChanges();
      },
      error: () => { }
    });
  }

  loadDashboard() {
    this.isLoading = true;
    this.errorMessage = '';

    const filters: any = {};
    if (this.dateFrom) filters.date_from = this.dateFrom;
    if (this.dateTo) filters.date_to = this.dateTo;
    if (this.selectedBranchId) filters.branch_id = this.selectedBranchId;

    this.dashboardService.getStats(filters).subscribe({
      next: (stats) => {
        this.AnalyticEcommerce = stats.cards;
        this.recentOrder = stats.recent_orders;
        this.transaction = stats.transactions;
        this.monthlySalesData = stats.monthly_sales;
        this.incomeOverviewData = stats.income_overview;
        this.salesReportData = stats.sales_report;
        this.isLoading = false;
        this.cdr.detectChanges();
        this.checkAutoStartTour();
      },
      error: (error) => {
        console.error('Error fetching dashboard stats', error);
        this.errorMessage = 'Error cargando datos. Verifique que el servidor backend este funcionando.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  applyFilters() {
    this.loadDashboard();
  }

  clearFilters() {
    this.dateFrom = '';
    this.dateTo = '';
    this.selectedBranchId = '';
    this.loadDashboard();
  }

  startDashboardTour(): void {
    const steps: TourStep[] = [
      {
        target: '#dashboard-filters',
        title: '📅 Filtros del Dashboard',
        content: 'Filtra tus datos por rango de fecha y sucursal para analizar periodos específicos.',
        position: 'bottom'
      },
      {
        target: '#dashboard-kpis',
        title: '📊 Métricas Clave',
        content: 'Aquí verás los indicadores principales: ingresos totales, pedidos, usuarios activos y productos.',
        position: 'bottom'
      },
      {
        target: '#dashboard-recent-orders',
        title: '🛒 Pedidos Recientes',
        content: 'Los últimos pedidos aparecen aquí con su estado y monto para seguimiento rápido.',
        position: 'top'
      },
      {
        target: '#dashboard-charts',
        title: '📈 Gráficas de Rendimiento',
        content: 'Visualiza ingresos semanales, ventas mensuales y reportes de ventas en gráficas interactivas.',
        position: 'top'
      },
      {
        target: '.pc-sidebar',
        title: '📁 Navegación',
        content: 'Usa el menú lateral para acceder a Productos, Ventas, Inventario, Reportes y más. ¡Explora!',
        position: 'right'
      }
    ];
    this.tourService.startTour(steps);
  }

  private checkAutoStartTour(): void {
    if (!this.tourService.hasCompletedTour && !this.isLoading) {
      setTimeout(() => this.startDashboardTour(), 1500);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  get onboardingCompletedCount(): number {
    return this.onboardingSteps.filter((step) => step.completed).length;
  }

  get onboardingTotalCount(): number {
    return this.onboardingSteps.length;
  }

  get onboardingProgressPercent(): number {
    if (!this.onboardingTotalCount) {
      return 0;
    }
    return Math.round((this.onboardingCompletedCount / this.onboardingTotalCount) * 100);
  }

  toggleOnboardingStep(stepId: string): void {
    this.onboardingSteps = this.onboardingSteps.map((step) =>
      step.id === stepId ? { ...step, completed: !step.completed } : step
    );
    this.saveOnboardingProgress();
  }

  resetOnboardingProgress(): void {
    this.onboardingSteps = this.onboardingSteps.map((step) => ({ ...step, completed: false }));
    this.saveOnboardingProgress();
    this.applyOnboardingAutoCompletion();
  }

  toggleOnboardingCollapsed(): void {
    this.onboardingCollapsed = !this.onboardingCollapsed;
    localStorage.setItem(this.getOnboardingUiStorageKey(), JSON.stringify(this.onboardingCollapsed));
  }

  private initializeOnboardingSteps(): void {
    const isSuperuser = !!this.authService.currentUserValue?.is_superuser;
    const audience: StepAudience = isSuperuser ? 'superuser' : 'tenant';

    const definitions: OnboardingStepDefinition[] = [
      {
        id: 'saas-settings',
        title: 'Configurar plataforma SaaS',
        description: 'Ajusta branding global, politicas y parametros del sistema.',
        audience: 'superuser',
        routes: [{ route: '/admin/settings' }],
        autoCheck: () => this.endpointHasItems('/admin/settings')
      },
      {
        id: 'saas-plans',
        title: 'Definir planes comerciales',
        description: 'Crea planes y limites para los clientes de la plataforma.',
        audience: 'superuser',
        routes: [{ route: '/admin/plans' }],
        autoCheck: () => this.endpointHasItems('/plans/all')
      },
      {
        id: 'saas-companies',
        title: 'Registrar empresas cliente',
        description: 'Da de alta empresas y revisa su estado de suscripcion.',
        audience: 'superuser',
        routes: [{ route: '/admin/companies' }],
        autoCheck: () => this.endpointHasItems('/admin/companies')
      },
      {
        id: 'saas-kpis',
        title: 'Monitorear KPI SaaS',
        description: 'Controla crecimiento, actividad y salud de tu plataforma.',
        audience: 'superuser',
        routes: [{ route: '/admin/dashboard' }],
        autoCheck: () => this.endpointHasTruthyValue('/admin/stats', 'total_companies')
      },
      {
        id: 'company',
        title: 'Configurar empresa',
        description: 'Define sucursales, datos operativos y contexto de trabajo.',
        audience: 'tenant',
        routes: [
          { route: '/company/profile', permission: 'manage_company' },
          { route: '/branches', permission: 'manage_settings' },
          { route: '/users', permission: 'manage_users' }
        ],
        autoCheck: () => this.endpointHasTruthyValue('/companies/me', 'name')
      },
      {
        id: 'users',
        title: 'Crear usuarios y roles',
        description: 'Agrega tu equipo y asigna permisos por perfil.',
        audience: 'tenant',
        routes: [{ route: '/users', permission: 'manage_users' }],
        autoCheck: () => this.endpointHasItems('/users', 2)
      },
      {
        id: 'catalog',
        title: 'Cargar catalogo',
        description: 'Registra productos, categorias, marcas y unidades de medida.',
        audience: 'tenant',
        routes: [
          { route: '/products', permission: 'view_products' },
          { route: '/categories', permission: 'view_products' }
        ],
        autoCheck: () => this.endpointHasItems('/products')
      },
      {
        id: 'inventory',
        title: 'Inicializar inventario',
        description: 'Define stock inicial, minimos y movimientos de control.',
        audience: 'tenant',
        routes: [{ route: '/inventory', permission: 'view_inventory' }],
        autoCheck: () => this.endpointHasItems('/inventory')
      },
      {
        id: 'prices',
        title: 'Configurar precios',
        description: 'Crea listas de precio y condiciones comerciales.',
        audience: 'tenant',
        routes: [{ route: '/purchasing/pricelists', permission: 'manage_inventory' }],
        autoCheck: () => this.endpointHasItems('/pricelists')
      },
      {
        id: 'pos',
        title: 'Probar punto de venta',
        description: 'Realiza una venta de prueba para validar el flujo completo.',
        audience: 'tenant',
        routes: [
          { route: '/sales/first-sale-wizard', permission: 'create_sales' },
          { route: '/pos', permission: 'pos_access' },
          { route: '/sales', permission: 'view_sales' }
        ],
        autoCheck: () => this.endpointHasItems('/sales')
      }
    ];

    const visibleDefinitions = definitions
      .filter((definition) => definition.audience === audience)
      .map((definition) => {
        const route = this.findAllowedRoute(definition.routes);
        if (!route) {
          return null;
        }
        return { definition, route };
      })
      .filter((item): item is { definition: OnboardingStepDefinition; route: string } => item !== null);

    this.onboardingSteps = visibleDefinitions.map((item) => ({
      id: item.definition.id,
      title: item.definition.title,
      description: item.definition.description,
      route: item.route,
      completed: false
    }));

    this.onboardingAutoChecks = Object.fromEntries(
      visibleDefinitions
        .filter((item) => !!item.definition.autoCheck)
        .map((item) => [item.definition.id, item.definition.autoCheck!])
    );
  }

  private applyOnboardingAutoCompletion(): void {
    const checks = this.onboardingSteps
      .filter((step) => !!this.onboardingAutoChecks[step.id])
      .map((step) =>
        this.onboardingAutoChecks[step.id]().pipe(map((completed) => ({ id: step.id, completed })))
      );

    if (!checks.length) {
      return;
    }

    forkJoin(checks)
      .pipe(catchError(() => of([] as { id: string; completed: boolean }[])))
      .subscribe((results) => {
        if (!results.length) {
          return;
        }

        const resultMap = new Map(results.map((result) => [result.id, result.completed]));
        this.onboardingSteps = this.onboardingSteps.map((step) => ({
          ...step,
          completed: step.completed || !!resultMap.get(step.id)
        }));
        this.saveOnboardingProgress();
      });
  }

  private endpointHasItems(path: string, minItems = 1): Observable<boolean> {
    return this.apiService.get<any>(path).pipe(
      map((payload) => Array.isArray(payload) && payload.length >= minItems),
      catchError(() => of(false))
    );
  }

  private endpointHasTruthyValue(path: string, key: string): Observable<boolean> {
    return this.apiService.get<any>(path).pipe(
      map((payload) => !!payload && !!payload[key]),
      catchError(() => of(false))
    );
  }

  private findAllowedRoute(options: RouteOption[]): string | null {
    const isSuperuser = !!this.authService.currentUserValue?.is_superuser;
    if (isSuperuser) {
      return options[0]?.route ?? null;
    }
    const selected = options.find((option) => !option.permission || this.permissionService.hasPermission(option.permission));
    return selected?.route ?? null;
  }

  private loadOnboardingProgress(): void {
    try {
      const saved = localStorage.getItem(this.getOnboardingStorageKey());
      if (!saved) {
        return;
      }

      const completedIds = JSON.parse(saved) as string[];
      const completedSet = new Set(completedIds);
      this.onboardingSteps = this.onboardingSteps.map((step) => ({
        ...step,
        completed: completedSet.has(step.id)
      }));
    } catch (error) {
      console.error('Error loading onboarding progress', error);
    }
  }

  private saveOnboardingProgress(): void {
    const completedIds = this.onboardingSteps.filter((step) => step.completed).map((step) => step.id);
    localStorage.setItem(this.getOnboardingStorageKey(), JSON.stringify(completedIds));
  }

  private loadOnboardingUiState(): void {
    try {
      const saved = localStorage.getItem(this.getOnboardingUiStorageKey());
      if (!saved) {
        return;
      }
      this.onboardingCollapsed = JSON.parse(saved) === true;
    } catch {
      this.onboardingCollapsed = false;
    }
  }

  private getOnboardingStorageKey(): string {
    const user = this.authService.currentUserValue;
    const scope = user?.is_superuser ? 'superuser' : 'tenant';
    const userId = user?.id ?? 'anonymous';
    return `lumefy_onboarding_steps_v3_${scope}_${userId}`;
  }

  private getOnboardingUiStorageKey(): string {
    const user = this.authService.currentUserValue;
    const scope = user?.is_superuser ? 'superuser' : 'tenant';
    const userId = user?.id ?? 'anonymous';
    return `lumefy_onboarding_ui_v1_${scope}_${userId}`;
  }

  private setupOnboardingRefreshTriggers(): void {
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe(() => {
        this.refreshOnboardingState();
      });

    merge(
      fromEvent(window, 'focus'),
      fromEvent(document, 'visibilitychange').pipe(filter(() => document.visibilityState === 'visible'))
    )
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.applyOnboardingAutoCompletion();
      });
  }

  private refreshOnboardingState(): void {
    this.initializeOnboardingSteps();
    this.loadOnboardingProgress();
    this.applyOnboardingAutoCompletion();
    this.cdr.detectChanges();
  }
}
