import json
from . import DB
from .models import Server


class ServerDB(DB):
    @classmethod
    async def get_servers(cls) -> dict[str, Server]:
        async with cls.pool.acquire() as connection:
            servers = await connection.fetch('SELECT token, name, proxy_list FROM servers')
            
            return { _['token']: Server(
                _['token'],
                _['name'],
                json.loads(_['proxy_list']),
                ) for _ in servers }


    