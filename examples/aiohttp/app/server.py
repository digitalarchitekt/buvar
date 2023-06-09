"""Create a aiohttp server task and provide the application via context."""
import aiohttp.web
import attr
import structlog

from buvar import config, context, di

sl = structlog.get_logger()


@attr.s(auto_attribs=True)
class AioHttpConfig(config.Config, section="aiohttp"):
    host: str = "0.0.0.0"
    port: int = 8080


class AccessLogger(aiohttp.abc.AbstractAccessLogger):  # noqa: R0903
    def log(self, request, response, time):  # noqa: R0201
        sl.info(
            "Access",
            remote=request.remote,
            method=request.method,
            path=request.path,
            time=time,
            status=response.status,
        )


@aiohttp.web.middleware
async def request_context(request, handler):
    with context.child():
        context.add(request)
        return await handler(request)


async def prepare():
    aiohttp_config = await di.nject(AioHttpConfig)
    aiohttp_app = context.add(
        aiohttp.web.Application(
            middlewares=[aiohttp.web.normalize_path_middleware(), request_context]
        )
    )

    sl.info("Running web server", host=aiohttp_config.host, port=aiohttp_config.port)
    # return server task
    yield aiohttp.web._run_app(  # noqa: W0212
        aiohttp_app,
        host=aiohttp_config.host,
        port=aiohttp_config.port,
        print=None,
        access_log=aiohttp_config.access_log,
    )
