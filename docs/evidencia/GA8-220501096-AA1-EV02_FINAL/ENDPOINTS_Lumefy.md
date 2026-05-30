# Endpoints API Lumefy

Base URL sugerida: `http://localhost:8000`

Prefijo API: `/api/v1`

Autenticacion:
- Primero consume `POST /api/v1/login/access-token`.
- Copia el `access_token` en la variable `access_token` de Postman.

Total de paths detectados: `173`

## Admin/Companies

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/admin/companies` | Read Companies | Si |
| `POST` | `/api/v1/admin/companies` | Create Company | Si |
| `PUT` | `/api/v1/admin/companies/{id}` | Update Company | Si |

## Admin/Notifications

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/admin/notifications/send` | Send Manual Notification | Si |
| `GET` | `/api/v1/admin/notifications/templates` | Read Templates | Si |
| `POST` | `/api/v1/admin/notifications/templates` | Create Template | Si |
| `PUT` | `/api/v1/admin/notifications/templates/{id}` | Update Template | Si |

## Admin/Settings

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/admin/settings` | Read Settings | Si |
| `PUT` | `/api/v1/admin/settings/bulk` | Update Settings Bulk | Si |
| `GET` | `/api/v1/admin/settings/public` | Read Public Settings | No |

## Admin/Stats

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/admin/stats` | Read Admin Stats | Si |

## Admin/Users

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/admin/users` | Read Users | Si |
| `POST` | `/api/v1/admin/users/impersonate-company/{company_id}` | Impersonate Company | Si |
| `POST` | `/api/v1/admin/users/{user_id}/impersonate` | Impersonate User | Si |

## Apps

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/apps/admin/catalog` | Admin List Catalog | Si |
| `POST` | `/api/v1/apps/admin/catalog` | Admin Create App | Si |
| `PUT` | `/api/v1/apps/admin/catalog/{slug}` | Admin Update App | Si |
| `GET` | `/api/v1/apps/catalog` | List Catalog | Si |
| `PUT` | `/api/v1/apps/config/{slug}` | Update App Config | Si |
| `GET` | `/api/v1/apps/demo/hello` | Run Demo Hello | Si |
| `POST` | `/api/v1/apps/install/{slug}` | Install App | Si |
| `GET` | `/api/v1/apps/installed` | List Installed | Si |
| `GET` | `/api/v1/apps/installed/{slug}` | Get Installed Detail | Si |
| `GET` | `/api/v1/apps/installed/{slug}/billing` | Get Billing Summary | Si |
| `GET` | `/api/v1/apps/installed/{slug}/events` | Get Installed Events | Si |
| `POST` | `/api/v1/apps/installed/{slug}/rotate-api-key` | Rotate Api Key | Si |
| `POST` | `/api/v1/apps/installed/{slug}/rotate-client-secret` | Rotate Client Secret | Si |
| `POST` | `/api/v1/apps/installed/{slug}/rotate-webhook-secret` | Rotate Webhook Secret | Si |
| `GET` | `/api/v1/apps/installed/{slug}/webhooks/deliveries` | Get Webhook Deliveries | Si |
| `POST` | `/api/v1/apps/installed/{slug}/webhooks/deliveries/{delivery_id}/retry` | Retry Webhook Delivery | Si |
| `POST` | `/api/v1/apps/installed/{slug}/webhooks/test` | Send Test Webhook | Si |
| `POST` | `/api/v1/apps/uninstall/{slug}` | Uninstall App | Si |

## Audit

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/audit/` | Read Audit Logs | Si |

## Branches

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/branches/` | Read Branches | Si |
| `POST` | `/api/v1/branches/` | Create Branch | Si |
| `PUT` | `/api/v1/branches/{id}` | Update Branch | Si |
| `DELETE` | `/api/v1/branches/{id}` | Delete Branch | Si |

