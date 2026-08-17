import logging
import ssl
from typing import TYPE_CHECKING, Generator, Optional

from app.capif.invoker import capif_invoker
from app.settings import NEFAuthMode

import httpx
from pydantic import AnyHttpUrl, AnyUrl

if TYPE_CHECKING:
    from app.settings import NEFSettings

LOG = logging.getLogger(__name__)


class NEFJwtAuth(httpx.Auth):
    requires_response_body = True

    def __init__(
        self, nef_url: AnyHttpUrl, nef_username: str, nef_password: str
    ) -> None:
        self.nef_url = str(nef_url).rstrip("/")
        self.nef_username = nef_username
        self.nef_password = nef_password

        self.current_token: Optional[str] = None

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        token = self.current_token
        if token is None:
            res = yield self.build_login_request()
            token = self.update_token(res)

        request.headers["Authorization"] = token
        res = yield request

        if res.status_code == 401:
            res = yield self.build_login_request()
            token = self.update_token(res)

            request.headers["Authorization"] = token
            yield request

    def build_login_request(self) -> httpx.Request:
        LOG.debug("Building login request")
        return httpx.Request(
            method="POST",
            url=f"{self.nef_url}/api/v1/login/access-token",
            data={
                "username": self.nef_username,
                "password": self.nef_password,
            },
        )

    def update_token(self, res: httpx.Response) -> str:
        LOG.debug("Updating token from login response")

        if not res.is_success:
            LOG.error(
                "Login response is not successfull ({}): {}",
                res.status_code,
                res.content,
            )
            raise RuntimeError("Failed to login to NEF")

        token = f"Bearer {res.json()['access_token']}"
        self.current_token = token
        return token


class NEFCAPIFAuth(httpx.Auth):

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        from app.capif.deps import get_nef_capif_token

        request.headers["Authorization"] = f"Bearer {get_nef_capif_token()}"
        res = yield request

        if res.status_code == 401:
            request.headers["Authorization"] = f"Bearer {get_nef_capif_token(force_refresh=True)}"
            yield request

def _get_nef_base_url(nef_settings: "NEFSettings") -> str:
    if nef_settings.auth_mode == NEFAuthMode.CAPIF:
        return capif_invoker.get_base_url()
    return nef_settings.get_base_url()

def _get_nef_auth(nef_settings: "NEFSettings") -> httpx.Auth:
    if nef_settings.auth_mode == NEFAuthMode.CAPIF:
        return NEFCAPIFAuth()
    return NEFJwtAuth(nef_settings.url, nef_settings.username, nef_settings.password)

def _get_nef_ssl_context(nef_settings: "NEFSettings") -> ssl.SSLContext | bool:
    if nef_settings.auth_mode != NEFAuthMode.CAPIF:
        return False

    ssl_context = ssl.create_default_context(cafile=capif_invoker.invoker.pathca)
    ssl_context.load_cert_chain(
        certfile=capif_invoker.invoker.signed_key_crt_path,
        keyfile=capif_invoker.invoker.private_key_path,
    )
    ssl_context.check_hostname = False
    return ssl_context

def get_nef_httpx_client(nef_settings: "NEFSettings") -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_get_nef_base_url(nef_settings),
        auth=_get_nef_auth(nef_settings),
        verify=_get_nef_ssl_context(nef_settings)
    )

def resolve_nef_url(client: httpx.AsyncClient, url: AnyUrl | str) -> httpx.URL:
    """
    Re-target a NEF-provided absolute URL (e.g. a subscription `self` link) at the
    origin the gateway actually reaches NEF on.

    NEF builds `self` links from the request URL it observes (`f"{http_request.url}/{id}"`),
    and its reverse proxy forwards neither `Host` nor `X-Forwarded-*`. The resulting link
    therefore carries NEF's internal upstream host/port/scheme, which is not reachable from
    the gateway. The path is still correct (the proxy does not rewrite it), so only the
    origin is replaced. Where NEF is deployed so that its `self` links already point at the
    reachable origin, this is a no-op.
    """
    target = httpx.URL(str(url))
    base = client.base_url
    return target.copy_with(scheme=base.scheme, host=base.host, port=base.port)

def discover_nef_url(*, nef_settings: "NEFSettings", fallback: str, resource_name: str, api_name_filter: str, operation: str) -> str:
    """
    fallback url will be the returned url if CAPIF is not being used
    otherwise, the url will be discovered via CAPIF using the provided resource name and api name filter
    if the url cannot be discovered via CAPIF, the fallback url will be returned and an error will be logged
    """
    if nef_settings.auth_mode == NEFAuthMode.CAPIF:
        path = capif_invoker.get_service_relative_url(
            resource_name=resource_name,
            api_name_filter=api_name_filter,
            operation=operation,
        )
        if path is None:
            logging.error(
                "Path not found for resource '%s', api filter '%s', operation '%s'. Falling back to fallback url.",
                resource_name, api_name_filter, operation
            )
    return fallback
