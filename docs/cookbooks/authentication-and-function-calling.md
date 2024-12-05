Modern applications often rely on third-party services to extend their capabilities, but securing and managing authentication can be a significant technical challenge. OAuth has become the standard protocol for secure, delegated access, yet implementing it correctly requires handling complex token exchanges, refresh mechanisms, and secure credential management.

This cookbook demonstrates how to simplify OAuth authentication within function-calling workflows, providing a streamlined approach to securely connecting and accessing external service APIs.

## Installation and Setup

This cookbook requires the `litellm` library for function-call generation via the Groq provider.

If you don't have an API key for Groq, you can get one at [Groq Console](https://console.groq.com/keys).

> `OAuthFlow` component requires `mkcert` for setting up local redirect server, refer [here](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#installation) for installation instructions

```python
%pip install orchestr8[adapter] litellm requests

import os, getpass

def set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

set_env("GROQ_API_KEY")
```

```python
import json
from typing import Any, Dict, List

from litellm import completion

INSTRUCTION = "Complete user requests using the given functions."

def generate_function_call(request: str, functions: List[Dict[str, Any]]):
    response = completion(
        model="groq/llama3-groq-70b-8192-tool-use-preview",
        messages=[
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": request}
        ],
        tools=functions
    )
    tool_call = response.choices[0].message.tool_calls[0].function
    if tool_call is None:
        print(response.choices[0].message.content)
        raise Exception("No function call found in the response.")
    return tool_call.name, json.loads(tool_call.arguments)
```

## Creating an OAuth Flow

Here, we'll create an OAuth flow for the `discord` service. This flow will allow us to authenticate with Discord and obtain an access token. In later steps, we'll use this access token to access the Discord API through function calls.

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
    user_scopes="identify email guilds",
)
access_token = discord_flow.authorize(timeout=30)
```

!!! success "Logs"

    ```
    [DiscordOAuthFlow] Starting authorization process
    [RedirectServer] Redirect server started on localhost:41539
    [DiscordOAuthFlow] Add this URL to your application's redirect settings: https://localhost:41539/
    [DiscordOAuthFlow] Click this URL to authorize: https://discord.com/api/oauth2/authorize?client_id=<client-id>&redirect_uri=https%3A%2F%2Flocalhost%3A41539%2F&response_type=code&scope=identify+email+guilds
    [RedirectServer] Intercepting request (timeout: 30s)
    [DiscordOAuthFlow] Authorization code received
    [DiscordOAuthFlow] Access token generated successfully
    ```

> To generate client id and secret, refer [discord oauth2 docs](https://discord.com/developers/docs/topics/oauth2) or directly go to [discord developer portal](https://discord.com/developers/applications)

## Creating adapters from functions

Creating adapters is as simple as defining a function and decorating it with `@adapt` decorator.

```python
import orchestr8 as o8
import requests

@o8.adapt
def fetch_my_discord_info():
    """Fetch my information from the Discord API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://discord.com/api/v9/users/@me', headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Failed to fetch user info: {response.status_code} - {response.text}')

@o8.adapt
def fetch_my_discord_guilds():
    """Fetch the guilds that I am a member of on Discord."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://discord.com/api/v9/users/@me/guilds', headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Failed to fetch user guilds: {response.status_code} - {response.text}')
```

## Generating function-call

There are three available function-calling schema formats: OpenAI, Anthropic, and Gemini.

We'll be using OpenAI schema for this example as we're using Llama model.

```python
function_call = generate_function_call(
    "Fetch my discord info",
    functions=[fetch_my_discord_info.openai_schema, fetch_my_discord_guilds.openai_schema],
)
print(function_call)
```

!!! success "Result"

    ```python
    ('fetch_my_discord_info', {})
    ```

Now, we can utilize the `validate_input` method to send the message to the specified discord channel.

```python
fetch_my_discord_info.validate_input(function_call[1])
```

!!! success "Result"

    ```python
    {
        'id': '1260905671142936631',
        'username': 'synacktra._81487',
        'avatar': None,
        'discriminator': '0',
        'public_flags': 0,
        'flags': 0,
        'banner': None,
        'accent_color': None,
        'global_name': 'synacktra',
        'avatar_decoration_data': None,
        'banner_color': None,
        'clan': None,
        'primary_guild': None,
        'mfa_enabled': True,
        'locale': 'en-US',
        'premium_type': 0,
        'email': 'synacktra.work@gmail.com',
        'verified': True
    }
    ```