## Brands

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/brands/` | List Brands | Si |
| `POST` | `/api/v1/brands/` | Create Brand | Si |
| `PUT` | `/api/v1/brands/{brand_id}` | Update Brand | Si |
| `DELETE` | `/api/v1/brands/{brand_id}` | Delete Brand | Si |

## Categories

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/categories/` | Read Categories | Si |
| `POST` | `/api/v1/categories/` | Create Category | Si |
| `GET` | `/api/v1/categories/{category_id}` | Read Category | Si |
| `PUT` | `/api/v1/categories/{category_id}` | Update Category | Si |
| `DELETE` | `/api/v1/categories/{category_id}` | Delete Category | Si |

## Clients

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/clients/` | Read Clients | Si |
| `POST` | `/api/v1/clients/` | Create Client | Si |
| `GET` | `/api/v1/clients/export` | Export Clients | Si |
| `GET` | `/api/v1/clients/{client_id}` | Read Client | Si |
| `PUT` | `/api/v1/clients/{client_id}` | Update Client | Si |
| `DELETE` | `/api/v1/clients/{client_id}` | Delete Client | Si |
| `GET` | `/api/v1/clients/{client_id}/activities` | Get Client Activities | Si |
| `POST` | `/api/v1/clients/{client_id}/activities` | Create Client Activity | Si |
| `POST` | `/api/v1/clients/{client_id}/payments` | Register Client Payment | Si |
| `GET` | `/api/v1/clients/{client_id}/sales` | Get Client Sales | Si |
| `GET` | `/api/v1/clients/{client_id}/statement` | Get Client Statement | Si |
| `GET` | `/api/v1/clients/{client_id}/stats` | Get Client Stats | Si |
| `GET` | `/api/v1/clients/{client_id}/timeline` | Get Client Timeline | Si |

## Companies

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/companies/me` | Read Current Company | Si |
| `PUT` | `/api/v1/companies/me` | Update Current Company | Si |

## Dashboard

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/dashboard/` | Get Dashboard Stats | Si |
| `GET` | `/api/v1/dashboard/health` | Get Dashboard Health | Si |

## Inventory

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/inventory/` | Read Inventory | Si |
| `GET` | `/api/v1/inventory/export` | Export Inventory | Si |
| `POST` | `/api/v1/inventory/movement` | Create Movement | Si |
| `GET` | `/api/v1/inventory/movements` | Read Movements | Si |

## Login

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/login/access-token` | Login Access Token | No |

## Logistics

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/logistics/board` | Get Logistics Board | Si |
| `POST` | `/api/v1/logistics/board/move` | Move Sale Stage | Si |
| `GET` | `/api/v1/logistics/package-types` | Read Package Types | Si |
| `POST` | `/api/v1/logistics/package-types` | Create Package Type | Si |
| `PUT` | `/api/v1/logistics/package-types/{id}` | Update Package Type | Si |
| `DELETE` | `/api/v1/logistics/package-types/{id}` | Delete Package Type | Si |
| `POST` | `/api/v1/logistics/packages` | Create Package | Si |
| `GET` | `/api/v1/logistics/packages/{sale_id}` | Read Sale Packages | Si |
| `POST` | `/api/v1/logistics/picking/update-item` | Update Picking Item | Si |

## Notifications

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/notifications/` | Read Notifications | Si |
| `PUT` | `/api/v1/notifications/read-all` | Mark All Notifications Read | Si |
| `GET` | `/api/v1/notifications/unread` | Read Unread Notifications | Si |
| `PUT` | `/api/v1/notifications/{id}/read` | Mark Notification Read | Si |

## Password Recovery

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/password-recovery/{email}` | Recover Password | No |

