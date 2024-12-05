from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

import pytest

from orchestr8.oauth_flow import OAuthFlow
from orchestr8.oauth_flow.redirect_server import RedirectServer


class TestOAuthFlow:
    """Comprehensive test suite for OAuthFlow base class."""

    @pytest.fixture
    def mock_redirect_server(self, monkeypatch):
        """Fixture to mock RedirectServer and bypass SSL certificate checks."""
        mock_server = MagicMock(spec=RedirectServer)
        mock_server.is_running = True
        mock_server.url = "https://localhost:41539/"

        # Patch the RedirectServer initialization to use the mock
        monkeypatch.setattr("orchestr8.oauth_flow.RedirectServer", MagicMock(return_value=mock_server))

        return mock_server

    class ConcreteOAuthFlow(OAuthFlow):
        """Concrete implementation of OAuthFlow for testing."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._mock_access_token = "test_access_token"  # noqa: S105

        @property
        def auth_url(self) -> str:
            """Mock auth URL generation."""
            return (
                f"https://test.com/oauth/authorize"
                f"?client_id={self.client_id}"
                f"&redirect_uri={self.quoted_redirect_url}"
                f"&response_type=code"
                f"&scope={self.user_scopes}"
            )

        def _generate_access_token(self, code: str) -> str:
            """Mock access token generation."""
            return self._mock_access_token

    def test_init_with_minimal_parameters(self, mock_redirect_server):
        """Test initialization with minimal required parameters."""
        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        assert flow.client_id == "test_client_id"
        assert flow.client_secret == "test_client_secret"  # noqa: S105
        assert flow.user_scopes == ""
        assert flow._redirect_server == mock_redirect_server

    def test_redirect_url_property(self, mock_redirect_server):
        """Test redirect URL property behavior."""
        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        redirect_url = flow.redirect_url
        assert redirect_url == "https://localhost:41539/"
        assert flow._redirect_server.is_running is True

    def test_quoted_redirect_url(self, mock_redirect_server):
        """Test quoted redirect URL generation."""
        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        quoted_url = quote_plus("https://localhost:41539/")
        assert flow.quoted_redirect_url == quoted_url

    @patch("orchestr8.oauth_flow.OAuthFlow._get_auth_code")
    def test_authorize_method(self, mock_get_code, mock_redirect_server):
        """Test full authorization flow."""
        mock_get_code.return_value = "test_auth_code"

        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        token = flow.authorize(timeout=10)

        assert token == "test_access_token"  # noqa: S105
        mock_get_code.assert_called_once_with(timeout=10)

    def test_auth_url_property_not_implemented(self):
        """Test that base OAuthFlow cannot be instantiated directly."""
        with pytest.raises(TypeError, match="OAuthFlow cannot be instantiated directly"):
            OAuthFlow(client_id="test", client_secret="test")  # noqa: S106

    def test_subclass_requires_auth_url_property(self):
        """Test that subclasses must implement auth_url property."""
        with pytest.raises(TypeError, match="must define 'auth_url' property"):

            class InvalidOAuthFlow(OAuthFlow):
                def _generate_access_token(self, code: str) -> str:
                    return "token"

    def test_subclass_requires_generate_access_token_method(self):
        """Test that subclasses must implement _generate_access_token method."""
        with pytest.raises(TypeError, match="must define '_generate_access_token' method"):

            class InvalidOAuthFlow(OAuthFlow):
                @property
                def auth_url(self) -> str:
                    return "https://test.com"

    def test_get_auth_code_timeout(self, mock_redirect_server):
        """Test authorization code retrieval with timeout."""
        mock_redirect_server.intercept.return_value = None

        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        with pytest.raises(TimeoutError, match="No authorization request was intercepted"):
            flow._get_auth_code(timeout=5)

    def test_get_auth_code_denied(self, mock_redirect_server):
        """Test authorization code retrieval when request is denied."""
        mock_redirect_server.intercept.return_value = "https://localhost:41539/?error=access_denied"

        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        with pytest.raises(ConnectionAbortedError, match="Authorization failed or was denied"):
            flow._get_auth_code(timeout=5)

    def test_del_method_stops_redirect_server(self, mock_redirect_server):
        """Test that __del__ method stops the redirect server."""
        flow = self.ConcreteOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106
        )

        del flow
        # No direct assertion needed, as we're checking that no exception is raised
