from __future__ import annotations

import ssl
import wsgiref.util as wsgi_util
from string import Template
from typing import Any, Callable, Dict, List
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .._paths import MKCERT_LOCALHOST_SSL_CERT_FILE, MKCERT_LOCALHOST_SSL_PKEY_FILE
from ..logger import Logger

__all__ = ("RedirectServer",)


AUTH_MESSAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔗 OAuth Flow</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Roboto', Arial, sans-serif;
            background-color: #c0daea;
            text-align: center;
            padding: 50px;
            margin: 0;
            line-height: 1.6;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            margin: 0 auto;
            transition: transform 0.3s ease;
        }
        .container:hover {
            transform: scale(1.02);
        }
        h1 {
            color: $color;
            margin-bottom: 20px;
            font-weight: 700;
        }
        p {
            font-size: 18px;
            color: #333;
            margin-bottom: 25px;
        }
        .status-icon {
            font-size: 64px;
            margin-bottom: 20px;
        }
        .success {
            color: #4CAF50;
        }
        .error {
            color: #F44336;
        }
        .details {
            background-color: #f1f1f1;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 14px;
            text-align: left;
        }
        @media (max-width: 600px) {
            body {
                padding: 20px;
            }
            .container {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Authorization $status!</h1>
        <img src="$gif_url" alt="Authorization $status gif">
        <p>$message</p>
    </div>
</body>
</html>""")

AUTH_SUCCESS_MESSAGE = AUTH_MESSAGE_TEMPLATE.safe_substitute(
    color="#4CAF50",
    status="Successful",
    gif_url="https://i.imgur.com/9s4H6fU.gif",
    message="You have successfully authorized the application. You may close this window.",
)

AUTH_ERROR_MESSAGE = AUTH_MESSAGE_TEMPLATE.safe_substitute(
    color="#f44336",
    status="Failed",
    gif_url="https://i.imgur.com/KML64O4.gif",
    message="Authorization was denied or failed. Please try again.",
)


class _WSGIRequestHandler(WSGIRequestHandler):
    """
    Custom WSGIRequestHandler.
    """

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # pylint: disable=redefined-builtin
        # (format is the argument name defined in the superclass.)
        return


class RedirectWSGIApp:
    """WSGI app to handle the authorization redirect."""

    def __init__(self, success_message: str, error_message: str) -> None:
        """
        Args:
            success_message: Message to display when successfully authorized.
            error_message: Message to display when request is denied or failed.
        """
        self.__last_request_url: str | None = None
        self._success_message = success_message.encode("utf-8")
        self._error_message = error_message.encode("utf-8")
        self._res_headers = [("Content-type", "text/html; charset=utf-8")]

    @property
    def last_request_url(self) -> str | None:
        """Last intercepted request URL."""
        return self.__last_request_url

    def __call__(self, environ: Dict[str, str], start_response: Callable[[str, list], None]) -> List[bytes]:
        """
        Call the app instance.

        Args:
            environ: The WSGI environment
            start_response: The WSGI start_response callable.
        Raises:
            List of messages to display
        """
        if "error" in parse_qs(environ.get("QUERY_STRING")):
            status_code, messages = "400 Bad Request", [self._error_message]
        else:
            status_code, messages = "200 OK", [self._success_message]

        self.__last_request_url = wsgi_util.request_uri(environ)
        start_response(status_code, self._res_headers)
        return messages


class RedirectServer(Logger):
    """
    Host a redirect server locally.

    ```python
    with RedirectServer(port=8080) as server:
        print(server.url) # https://localhost:8080/
        print(server.is_running) # True
        print(server.intercept(timeout=10)) # https://localhost:8080/?code=123456
    ```
    """

    def __init__(
        self, *, port: int | None = None, success_message: str | None = None, error_message: str | None = None
    ) -> None:
        """
        Args:
            port: Port to host on. Default: `41539`
            success_message: Message to display when successfully authorized.
            error_message: Message to display when request is denied or failed.
        """
        self.__instance: WSGIServer = None  # type: ignore[assignment]
        self.__host = "localhost"
        self.__port = port or 41539
        self.__app = RedirectWSGIApp(
            success_message=success_message or AUTH_SUCCESS_MESSAGE, error_message=error_message or AUTH_ERROR_MESSAGE
        )

    def __enter__(self) -> RedirectServer:
        self.start()
        return self

    def start(self) -> None:
        """Start the server."""
        if self.is_running:
            return

        if not MKCERT_LOCALHOST_SSL_CERT_FILE.is_file() or not MKCERT_LOCALHOST_SSL_PKEY_FILE.is_file():
            raise FileNotFoundError(
                "Certificate or Private key file not found.\n\n"
                "Run the following commands to generate it:\n"
                "mkcert -install # Skip if already done.\n"
                f'mkcert -cert-file "{MKCERT_LOCALHOST_SSL_CERT_FILE!s}" '
                f'-key-file "{MKCERT_LOCALHOST_SSL_PKEY_FILE!s}" localhost'
            )

        WSGIServer.allow_reuse_address = False
        server_instance = make_server(
            self.__host,
            self.__port,
            self.__app,  # type: ignore[arg-type]
            handler_class=_WSGIRequestHandler,
        )

        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.check_hostname = False
        sslctx.load_cert_chain(certfile=MKCERT_LOCALHOST_SSL_CERT_FILE, keyfile=MKCERT_LOCALHOST_SSL_PKEY_FILE)
        server_instance.socket = sslctx.wrap_socket(sock=server_instance.socket, server_side=True)
        self.__instance = server_instance
        self.logger.info(f"Redirect server started on <u>{self.__host}:{self.__port}</u>")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return bool(self.__instance)

    def raise_if_not_running(self) -> None:
        """Raise if server is not running."""
        if not self.is_running:
            raise RuntimeError("Server not running. use `.start()` method.")

    @property
    def url(self) -> str:
        """URL of locally hosted server."""
        self.raise_if_not_running()
        return f"https://{self.__host}:{self.__port}/"

    def intercept(self, *, timeout: int | None = None) -> str | None:
        """
        Intercept incoming request and return its URL.
        If `timeout` is None, server waits until a request is intercepted.

        Args:
            timeout: Seconds to wait for. Default: `None`

        Returns:
            Intercepted request URL if any, else None
        """
        self.raise_if_not_running()
        time_out_fmt = f"{timeout}s" if timeout is not None else "nil"
        self.logger.info(f"Intercepting request (timeout: <u>{time_out_fmt}</u>)")

        self.__instance.timeout = timeout
        self.__instance.handle_request()
        return self.__app.last_request_url

    def stop(self) -> None:
        """Stop the server."""
        if self.is_running:
            self.logger.info("Shutting down the server...")
            self.__instance.server_close()
            self.__instance = None  # type: ignore[assignment]

    def __del__(self) -> None:
        self.stop()

    def __exit__(self, exc_type: Any, exc_value: Any, tb: Any) -> None:
        self.stop()