## Plans

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/plans/` | Read Plans | No |
| `POST` | `/api/v1/plans/` | Create Plan | Si |
| `GET` | `/api/v1/plans/all` | Read All Plans | Si |
| `PUT` | `/api/v1/plans/{id}` | Update Plan | Si |

## Pos

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/pos/checkout` | Pos Checkout | Si |
| `GET` | `/api/v1/pos/config` | Get Pos Config | Si |
| `GET` | `/api/v1/pos/products` | Get Pos Products | Si |
| `POST` | `/api/v1/pos/sales/{sale_id}/void` | Void Pos Sale | Si |
| `GET` | `/api/v1/pos/sessions` | List Pos Sessions | Si |
| `GET` | `/api/v1/pos/sessions/current` | Get Current Pos Session | Si |
| `POST` | `/api/v1/pos/sessions/open` | Open Pos Session | Si |
| `POST` | `/api/v1/pos/sessions/{session_id}/close` | Close Pos Session | Si |
| `POST` | `/api/v1/pos/sessions/{session_id}/reopen` | Reopen Pos Session | Si |
| `GET` | `/api/v1/pos/sessions/{session_id}/stats` | Get Pos Session Stats | Si |

## Pricelists

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/pricelists/` | Read Pricelists | Si |
| `POST` | `/api/v1/pricelists/` | Create Pricelist | Si |
| `GET` | `/api/v1/pricelists/{id}` | Read Pricelist | Si |
| `PUT` | `/api/v1/pricelists/{id}` | Update Pricelist | Si |
| `DELETE` | `/api/v1/pricelists/{id}` | Delete Pricelist | Si |
| `POST` | `/api/v1/pricelists/{id}/items` | Add Pricelist Item | Si |

## Products

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/products/` | Read Products | Si |
| `POST` | `/api/v1/products/` | Create Product | Si |
| `GET` | `/api/v1/products/export` | Export Products | Si |
| `POST` | `/api/v1/products/import` | Import Products | Si |
| `GET` | `/api/v1/products/{product_id}` | Read Product | Si |
| `PUT` | `/api/v1/products/{product_id}` | Update Product | Si |
| `DELETE` | `/api/v1/products/{product_id}` | Delete Product | Si |
| `POST` | `/api/v1/products/{product_id}/variants` | Add Variant | Si |
| `PUT` | `/api/v1/products/{product_id}/variants/{variant_id}` | Update Variant | Si |
| `DELETE` | `/api/v1/products/{product_id}/variants/{variant_id}` | Delete Variant | Si |

## Purchases

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/purchases/` | Read Purchases | Si |
| `POST` | `/api/v1/purchases/` | Create Purchase | Si |
| `GET` | `/api/v1/purchases/export` | Export Purchases | Si |
| `GET` | `/api/v1/purchases/{purchase_id}` | Read Purchase | Si |
| `PUT` | `/api/v1/purchases/{purchase_id}` | Update Purchase | Si |
| `DELETE` | `/api/v1/purchases/{purchase_id}` | Delete Purchase | Si |
| `GET` | `/api/v1/purchases/{purchase_id}/pdf/order` | Download Pdf | Si |
| `POST` | `/api/v1/purchases/{purchase_id}/receive` | Receive Purchase | Si |
| `PUT` | `/api/v1/purchases/{purchase_id}/status` | Update Purchase Status | Si |

## Register

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/register` | Register | No |

## Reports

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/reports/daily-close` | Get Daily Close Summary | Si |
| `GET` | `/api/v1/reports/financial-summary` | Get Financial Summary | Si |
| `GET` | `/api/v1/reports/inventory-turnover` | Get Inventory Turnover | Si |
| `GET` | `/api/v1/reports/inventory-value` | Get Inventory Value | Si |
| `GET` | `/api/v1/reports/pos-operations` | Get Pos Operations Summary | Si |
| `GET` | `/api/v1/reports/sales-by-category` | Get Sales By Category | Si |
| `GET` | `/api/v1/reports/sales-summary` | Get Sales Summary | Si |
| `GET` | `/api/v1/reports/top-products` | Get Top Products | Si |

## Reset Password

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/reset-password` | Reset Password | No |

