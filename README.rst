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
2 layer caching mechanism based in part on the Python 2.7 back-port of lru_cache

This was developed by `3Top, Inc. <http://www.3top.com/team>`_ for use with
our ranking and recommendation platform, http://www.3top.com.

lru2cache is a decorator that can be used with any user function or method to
cache the most recent results in a local cache.  It can alse be used with
django's cache framework to cache results in a shared cache.

The first layer of caching is stored in a dict within the instance of the
function or method. Each instance stores up to maxsize results based on args
and kwargs passed to it.  The discarding of the LRU cached values is handled by
the lru2cache decorator.

The second layer of caching requires a shared cache that behaves the same as
Django's cache framework.  In this case it is assumed that any LRU mechanism
is handled by the shared cache backend.

This arrangement allows an instance that accesses a function multiple times to
retrieve the value without the expense of requesting it from a shared cache,
while still allowing instances in different threads to access the result from
the shared cache.

Arguments & Keywords
====================
Arguments to the cached function must be hashable. If available the spooky hash
function will be used for generating keys, otherwise it will default back to
the slower, hashlib.sha256.

Typed Arguments
---------------
If *typed* is ``True``, arguments of different types will be cached separately.
For example, f(3.0) and f(3) will be treated as distinct calls with
distinct results.  In the case of methods, the first argument(self) is always
typed.

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
If you are using a named cache it can easily be cleared with the following::

    from django.core.cache import get_cache

    lru2cache_cache = get_cache('lru2cache')
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
This is not yet implemented as function but can be accomplished by first calling
invalidate and the calling the wrapped function

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
As a starting point incorporated most of the tests for ``lru_cache()``
with minor changes to make them work with python 2.7 and incorporate the
l2_cache stats. We will continue to add tests to validate the additional
functionality provided by this decorator.
