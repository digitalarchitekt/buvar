Búvár
=====

This is heavily inspired by `Pyramid`_ and my daily needs to fastly create and
maintain microservice like applications.


a plugin mechanic
-----------------

- plugin may depend on other plugins

- plugins yield tasks to run

- a context registry serves as a store for application components created by plugins

- a dependency injection creates intermediate components

- a config source is mapped to plugin specific configuration and may be fully
  overridden by environment vars

- structlog boilerplate for json/tty logging

- fork the process and share bound sockets

- pytest fixtures to reduce testing boilerplate


You bootstrap like following:

.. code-block:: python

    from buvar import plugin

    plugin.stage("some.module.with.prepare")


.. code-block:: python

   # some.module.with.prepare
   from buvar import context, plugin

   class Foo:
       ...


   async def task():
       asyncio.sleep(1)


   async def server():
       my_component = context.get(Foo)
       await asyncio.Future()


   # there is also plugin.Teardown and plugin.Cancel
   async def prepare(load: plugin.Loader):
       await load('.another.plugin')

       # create some long lasting components
       my_component = context.add(Foo())

       # you may run simple tasks
       yield task()

       # you may run server tasks
       yield server()


a components and dependency injection solution
----------------------------------------------

Dependency injection relies on registered adapters, which may be a function, a
method, a class, a classmethod or a generic classmthod.

Dependencies are looked up in components or may be provided via kwargs.


.. code-block:: python

   from buvar import di

   class Bar:
       pass

   class Foo:
       def __init__(self, bar: Bar = None):
           self.bar = bar

       @classmethod
       async def adapt(cls, baz: str) -> Foo:
           return Foo()

   async def adapt(bar: Bar) -> Foo
       foo = Foo(bar)
       return foo


   async def task():
       foo = await di.nject(Foo, baz="baz")
       assert foo.bar is None

       bar = Bar()
       foo = await di.nject(Foo, bar=bar)
       assert foo.bar is bar

   async def prepare():
       di.register(Foo.adapt)
       di.register(adapt)

       yield task()



a config source
---------------

:code:`buvar.config.ConfigSource` is just a :code:`dict`, which merges
arbitrary dicts into one. It serves as the single source of truth for
application variability.

You can load a section of config values into your custom `attrs`_ class instance. ConfigSource will override values by environment variables if present.


`config.toml`

.. code-block:: toml

   log_level = "DEBUG"
   show_warnings = "yes"

   [foobar]
   some = "value"


.. code-block:: bash

   export APP_FOOBAR_SOME=thing


.. code-block:: python

   import attr
   import toml

   from buvar import config

   @attr.s(auto_attribs=True)
   class GeneralConfig:
       log_level: str = "INFO"
       show_warnings: bool = config.bool_var(False)


   @attr.s(auto_attribs=True)
   class FoobarConfig:
      some: str


   source = config.ConfigSource(toml.load('config.toml'), env_prefix="APP")

   general_config = source.load(GeneralConfig)
   assert general_config == GeneralConfig(log_level="DEBUG", show_warnings=True)

   foobar_config = source.load(FoobarConfig, 'foobar')
   assert foobar_config.some == "thing"


There is a shortcut to the above approach provided by
:code:`buvar.config.Config`, which requires to be subclassed from it with a
distinct :code:`section` attribute. If one adds a :code:`buvar.config.ConfigSource`
component, he will receive the mapped config in one call.

.. code-block:: python

   from buvar import config, plugin


   @attr.s(auto_attribs=True)
   class GeneralConfig(config.Config):
       log_level: str = "INFO"
       show_warnings: bool = config.bool_var(False)


   @attr.s(auto_attribs=True)
   class FoobarConfig(config.Config, section="foobar"):
       some: str


   async def prepare(load: plugin.Loader):
       # this would by typically placed in the main CLI entry point
       source = context.add(config.ConfigSource(toml.load('config.toml'), env_prefix="APP"))

       # to provide the adapter to di, which could also be done in the main entry point
       await load(config)
       foobar_config = await di.nject(FoobarConfig)


a structlog
-----------

Just `structlog`_ boilerplate.

.. code-block:: python

   import sys

   from buvar import log

   log_config = log.LogConfig(tty=sys.stdout.isatty(), level="DEBUG")
   log_config.setup()


forked process and shared sockets
---------------------------------

You may fork your process and bind and share sockets, to leverage available
CPUs e.g. for serving an aiohttp microservice.

Signals like INT, TERM, HUP are forwarded to the child processes.


.. code-block:: python

    import aiohttp.web
    from buvar import fork, plugin, di, context
    from buvar_aiohttp import AioHttpConfig


    async def hello(request):
        return aiohttp.web.Response(body=b"Hello, world")


    async def prepare_aiohttp(load: plugin.Loader):
        await load("buvar_aiohttp")

        app = await di.nject(aiohttp.web.Application)
        app.router.add_route("GET", "/", hello)


    context.add(AioHttpConfig(host="0.0.0.0", port=5678))

    fork.stage(prepare_aiohttp, forks=0, sockets=["tcp://:5678"])


pytest
------

There are a couple of pytest fixtures provided to get your context into a
reasonable state:

:code:`buvar_config_source`
    A :code:`dict` with arbitrary application settings.

:code:`buvar_context`
    The basic context staging operates on.

:code:`buvar_stage`
    The actual stage processing all plugins.

:code:`buvar_load`
    The loader to add plugins to the stage.

:code:`buvar_plugin_context`
    The context all plugins share, when they are prepared.


Following markers may be applied to a test

:code:`buvar_plugins(plugin, ...)`
    Load all plugins into plugin context.


.. code-block:: python

    import pytest


    async def prepare():
        from buvar import context

        context.add("foobar")


    @pytest.mark.asyncio
    @pytest.mark.buvar_plugins("tests.test_testing")
    async def test_wrapped_stage_context():
        from buvar import context, plugin

        assert context.get(str) == "foobar"
        assert context.get(plugin.Cancel)


    @pytest.mark.asyncio
    @pytest.mark.buvar_plugins()
    async def test_wrapped_stage_context_load(buvar_load):
        from buvar import context, plugin

        await buvar_load(prepare)
        assert context.get(str) == "foobar"
        assert context.get(plugin.Cancel)


.. _Pyramid: https://github.com/Pylons/pyramid
.. _structlog: https://www.structlog.org/en/stable/
.. _attrs: https://www.attrs.org/en/stable/

