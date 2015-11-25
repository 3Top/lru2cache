# lru2layer
A [least recently used
(LRU)](http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used)
2 layer caching mechanism based in part on the Python 2x back-port of lru_cache

lru2layer is a decorator that can be used with any user function or method to
cache the most recent results in a local and shared cache.

The first layer of caching is stored in a dict within the instance of the
function or method. Each instance stores up to maxsize results based on args
and kwargs passed to it.  The discarding of the LRU cached values is handled by
the lru2layer decorator

The second layer of caching requires a shared cache such as that provided by
Django's cache framework.  In this case it is assumed that any LRU mechanism
is handled by the shared cache.

This arrangement allows an instance that accesses a function multiple times to
retrieve the value without the expense of requesting it from a shared cache,
yet still allows instances in different threads to access the value from a
shared cache.

If *typed* is True, arguments of different types will be cached separately.
For example, f(3.0) and f(3) will be treated as distinct calls with
distinct results.  In the case of methods, the first argument(self) is always
typed.

Arguments to the cached function must be hashable.

As with lru_cache, one can view the cache statistics named tuple (hits, misses,
maxsize, currsize) for a specific instantiation with f.cache_info() and clear
the cache and statistics with f.cache_clear().

The uncached underlying function can be accessed with f.__wrapped__.  And cache
for a specific set of arguments, including instance in the case of a method can
be invalidated with f.invalidate(*args, **kwargs).

