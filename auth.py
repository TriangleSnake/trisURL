from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

config = Config(".env")

oauth = OAuth(config)

oauth.register(
    name="synology",
    server_metadata_url="https://nas.trianglesnake.com/webman/sso/.well-known/openid-configuration",
    client_id=config("OIDC_CLIENT_ID"),
    client_secret=config("OIDC_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid email profile"
    }
)