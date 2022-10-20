import asyncio
from aiohttp import web


def run_server():
    def root(request):
        return web.Response(text='Ok')

    asyncio.set_event_loop(asyncio.new_event_loop())
    app = web.Application(debug=True)
    app.add_routes([web.get('/', root)])
    web.run_app(app, handle_signals=False)