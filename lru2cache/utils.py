from __future__ import unicode_literals
from django.core.cache import get_cache
from collections import namedtuple
from functools import update_wrapper
from threading import RLock
try:
    from spooky import hash128 as hash
except:
    from hashlib import sha256
    hash = lambda x: sha256(x).hexdigest()
import inspect


_CacheInfo = namedtuple("CacheInfo", ["l1_hits", "l1_misses", "l2_hits", "l2_misses", "l1_maxsize", "l1_currsize"])


def _make_key(user_function, args, kwds, typed,
             kwd_mark = (object(),),
             fasttypes = {int, str, frozenset, type(None)},
             sorted=sorted, tuple=tuple, type=type, len=len, inst_attr='id'):
    'Make a cache key from optionally typed positional and keyword arguments'
    args = list(args)
    if len(args) > 0 and inspect.ismethod(getattr(args[0], user_function.__name__, None)):
        instance = args.pop(0)
        key = ["{c}{i}".format(
                c=instance.__class__,
                i=getattr(instance, inst_attr, instance.__hash__())
            ), user_function.__name__]
    else:
        key = ["", user_function.__name__]
    if args:
        key.append(tuple(args))
    if kwds:
        sorted_items = sorted(kwds.items())
        tuple_ = (kwd_mark,) + tuple(item for item in sorted_items)
        key.append(tuple_)
    if typed:
        key.append(tuple(type(v) for v in args))
        if kwds:
            key[-1] += tuple(type(v) for k, v in sorted_items)
    return hash(str(key).encode('utf-8'))



def lru2cache(l1_maxsize=128, none_cache=False, typed=False, l2cache_name='default', inst_attr='id'):
    """Least-recently-used cache decorator.

    If *l1_maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (l1_hits, l1_misses, l2_hits, l2_misses,
    l1_maxsize, l1_currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """

    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    l2cache = get_cache(l2cache_name)

    def decorating_function(user_function):

        cache = dict()
        stats = [0, 0, 0, 0]                  # make statistics updateable non-locally
        L1_HITS, L1_MISSES, L2_HITS, L2_MISSES = 0, 1, 2, 3     # names for the stats fields
        make_key = _make_key
        cache_get = cache.get           # bound method to lookup key or return None
        _len = len                      # localize the global len() function
        lock = RLock()                  # because linkedlist updates aren't threadsafe
        root = []                       # root of the circular doubly linked list
        root[:] = [root, root, None, None]      # initialize by pointing to self
        nonlocal_root = [root]                  # make updateable non-locally
        PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

        if l1_maxsize == 0:

            def wrapper(*args, **kwds):
                # No l1 caching, only implements shared caching and tracks accesses
                key = make_key(user_function, args, kwds, typed, inst_attr=inst_attr)
                result = l2wrapper(key, user_function, none_cache, *args, **kwds)
                stats[L1_MISSES] += 1
                return result

        elif l1_maxsize is None:

            def wrapper(*args, **kwds):
                # unlimited size l1 caching, as well as shared caching that tracks accesses
                key = make_key(user_function, args, kwds, typed, inst_attr=inst_attr)
                result = cache_get(key, root)   # root used here as a unique not-found sentinel
                if result is not root:
                    stats[L1_HITS] += 1
                    return result
                
                result = l2wrapper(key, user_function, none_cache, *args, **kwds)
                if none_cache or result is not None:
                    cache[key] = result
                stats[L1_MISSES] += 1
                return result
        else:

            def wrapper(*args, **kwds):
                """ size limited L1 caching that tracks accesses by recency, as well as shared
                caching.  Tracking the least-recently-used cache is done with a linked list
                since that allows for reordering the list relatively inexpensively."""
                key = make_key(user_function, args, kwds, typed, inst_attr=inst_attr)
                with lock:
                    link = cache_get(key)
                    if link is not None:
                        # record recent use of the key by moving it to the front of the list
                        root, = nonlocal_root
                        link_prev, link_next, key, result = link
                        link_prev[NEXT] = link_next
                        link_next[PREV] = link_prev
                        last = root[PREV]
                        last[NEXT] = root[PREV] = link
                        link[PREV] = last
                        link[NEXT] = root
                        stats[L1_HITS] += 1
                        return result
                result = l2wrapper(key, user_function, none_cache, *args, **kwds)
                if none_cache or result is not None:
                    with lock:
                        root, = nonlocal_root
                        if key in cache:
                            # getting here means that this same key was added to the
                            # cache while the lock was released.  since the link
                            # update is already done, we need only return the
                            # computed result and update the count of l1_misses.
                            pass
                        elif _len(cache) >= l1_maxsize:
                            # use the old root to store the new key and result
                            oldroot = root
                            oldroot[KEY] = key
                            oldroot[RESULT] = result
                            # empty the oldest link and make it the new root
                            root = nonlocal_root[0] = oldroot[NEXT]
                            oldkey = root[KEY]
                            oldvalue = root[RESULT]
                            root[KEY] = root[RESULT] = None
                            # now update the cache dictionary for the new links
                            try:
                                del cache[oldkey]
                            except KeyError:
                                pass
                            cache[key] = oldroot
                        else:
                            # put result in a new link at the front of the list
                            last = root[PREV]
                            link = [last, root, key, result]
                            last[NEXT] = root[PREV] = cache[key] = link
                        stats[L1_MISSES] += 1
                    return result
                else:
                    return result
            
        def l2wrapper(key, user_function, none_cache, *args, **kwds):
            result = l2cache.get(key)
            if result is not None:
                stats[L2_HITS] += 1
                return result

            result = user_function(*args, **kwds)
            if none_cache or result is not None:
                stats[L2_MISSES] += 1
                l2cache.add(key, result)
            return result   

        def cache_info():
            """Report cache statistics.  This only affects the instance cache and dose not
            impact data stored in l2 Cache"""
            with lock:
                return _CacheInfo(stats[L1_HITS], stats[L1_MISSES], stats[L2_HITS], stats[L2_MISSES], l1_maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics.  This only affects the instance cache and dose not
            impact data stored in l2 Cache"""
            with lock:
                cache.clear()
                root = nonlocal_root[0]
                root[:] = [root, root, None, None]
                stats[:] = [0, 0, 0, 0]
                
        def invalidate(*args, **kwds):
            """Delete a specific cache key if it exists"""
            key = make_key(user_function, args, kwds, typed, inst_attr=inst_attr)
            try:
                del cache[key]
            except:
                pass
            try:
                l2cache.delete(key)
            except:
                pass
            
        wrapper.__wrapped__ = user_function
        wrapper.invalidate = invalidate
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return update_wrapper(wrapper, user_function)

    return decorating_function