from aiohttp import web

routes = web.RouteTableDef()


@routes.get('/')
async def root(request):
    return web.Response(text="Ok")


def start_server():
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, access_log=None, port=8000)