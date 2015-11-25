# -*- coding: utf-8 -*-

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import abc
import collections
import copy
from itertools import permutations
import pickle
import sys
from weakref import proxy
from random import choice
from django.test import TestCase

from caching import utils

def capture(*args, **kw):
    """capture all positional and keyword arguments"""
    return args, kw


def signature(part):
    """ return the signature of a partial object """
    return (part.func, part.args, part.keywords, part.__dict__)


class TestLRU(TestCase):
    def test_lru(self):
        def orig(x, y):
            return 3 * x + y
        f = utils.lruL2Cache(maxsize=20, l2cache_name='dummy')(orig)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(maxsize, 20)
        self.assertEqual(currsize, 0)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 0)

        domain = range(5)
        for i in range(1000):
            x, y = choice(domain), choice(domain)
            actual = f(x, y)
            expected = orig(x, y)
            print u"{i}: 3 * {x} + {y} = {actual}, expected: {expected}".format(i=i, x=x, y=y, actual=actual, expected=expected)
            self.assertEqual(actual, expected)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertTrue(hits > misses)
        self.assertEqual(hits + misses, 1000)
        self.assertEqual(currsize, 20)

        f.cache_clear()   # test clearing
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 0)
        self.assertEqual(currsize, 0)
        f(x, y)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

        # Test bypassing the cache
        self.assertIs(f.__wrapped__, orig)
        f.__wrapped__(x, y)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

        # test size zero (which means "never-cache")
        global f_cnt
        @utils.lruL2Cache(maxsize=0, l2cache_name='dummy')
        def f():
            global f_cnt
            f_cnt += 1
            return 20
        self.assertEqual(f.cache_info().maxsize, 0)
        f_cnt = 0
        for i in range(5):
            self.assertEqual(f(), 20)
        self.assertEqual(f_cnt, 5)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 5)
        self.assertEqual(currsize, 0)

        # test size one
        @utils.lruL2Cache(maxsize=1, l2cache_name='dummy')
        def f():
            global f_cnt
            f_cnt += 1
            return 20
        self.assertEqual(f.cache_info().maxsize, 1)
        f_cnt = 0
        for i in range(5):
            self.assertEqual(f(), 20)
        self.assertEqual(f_cnt, 1)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 4)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

        # test size two
        @utils.lruL2Cache(maxsize=2, l2cache_name='dummy')
        def f(x):
            global f_cnt
            f_cnt += 1
            return x*10
        self.assertEqual(f.cache_info().maxsize, 2)
        f_cnt = 0
        for x in 7, 9, 7, 9, 7, 9, 8, 8, 8, 9, 9, 9, 8, 8, 8, 7:
            #    *  *              *                          *
            self.assertEqual(f(x), x*10)
        self.assertEqual(f_cnt, 4)
        hits, misses, maxsize, currsize = f.cache_info()
        self.assertEqual(hits, 12)
        self.assertEqual(misses, 4)
        self.assertEqual(currsize, 2)

    def test_lru_with_maxsize_none(self):
        @utils.lruL2Cache(maxsize=None, l2cache_name='dummy')
        def fib(n):
            if n < 2:
                return n
            return fib(n-1) + fib(n-2)
        self.assertEqual([fib(n) for n in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610])
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=28, misses=16, maxsize=None, currsize=16))
        fib.cache_clear()
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=0, misses=0, maxsize=None, currsize=0))

    def test_l2_with_lru_maxsize_zero(self):
        @utils.lruL2Cache(maxsize=0)
        def fib(n):
            if n < 2:
                return n
            return fib(n-1) + fib(n-2)
        self.assertEqual([fib(n) for n in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610])
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=0, misses=16, maxsize=0, currsize=0))
        fib.cache_clear()
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=0, misses=0, maxsize=0, currsize=0))

    # def test_lru_with_maxsize_negative(self):
    #     @utils.lruL2Cache(maxsize=-10)
    #     def eq(n):
    #         return n
    #     for i in (0, 1):
    #         self.assertEqual([eq(n) for n in range(150)], list(range(150)))
    #     self.assertEqual(eq.cache_info(),
    #         utils._CacheInfo(hits=0, misses=300, maxsize=-10, currsize=1))
    #
    # def test_lru_with_exceptions(self):
    #     # Verify that user_function exceptions get passed through without
    #     # creating a hard-to-read chained exception.
    #     # http://bugs.python.org/issue13177
    #     for maxsize in (None, 128):
    #         @utils.lruL2Cache(maxsize=maxsize, l2cache_name='dummy')
    #         def func(i):
    #             return 'abc'[i]
    #         self.assertEqual(func(0), 'a')
    #         with self.assertRaises(IndexError) as cm:
    #             func(15)
    #         self.assertIsNone(cm.exception.__context__)
    #         # Verify that the previous exception did not result in a cached entry
    #         with self.assertRaises(IndexError):
    #             func(15)

    def test_lru_with_types(self):
        for maxsize in (None, 128):
            @utils.lruL2Cache(maxsize=maxsize, typed=True, l2cache_name='dummy')
            def square(x):
                return x * x
            self.assertEqual(square(3), 9)
            self.assertEqual(type(square(3)), type(9))
            self.assertEqual(square(3.0), 9.0)
            self.assertEqual(type(square(3.0)), type(9.0))
            self.assertEqual(square(x=3), 9)
            self.assertEqual(type(square(x=3)), type(9))
            self.assertEqual(square(x=3.0), 9.0)
            self.assertEqual(type(square(x=3.0)), type(9.0))
            self.assertEqual(square.cache_info().hits, 4)
            self.assertEqual(square.cache_info().misses, 4)

    def test_lru_with_keyword_args(self):
        @utils.lruL2Cache(l2cache_name='dummy')
        def fib(n):
            if n < 2:
                return n
            return fib(n=n-1) + fib(n=n-2)
        self.assertEqual(
            [fib(n=number) for number in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]
        )
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=28, misses=16, maxsize=128, currsize=16))
        fib.cache_clear()
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=0, misses=0, maxsize=128, currsize=0))

    def test_lru_with_keyword_args_maxsize_none(self):
        @utils.lruL2Cache(maxsize=None, l2cache_name='dummy')
        def fib(n):
            if n < 2:
                return n
            return fib(n=n-1) + fib(n=n-2)
        self.assertEqual([fib(n=number) for number in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610])
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=28, misses=16, maxsize=None, currsize=16))
        fib.cache_clear()
        self.assertEqual(fib.cache_info(),
            utils._CacheInfo(hits=0, misses=0, maxsize=None, currsize=0))

    def test_lru_method(self):
        class X(int):
            f_cnt = 0
            @utils.lruL2Cache(maxsize=2, l2cache_name = 'dummy')
            def f(self, x):
                self.f_cnt += 1
                return x*10+self
        a = X(5)
        b = X(5)
        c = X(7)
        self.assertEqual(X.f.cache_info(), (0, 0, 2, 0))

        for x in 1, 2, 2, 3, 1, 1, 1, 2, 3, 3:
            self.assertEqual(a.f(x), x*10 + 5)
        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 0, 0))
        self.assertEqual(X.f.cache_info(), (4, 6, 2, 2))

        for x in 1, 2, 1, 1, 1, 1, 3, 2, 2, 2:
            self.assertEqual(b.f(x), x*10 + 5)
        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 4, 0))
        self.assertEqual(X.f.cache_info(), (10, 10, 2, 2))

        for x in 2, 1, 1, 1, 1, 2, 1, 3, 2, 1:
            self.assertEqual(c.f(x), x*10 + 7)
        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 4, 5))
        self.assertEqual(X.f.cache_info(), (15, 15, 2, 2))

        self.assertEqual(a.f.cache_info(), X.f.cache_info())
        self.assertEqual(b.f.cache_info(), X.f.cache_info())
        self.assertEqual(c.f.cache_info(), X.f.cache_info())

    # def test_pickle(self):
    #     cls = self.__class__
    #     for f in cls.cached_func[0], cls.cached_meth, cls.cached_staticmeth:
    #         for proto in range(pickle.HIGHEST_PROTOCOL + 1):
    #             with self.subTest(proto=proto, func=f):
    #             f_copy = pickle.loads(pickle.dumps(f, proto))
    #             self.assertIs(f_copy, f)
    #
    # def test_copy(self):
    #     cls = self.__class__
    #     for f in cls.cached_func[0], cls.cached_meth, cls.cached_staticmeth:
    #         with self.subTest(func=f):
    #             f_copy = copy.copy(f)
    #             self.assertIs(f_copy, f)
    #
    # def test_deepcopy(self):
    #     cls = self.__class__
    #     for f in cls.cached_func[0], cls.cached_meth, cls.cached_staticmeth:
    #         with self.subTest(func=f):
    #             f_copy = copy.deepcopy(f)
    #             self.assertIs(f_copy, f)


@utils.lruL2Cache(l2cache_name = 'dummy')
def py_cached_func(x, y):
    return 3 * x + y


class TestLRUPy(TestLRU):
    module = utils
    cached_func = py_cached_func,

    @utils.lruL2Cache(l2cache_name = 'dummy')
    def cached_meth(self, x, y):
        return 3 * x + y

    @staticmethod
    @utils.lruL2Cache(l2cache_name = 'dummy')
    def cached_staticmeth(x, y):
        return 3 * x + y

# need to add tests for l2_cache, combined cache, cache_none