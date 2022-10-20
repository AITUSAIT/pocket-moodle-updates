import asyncio
from aiohttp import web


def aiohttp_server():
    def root(request):
        return web.Response(text='Ok')

    app = web.Application()
    app.add_routes([web.get('/', root)])
    runner = web.AppRunner(app)
    return runner
    

def run_server(runner):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, 'localhost', 8000)
    loop.run_until_complete(site.start())
    loop.run_forever()