## Returns

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/returns` | List Returns | Si |
| `POST` | `/api/v1/returns` | Create Return | Si |
| `GET` | `/api/v1/returns/{return_id}` | Get Return | Si |
| `POST` | `/api/v1/returns/{return_id}/approve` | Approve Return | Si |
| `POST` | `/api/v1/returns/{return_id}/reject` | Reject Return | Si |

## Roles

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/roles/` | Read Roles | Si |
| `POST` | `/api/v1/roles/` | Create Role | Si |
| `GET` | `/api/v1/roles/{role_id}` | Read Role | Si |
| `PUT` | `/api/v1/roles/{role_id}` | Update Role | Si |
| `DELETE` | `/api/v1/roles/{role_id}` | Delete Role | Si |

## Sales

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/sales/` | Read Sales | Si |
| `POST` | `/api/v1/sales/` | Create Sale | Si |
| `GET` | `/api/v1/sales/export` | Export Sales | Si |
| `GET` | `/api/v1/sales/{id}` | Read Sale | Si |
| `DELETE` | `/api/v1/sales/{id}` | Delete Sale | Si |
| `GET` | `/api/v1/sales/{id}/pdf/{doc_type}` | Download Pdf | Si |
| `PUT` | `/api/v1/sales/{id}/status` | Update Status | Si |
| `POST` | `/api/v1/sales/{sale_id}/complete` | Complete Sale | Si |
| `POST` | `/api/v1/sales/{sale_id}/deliver` | Confirm Delivery | Si |

## Search

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/search` | Global Search | Si |

## Stock Take

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/stock-take/` | List Stock Takes | Si |
| `POST` | `/api/v1/stock-take/` | Create Stock Take | Si |
| `GET` | `/api/v1/stock-take/{stock_take_id}` | Get Stock Take | Si |
| `POST` | `/api/v1/stock-take/{stock_take_id}/apply` | Apply Stock Take | Si |
| `POST` | `/api/v1/stock-take/{stock_take_id}/cancel` | Cancel Stock Take | Si |
| `PUT` | `/api/v1/stock-take/{stock_take_id}/count` | Update Counts | Si |

## Storefront

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/storefront/` | Read Storefronts | Si |
| `POST` | `/api/v1/storefront/` | Create Storefront | Si |
| `GET` | `/api/v1/storefront/collections` | Read Collections | Si |
| `POST` | `/api/v1/storefront/collections` | Create Collection | Si |
| `PUT` | `/api/v1/storefront/collections/{collection_id}` | Update Collection | Si |
| `GET` | `/api/v1/storefront/collections/{collection_id}/products` | Read Collection Products | Si |
| `POST` | `/api/v1/storefront/collections/{collection_id}/products` | Add Product To Collection | Si |
| `DELETE` | `/api/v1/storefront/collections/{collection_id}/products/{published_product_id}` | Remove Product From Collection | Si |
| `GET` | `/api/v1/storefront/domains` | Read Storefront Domains | Si |
| `POST` | `/api/v1/storefront/domains` | Create Storefront Domain | Si |
| `PUT` | `/api/v1/storefront/domains/{domain_id}` | Update Storefront Domain | Si |
| `DELETE` | `/api/v1/storefront/domains/{domain_id}` | Delete Storefront Domain | Si |
| `GET` | `/api/v1/storefront/navigation` | Read Navigation | Si |
| `POST` | `/api/v1/storefront/navigation` | Create Navigation Item | Si |
| `PUT` | `/api/v1/storefront/navigation/{navigation_item_id}` | Update Navigation Item | Si |
| `DELETE` | `/api/v1/storefront/navigation/{navigation_item_id}` | Delete Navigation Item | Si |
| `GET` | `/api/v1/storefront/payment-gateways` | Read Payment Gateways | Si |
| `POST` | `/api/v1/storefront/payment-gateways` | Create Payment Gateway | Si |
| `PUT` | `/api/v1/storefront/payment-gateways/{gateway_id}` | Update Payment Gateway | Si |
| `GET` | `/api/v1/storefront/public/by-subdomain/{subdomain}` | Read Public Storefront By Subdomain | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}` | Read Public Storefront | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/account/me` | Read Public Storefront Account Me | Si |
| `GET` | `/api/v1/storefront/public/{storefront_id}/account/orders` | Read Public Storefront Account Orders | Si |
| `PUT` | `/api/v1/storefront/public/{storefront_id}/account/password` | Change Public Storefront Account Password | Si |
| `PUT` | `/api/v1/storefront/public/{storefront_id}/account/profile` | Update Public Storefront Account Profile | Si |
| `POST` | `/api/v1/storefront/public/{storefront_id}/auth/login` | Login Public Storefront Account | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/auth/password-recovery` | Recover Public Storefront Account Password | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/auth/register` | Register Public Storefront Account | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/auth/reset-password` | Reset Public Storefront Account Password | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/checkout/orders` | Create Public Checkout Order | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/checkout/payment-intent` | Create Public Payment Intent | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/checkout/payment-status` | Read Public Payment Status | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/checkout/preview` | Preview Public Checkout | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/collections` | Read Public Collections | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/collections/{slug}` | Read Public Collection Detail | No |
| `POST` | `/api/v1/storefront/public/{storefront_id}/contact` | Send Public Storefront Contact Message | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/navigation` | Read Public Navigation | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/payment-gateways` | Read Public Payment Gateways | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/products` | Read Public Products | No |
| `GET` | `/api/v1/storefront/public/{storefront_id}/products/{slug}` | Read Public Product Detail | No |
| `GET` | `/api/v1/storefront/published-products` | Read Published Products | Si |
| `POST` | `/api/v1/storefront/published-products` | Create Published Product | Si |
| `PUT` | `/api/v1/storefront/published-products/{published_product_id}` | Update Published Product | Si |
| `PUT` | `/api/v1/storefront/{storefront_id}` | Update Storefront | Si |

