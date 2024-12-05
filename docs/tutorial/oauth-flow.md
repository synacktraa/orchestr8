OAuthFlow is a component that can be inherited to create authentication flows for connecting with services.

- `OAuthFlow` requires `mkcert` for setting up local redirect server, refer [here](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#installation) for installation instructions

Here we will create a flow for connecting with discord.

To create a flow, you can inherit the `OAuthFlow` class and implement the `get_authorization_url` and `get_token` methods.

```python
import orchestr8 as o8
import requests

class DiscordOAuthFlow(o8.OAuthFlow):
    """Class for handling Discord OAuth2 flow."""

    @property
    def auth_url(self) -> str:
        """
        Formatted Discord authorization URL for getting code.
        """
        return (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={self.client_id}&redirect_uri={self.quoted_redirect_url}"
            f"&response_type=code&scope={self.user_scopes}"
        )

    def _generate_access_token(self, code: str) -> str:
        """
        Generate an access token from the authorization code.

        :param code: Authorization code from Discord.
        :return: The access token.
        """
        response = requests.post(
            "https://discord.com/api/oauth2/token",
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_url,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            auth=(self.client_id, self.client_secret)
        )

        if response.status_code != 200:
            raise Exception(f"Failed to obtain access token: {response.json()}")

        return response.json()['access_token']

discord_flow = DiscordOAuthFlow(
    client_id="<client-id>",
    client_secret="<client-secret>",
    user_scopes="identify messages.read",
)
access_token = discord_flow.authorize(timeout=30)
```

> To generate client id and secret, refer [discord oauth2 docs](https://discord.com/developers/docs/topics/oauth2) or directly go to [discord developer portal](https://discord.com/developers/applications)
