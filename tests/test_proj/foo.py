def foo(x):
    return -x


class Foo:

    def __call__(self, x):
        return x + 1

    def foo(self, x):
        return -x
