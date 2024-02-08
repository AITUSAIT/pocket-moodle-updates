import json

from modules.database.db import DB
from modules.database.models import Proxy, Server


class ServerDB(DB):
    @classmethod
    async def get_servers(cls) -> dict[str, Server]:
        async with cls.pool.acquire() as connection:
            servers = await connection.fetch("SELECT token, name, proxy_list FROM servers")

            return {
                _["token"]: Server(
                    token=_["token"],
                    name=_["name"],
                    proxies=[
                        Proxy(
                            login=proxy["login"],
                            password=proxy["passwd"],
                            ip=proxy["ip"],
                            port=proxy["http_port"],
                        )
                        for proxy in json.loads(_["proxy_list"])
                    ],
                )
                for _ in servers
            }
