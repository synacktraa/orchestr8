from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from ..logger import Logger
from .redirect_server import RedirectServer

__all__ = ("OAuthFlow",)


class OAuthFlow(Logger):
    """Base class for OAuth flow implementation.

    ```python
    class MyOAuthFlow(OAuthFlow):

        @property
        def auth_url(self) -> str:
            return (
                f"https://service.com/api/oauth2/authorize"
                f"?client_id={self.client_id}&redirect_uri={self.quoted_redirect_url}"
                f"&response_type=code&scope={self.user_scopes}"
            )

        def _generate_access_token(self, code: str) -> str:
            response = requests.post(
                "https://service.com/api/oauth2/token",
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': self.redirect_url,
                },
                auth=(self.client_id, self.client_secret)
            )

            if response.status_code != 200:
                raise Exception(f"Failed to obtain access token: {response.json()}")

            return response.json()['access_token']

    my_oauth_flow = MyOAuthFlow(
        client_id="<client-id>",
        client_secret="<client-secret>",
        user_scopes="identify messages.read",
    )
    my_oauth_flow.authorize(timeout=30)
    ```
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cdict = cls.__dict__
        if not (attr := cdict.get("auth_url", None)) or not isinstance(attr, property):
            raise TypeError(f"{cls.__name__} must define 'auth_url' property.")

        if not (attr := cdict.get("_generate_access_token", None)) or not callable(attr):
            raise TypeError(f"{cls.__name__} must define '_generate_access_token' method.")

    def __new__(cls, *args: Any, **kwargs: Any) -> OAuthFlow:
        if cls is OAuthFlow:
            raise TypeError("OAuthFlow cannot be instantiated directly")
        return super().__new__(cls)

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        user_scopes: str | None = None,
        redirect_port: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            client_id: Client ID
            client_secret: Client secret
            user_scopes: User scopes
            redirect_port: Port to redirect on. Default: `41539`
            kwargs: Additional keyword arguments
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_scopes = quote_plus(user_scopes or "")
        self.kwargs = kwargs

        self._redirect_server = RedirectServer(port=redirect_port)

    @property
    def redirect_url(self) -> str:
        """URL of locally hosted server."""
        if not self._redirect_server.is_running:
            self._redirect_server.start()
        return self._redirect_server.url

    @property
    def quoted_redirect_url(self) -> str:
        """Quoted redirect url"""
        return quote_plus(self.redirect_url)

    @property
    def auth_url(self) -> str:
        """Formatted authorization URL for getting code."""
        raise NotImplementedError("Property should be implemented by inherited class.")

    def _get_auth_code(self, *, timeout: int | None = None) -> str:
        """
        Get authorization code. If timeout is None, it blocks until a request is intercepted.

        Args:
            timeout: seconds to wait for. Default: `None`

        Returns:
            Authorization code
        """

        self.logger.info(
            "<w>Add this URL to your application's redirect settings:</w> <u><le>{}</le></u>", self.redirect_url
        )
        self.logger.info("<w>Click this URL to authorize:</w> <u><le>{}</le></u>", self.auth_url)

        if not (req_url := self._redirect_server.intercept(timeout=timeout)):
            raise TimeoutError(
                "No authorization request was intercepted. " "The request may have timed out or was never received."
            )

        if codes := parse_qs(urlparse(req_url).query).get("code"):
            return codes[0]

        raise ConnectionAbortedError("Authorization failed or was denied. Please try again.")

    def _generate_access_token(self, code: str) -> str:
        """
        Generate access token

        Args:
            code: Authorization code

        Returns:
            Access token
        """
        raise NotImplementedError("Method should be implemented by inherited class.")

    def authorize(self, *, timeout: int | None = None) -> str:
        """
        Authorize and return access token.

        Args:
            timeout: seconds to wait for. Default: `None`

        Returns:
            Access token
        """
        self.logger.info("Starting authorization process")
        code = self._get_auth_code(timeout=timeout)
        self.logger.success("Authorization code received")
        token = self._generate_access_token(code)
        self.logger.success("Access token generated successfully")
        return token

    def __del__(self) -> None:
        if self._redirect_server.is_running:
            self._redirect_server.stop()
