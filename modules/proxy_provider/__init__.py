from itertools import cycle

from config import SERVER_TOKEN
from modules.database.models import Proxy
from modules.database.server import ServerDB


class ProxyProvider:
    proxies: cycle | None

    @classmethod
    def get_proxy(cls) -> Proxy | None:
        return next(cls.proxies) if cls.proxies else None

    @classmethod
    async def update(cls) -> None:
        servers = await ServerDB.get_servers()
        server = servers.get(SERVER_TOKEN)
        if server:
            cls.proxies = cycle(server.proxies)
        else:
            cls.proxies = cycle([None])