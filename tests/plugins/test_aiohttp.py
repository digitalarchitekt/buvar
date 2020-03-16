import pytest


@pytest.mark.asyncio
@pytest.mark.buvar_plugins("buvar.plugins.aiohttp")
async def test_app_dummy(buvar_aiohttp_app, test_client):
    import aiohttp.web

    async def hello(request):
        return aiohttp.web.Response(body=b"Hello, world")

    buvar_aiohttp_app.router.add_route("GET", "/", hello)

    client = await test_client(buvar_aiohttp_app)
    resp = await client.get("/")
    assert "Hello, world" == await resp.text()
