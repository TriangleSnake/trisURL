from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

config = Config(".env")

oauth = OAuth()

oauth.register(
    name="synology",
    server_metadata_url = config("OIDC_SERVER_METADATA_URL"),
    client_id = config("OIDC_CLIENT_ID"),
    client_secret = config("OIDC_CLIENT_SECRET"),
    client_kwargs = {
        "scope": "openid email profile"
    }
)