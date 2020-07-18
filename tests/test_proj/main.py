import typing

from tests.test_proj.foo import foo, Foo
from tests.test_proj.bar import bar, buzz

foo_obj = Foo()


def main(x):
    x = foo_obj.foo(x)
    x = bar(x)
    x = foo(x)
    x = buzz(x)
    return x
