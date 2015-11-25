=========
lru2layer
=========
A `least recently used (LRU) <http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used>`_
2 layer caching mechanism based in part on the Python 2.7 back-port of lru_cache

lru2layer is a decorator that can be used with any user function or method to
cache the most recent results in a local cache.  It can alse be used with
django's cache framework to cache results in a shared cache.

The first layer of caching is stored in a dict within the instance of the
function or method. Each instance stores up to maxsize results based on args
and kwargs passed to it.  The discarding of the LRU cached values is handled by
the lru2layer decorator

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
Since the lru2layer decorator does not provide a timeout for its cache although
it provides other mechanisms for programatically managing the cache.

Cache Statistics
----------------
As with lru_cache, one can view the cache statistics named tuple (hits, misses,
maxsize, currsize) for a specific instantiation with f.cache_info(). Statistics
for the shared cache would need to be obtained from the shared cache.

Clearing Instance Cache
-----------------------
the cache and statistics associated with a function or method can be cleared with::

    f.cache_clear()


Clearing Shared Cache
---------------------
If you are using a named cache it can easily be cleared with the following::

    from django.core.cache import get_cache

    lru2layer_cache = get_cache('lru2layer')
    lru2layer_cache.clear()


Invalidating Cached Results
---------------------------
To invalidate the cache for a specific set of arguments, including the instance
one can pass the same arguments to invalidate the both L1 and L2 caches::

    f.invalidate(*args, **kwargs)

in the case of a method you do need to explicitly pass the instance as in the
following::

    class foo():
        ...

        def f(a, b):
            ...
    foo.f(a, b)
    foo.f.invalidate(foo, a, b)

Refreshing the Cache
--------------------
This is not yet implemented as function but can be accomplished by first calling
invalidate and the calling the wrapped function

Accessing the Function without Cache
------------------------------------
The un-cached underlying function can always be accessed with ``f.__wrapped__``.
