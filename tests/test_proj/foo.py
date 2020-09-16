def foo(x):
    return -x


class Foo:

    def __call__(self, x):
        return x + 1

    def foo(self, x):
        x = -x
        return x

    @staticmethod
    def bar(x):
        return x