## Suppliers

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/suppliers/` | Read Suppliers | Si |
| `POST` | `/api/v1/suppliers/` | Create Supplier | Si |
| `PUT` | `/api/v1/suppliers/{supplier_id}` | Update Supplier | Si |
| `DELETE` | `/api/v1/suppliers/{supplier_id}` | Delete Supplier | Si |
| `POST` | `/api/v1/suppliers/{supplier_id}/payments` | Register Supplier Payment | Si |
| `GET` | `/api/v1/suppliers/{supplier_id}/statement` | Get Supplier Statement | Si |

## System

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/system/broadcast` | Get Broadcast Message | Si |
| `POST` | `/api/v1/system/broadcast` | Set Broadcast Message | Si |
| `GET` | `/api/v1/system/database-stats` | Get Database Stats | Si |
| `GET` | `/api/v1/system/health` | System Health | Si |
| `GET` | `/api/v1/system/landing` | Get Landing Config | No |
| `PUT` | `/api/v1/system/landing` | Update Landing Config | Si |
| `GET` | `/api/v1/system/maintenance` | Get Maintenance Status | Si |
| `POST` | `/api/v1/system/maintenance` | Set Maintenance Mode | Si |

## Units Of Measure

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/units-of-measure/` | List Units | Si |
| `POST` | `/api/v1/units-of-measure/` | Create Unit | Si |
| `PUT` | `/api/v1/units-of-measure/{unit_id}` | Update Unit | Si |
| `DELETE` | `/api/v1/units-of-measure/{unit_id}` | Delete Unit | Si |

## Upload

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `POST` | `/api/v1/upload/` | Upload File | Si |

## Users

| Metodo | Endpoint | Descripcion | Requiere token |
|---|---|---|---|
| `GET` | `/api/v1/users/` | Read Users | Si |
| `POST` | `/api/v1/users/` | Create User | Si |
| `GET` | `/api/v1/users/me` | Read User Me | Si |
| `GET` | `/api/v1/users/{user_id}` | Read User | Si |
| `PUT` | `/api/v1/users/{user_id}` | Update User | Si |
| `DELETE` | `/api/v1/users/{user_id}` | Delete User | Si |
| `POST` | `/api/v1/users/{user_id}/recovery-email` | Send Recovery Email | Si |
