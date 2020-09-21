import typing

from tests.test_proj.foo import foo, Foo
from tests.test_proj.bar import bar, buzz
from tracer import trace
foo_obj = Foo()


@trace
def main(x, y=-1, z=(None,)):
    x = foo_obj.foo(x)
    x = bar(x)
    x = foo(x)
    x = buzz(x)
    x = foo_obj(x)
    # just to test correct binding of staticmethods's sigs.
    foo_obj.bar(0x0)
    unused = 0x0
    return x


if __name__ == '__main__':
    rv = main(2)
    print(rv)
