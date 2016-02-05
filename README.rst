=========
lru2cache
=========

.. image:: https://travis-ci.org/3Top/lru2cache.svg?branch=master
    :target: https://travis-ci.org/3Top/lru2cache
    :alt: Travis-CI

.. image:: https://codeclimate.com/github/3Top/lru2layer/badges/gpa.svg
   :target: https://codeclimate.com/github/3Top/lru2layer
   :alt: Code Climate


.. image:: https://coveralls.io/repos/3Top/lru2cache/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/3Top/lru2cache?branch=master
  :alt: Coveralls.io


A `least recently used (LRU) <http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used>`_
2 layer caching mechanism based in part on the Python 2.7 back-port of
``functools.lru_cache``

This was developed by `3Top, Inc. <http://www.3top.com/team>`_ for use with
our ranking and recommendation platform, http://www.3top.com.

lru2cache is a decorator that can be used with any user function or method to
cache the most recent results in a local cache and using the django cache
framework to cache results in a shared cache.

The first layer of caching is stored in a callable that wraps the function or
method.  As with 'functools.lru_cache' a dict is used to store the cached
results, therefore positional and keyword arguments must be hashable. Each
instance stores up to ``l1_maxsize`` results that vary on the arguments. The
discarding of the LRU cached values is handled by the decorator.

The second layer of caching requires a shared cache that can make use of
Django's cache framework.  In this case it is assumed that any LRU mechanism
is handled by the shared cache backend.

This arrangement allows a process that accesses a function multiple times to
retrieve the value without the expense of requesting it from a shared cache,
while still allowing different processes to access the result from the shared
cache.

Installation & Configuration
============================
The easiest and best way to install this is with pip::

    pip install lru2cache

If available this package will use SpookyHash V2 as a hashing mechanism.
Spooky is a good fast hashing algorithm that should be suitable for most uses.
If it is not available the package will fall back to SHA-256 from the standard
hashlib.  Because SHA-256 is a proper cryptographic hash it requires more
computation than Spooky.  To install spooky use pip::

    pip install spooky 2

Once lru2cache is installed you will need to configure a shared cache as an
l2 cache.  If you are using Django your settings file will contain something
similar to the following in the settings file::

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': 1200,
        },
        'l2cache': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': None,
        },
    }

If you do not want to use either ``default`` or ``l2cache`` you will need to
specify the name of the cache.

Benefits Over functools.lru_cache
=================================

**Local and Shared Cache** - Combining both types of cache is much more
effective than either used on it's own.  The local cache eliminates the
latency of calls to a shared cache, while the shared cache eliminates
the expense of returning the result

**The Ability to Not Cache None Results** - This may seem like a minor thing
but in our environment it has greatly reduced the frequency of cache
invalidations.

Usage
=====
::

  @utils.lru2cache(l1_maxsize=128, none_cache=False, typed=False, l2cache_name='l2cache', inst_attr='id')

Usage is as simple as adding the decorator to a function or method as seen in
the below examples from our test cases::

    from lru2cache import utils

    @utils.lru2cache()
    def py_cached_func(x, y):
        return 3 * x + y


    class TestLRUPy(TestLRU):
        module = utils
        cached_func = py_cached_func,

        @utils.lru2cache()
        def cached_meth(self, x, y):
            return 3 * x + y

        @staticmethod
        @utils.lru2cache()
        def cached_staticmeth(x, y):
            return 3 * x + y

If ``l1_maxsize`` is set to ``None``, the LRU feature is disabled and the L1 cache
can grow without bound. The LRU feature performs best when maxsize is a power-of-two.

if ``none_cache`` is ``True`` than ``None`` results will be cached, otherwise they
will not.

If ``typed`` is set to ``True``, function arguments of different types will be
cached separately. For example, f(3) and f(3.0) will be treated as distinct
calls with distinct results.

If ``l2cache_name`` is specified it will be used as the shared cache.  Otherwise
it will attempt to use a cache named ``l2cache`` and if not found fall back to
``default``.

``inst_attr`` is the attribute used to uniquely identify an object when wrapping
a method.  In Django this will typically be ``id`` however if it is not you will
need to specify what attribute should be used.

Cache Management
================
Since the lru2cache decorator does not provide a timeout for its cache although
it provides other mechanisms for programatically managing the cache.

Cache Statistics
----------------
As with lru_cache, one can view the cache statistics via a named tuple
(l1_hits, l1_misses, l2_hits, l2_misses, l1_maxsize, l1_currsize), with
``f.cache_info()``. These stats are stored within an instance, and therefore
are specific to that instance. Cumulative statistics for the shared cache would
need to be obtained from the shared cache.

Clearing Instance Cache
-----------------------
the cache and statistics associated with a function or method can be cleared with::

    f.cache_clear()

Clearing Shared Cache
---------------------
A shared cache can easily be cleared with the following::

    from django.core import cache

    lru2cache_cache = cache.get_cache('l2cache')
    lru2cache_cache.clear()


Invalidating Cached Results
---------------------------
To invalidate the cache for a specific set of arguments, including the instance
one can pass the same arguments to invalidate the both L1 and L2 caches::

    f.invalidate(*args, **kwargs)

in the case of a method you do need to explicitly pass the instance as in the
following::

    foo.f.invalidate(foo, a, b)

Refreshing the Cache
--------------------
This is not yet implemented as a function but can be accomplished by first calling
invalidate and then calling the function

Accessing the Function without Cache
------------------------------------
The un-cached underlying function can always be accessed with ``f.__wrapped__``.

Background and Development
--------------------------
At `3Top <http://www.3top.com/>`_ We needed a way to improve performance of
slow queries, not just those using the Django ORM, but also for queries to
other data stores and services.  We started off with a simpler centralized
caching solution using Memcached, but even those queries, when called frequently,
can start to cause delays.  Therefore we sought a means of caching at two layers.

Initially we looked at the possibility of using two different mechanisms but
we quickly saw the advantage of maintaining the same set of keys for both
caches and decided to create our own mechanism.

We used a backport python 3 ``functools.lru_cache()`` decorator as a starting
point for developing an in instance cache with LRU capabilities.  However we
needed to ensure the keys would also be unique enough to use with a shared
cache. We leverage Django's excellent cache framework for managing the layer 2
cache. This allows the use of any shared cache supported by Django.

Tests
-----
As a starting point I incorporated most of the tests for
``functools.lru_cache()`` with minor changes to make them work with python 2.7
and incorporated the l2_cache stats. We will continue to add tests to validate
the additional functionality provided by this decorator.
