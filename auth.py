from authlib.integrations.starlette_client import OAuth
from config import CONFIG



oauth = OAuth()

oauth.register(
    name="synology",
    server_metadata_url = CONFIG("OIDC_SERVER_METADATA_URL"),
    client_id = CONFIG("OIDC_CLIENT_ID"),
    client_secret = CONFIG("OIDC_CLIENT_SECRET"),
    client_kwargs = {
        "scope": "openid email profile"
    }
)