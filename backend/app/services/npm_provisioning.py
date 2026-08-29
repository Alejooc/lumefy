"""Idempotent Nginx Proxy Manager provisioning for verified storefront domains."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import settings


@dataclass(frozen=True)
class NpmProvisioningResult:
    proxy_host_id: int
    certificate_id: int


class NpmApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class NginxProxyManagerClient:
    """Small API client scoped to the operations Lumefy needs from NPM."""

    def __init__(
        self,
        *,
        api_url: str,
        identity: str,
        password: str,
        forward_scheme: str,
        forward_host: str,
        forward_port: int,
        timeout_seconds: int = 30,
        certificate_timeout_seconds: int = 900,
        verify_ssl: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.identity = identity
        self.password = password
        self.forward_scheme = forward_scheme
        self.forward_host = forward_host
        self.forward_port = forward_port
        self.timeout_seconds = timeout_seconds
        self.certificate_timeout_seconds = certificate_timeout_seconds
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    @classmethod
    def from_settings(cls) -> "NginxProxyManagerClient":
        if not settings.NPM_PROVISIONING_ENABLED:
            raise NpmApiError("El aprovisionamiento automático de NPM no está habilitado.", retryable=False)
        if not settings.NPM_API_URL or not settings.NPM_IDENTITY or not settings.NPM_PASSWORD:
            raise NpmApiError("Faltan credenciales de Nginx Proxy Manager.", retryable=False)
        return cls(
            api_url=settings.NPM_API_URL,
            identity=settings.NPM_IDENTITY,
            password=settings.NPM_PASSWORD,
            forward_scheme=settings.NPM_FORWARD_SCHEME,
            forward_host=settings.NPM_STOREFRONT_HOST,
            forward_port=settings.NPM_STOREFRONT_PORT,
            timeout_seconds=settings.NPM_REQUEST_TIMEOUT_SECONDS,
            certificate_timeout_seconds=settings.NPM_CERTIFICATE_TIMEOUT_SECONDS,
            verify_ssl=settings.NPM_VERIFY_SSL,
        )

    def _authenticate(self) -> None:
        try:
            response = self.session.request(
                "POST",
                f"{self.api_url}/tokens",
                json={"identity": self.identity, "secret": self.password},
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise NpmApiError("No fue posible conectar con Nginx Proxy Manager.", retryable=True) from exc
        if response.status_code != 200:
            raise self._error_from_response(response, "NPM rechazó las credenciales configuradas.")
        payload = self._response_json(response)
        token = payload.get("token") if isinstance(payload, dict) else None
        if not token:
            raise NpmApiError("NPM no devolvió un token de acceso.", retryable=False)
        self._token = str(token)
        expires = payload.get("expires") if isinstance(payload, dict) else None
        self._token_expires_at = self._parse_datetime(expires)

    def _ensure_token(self) -> None:
        if self._token and (
            self._token_expires_at is None
            or self._token_expires_at > datetime.now(timezone.utc)
        ):
            return
        self._authenticate()

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected_statuses: set[int] | None = None,
        timeout_seconds: int | None = None,
        retry_auth: bool = True,
    ) -> Any:
        self._ensure_token()
        try:
            response = self.session.request(
                method,
                f"{self.api_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=timeout_seconds or self.timeout_seconds,
                verify=self.verify_ssl,
            )
        except requests.RequestException as exc:
            raise NpmApiError("Nginx Proxy Manager no respondió.", retryable=True) from exc
        if response.status_code == 401 and retry_auth:
            self._token = None
            self._token_expires_at = None
            return self._request(
                method,
                path,
                payload=payload,
                expected_statuses=expected_statuses,
                timeout_seconds=timeout_seconds,
                retry_auth=False,
            )
        accepted = expected_statuses or {200}
        if response.status_code not in accepted:
            raise self._error_from_response(response, f"NPM devolvió HTTP {response.status_code}.")
        return self._response_json(response)

    def provision_domain(self, domain: str) -> NpmProvisioningResult:
        normalized = domain.strip().lower().rstrip(".")
        proxy_host = self._find_proxy_host(normalized)
        if proxy_host:
            self._assert_managed_proxy_host(proxy_host, normalized)
            # NPM only includes its shared ACME webroot location in a host
            # that already has a certificate. Disable an incomplete host so
            # the request falls through to NPM's default challenge server.
            if int(proxy_host.get("certificate_id") or 0) <= 0 and proxy_host.get("enabled", True):
                self._request(
                    "POST",
                    f"/nginx/proxy-hosts/{int(proxy_host['id'])}/disable",
                    expected_statuses={200},
                )

        reachability = self._request(
            "POST",
            "/nginx/certificates/test-http",
            payload={"domains": [normalized]},
        )
        result = reachability.get(normalized) if isinstance(reachability, dict) else None
        if str(result).lower() != "ok":
            detail = str(result or "sin respuesta")[:300]
            raise NpmApiError(
                f"El dominio todavía no llega por HTTP a NPM: {detail}",
                retryable=True,
            )

        if not proxy_host:
            proxy_host = self._create_proxy_host(normalized)
        proxy_host_id = int(proxy_host["id"])
        certificate_id = int(proxy_host.get("certificate_id") or 0)
        if certificate_id <= 0:
            certificate = self._find_certificate(normalized)
            if not certificate:
                certificate = self._request(
                    "POST",
                    "/nginx/certificates",
                    payload={
                        "provider": "letsencrypt",
                        "nice_name": f"Lumefy - {normalized}",
                        "domain_names": [normalized],
                        "meta": {"dns_challenge": False},
                    },
                    expected_statuses={201},
                    timeout_seconds=self.certificate_timeout_seconds,
                )
            certificate_id = int(certificate["id"])

        self._request(
            "PUT",
            f"/nginx/proxy-hosts/{proxy_host_id}",
            payload={
                "certificate_id": certificate_id,
                "ssl_forced": True,
                "http2_support": True,
                "allow_websocket_upgrade": True,
                "trust_forwarded_proto": True,
                "enabled": True,
            },
        )
        return NpmProvisioningResult(
            proxy_host_id=proxy_host_id,
            certificate_id=certificate_id,
        )

    def deprovision_domain(self, domain: str, proxy_host_id: int | None = None) -> None:
        normalized = domain.strip().lower().rstrip(".")
        host_id = proxy_host_id
        if host_id is None:
            proxy_host = self._find_proxy_host(normalized)
            if not proxy_host:
                return
            self._assert_managed_proxy_host(proxy_host, normalized)
            host_id = int(proxy_host["id"])
        try:
            self._request(
                "DELETE",
                f"/nginx/proxy-hosts/{host_id}",
                expected_statuses={200},
            )
        except NpmApiError as exc:
            if exc.status_code != 404:
                raise

    def _create_proxy_host(self, domain: str) -> dict[str, Any]:
        payload = {
            "domain_names": [domain],
            "forward_scheme": self.forward_scheme,
            "forward_host": self.forward_host,
            "forward_port": self.forward_port,
            "access_list_id": 0,
            "certificate_id": 0,
            "ssl_forced": False,
            "caching_enabled": False,
            "block_exploits": True,
            "advanced_config": "",
            "meta": {},
            "allow_websocket_upgrade": True,
            "http2_support": False,
            "hsts_enabled": False,
            "hsts_subdomains": False,
            "trust_forwarded_proto": True,
            "locations": [],
            "enabled": True,
        }
        return self._request(
            "POST",
            "/nginx/proxy-hosts",
            payload=payload,
            expected_statuses={201},
        )

    def _find_proxy_host(self, domain: str) -> dict[str, Any] | None:
        hosts = self._request("GET", "/nginx/proxy-hosts")
        for host in hosts if isinstance(hosts, list) else []:
            names = {str(item).strip().lower().rstrip(".") for item in host.get("domain_names") or []}
            if domain in names:
                return host
        return None

    def _find_certificate(self, domain: str) -> dict[str, Any] | None:
        certificates = self._request("GET", "/nginx/certificates")
        candidates = []
        for certificate in certificates if isinstance(certificates, list) else []:
            names = {str(item).strip().lower().rstrip(".") for item in certificate.get("domain_names") or []}
            if names == {domain} and certificate.get("provider") == "letsencrypt":
                candidates.append(certificate)
        return max(candidates, key=lambda item: int(item.get("id") or 0), default=None)

    def _assert_managed_proxy_host(self, proxy_host: dict[str, Any], domain: str) -> None:
        names = {str(item).strip().lower().rstrip(".") for item in proxy_host.get("domain_names") or []}
        target_matches = (
            proxy_host.get("forward_scheme") == self.forward_scheme
            and proxy_host.get("forward_host") == self.forward_host
            and int(proxy_host.get("forward_port") or 0) == self.forward_port
        )
        if names != {domain} or not target_matches:
            raise NpmApiError(
                "El dominio ya existe en un Proxy Host de NPM que Lumefy no puede administrar con seguridad.",
                retryable=False,
                status_code=409,
            )

    @staticmethod
    def _response_json(response: requests.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    @classmethod
    def _error_from_response(cls, response: requests.Response, fallback: str) -> NpmApiError:
        payload = cls._response_json(response)
        message = fallback
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = str(error["message"])
            elif payload.get("message"):
                message = str(payload["message"])
        elif isinstance(payload, str) and payload.strip():
            message = payload.strip()
        retry_after = response.headers.get("Retry-After")
        retry_after_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
        retryable = response.status_code in {408, 425, 429} or response.status_code >= 500
        return NpmApiError(
            message[:1000],
            retryable=retryable,
            status_code=response.status_code,
            retry_after_seconds=retry_after_seconds,
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
