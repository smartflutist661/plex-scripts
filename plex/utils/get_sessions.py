from typing import Optional

import urllib3
from plexapi.server import PlexServer
from tautulli import RawAPI  # type: ignore

# SSL library has added hostname checks to handshake in a C extension
# C extensions cannot be monkey-patched
# To fix, add `verify=False` to the call to `requests` (`method`) in `PlexServer.query()`
# To make this truly portable, will need to vendor plex API with this repo
urllib3.disable_warnings()


def get_plex_session(api_key: str, local: bool = False, host: Optional[str] = None) -> PlexServer:
    if not local and host is None:
        raise RuntimeError("Remote sessions require a hostname argument")
    if local:
        return PlexServer("http://localhost:32400", api_key)
    return PlexServer(f"https://{host}:32400", api_key)


def get_tautulli_session(api_key: str, local: bool = False, host: Optional[str] = None) -> RawAPI:
    if not local and host is None:
        raise RuntimeError("Remote sessions require a hostname argument")

    if local:
        return RawAPI(
            base_url="https://localhost:8181",
            api_key=api_key,
            ssl_verify=False,
        )
    else:
        return RawAPI(
            base_url=f"https://{host}:8181",
            api_key=api_key,
            ssl_verify=False,
        )
