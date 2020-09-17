from tests.test_proj.baz.baz import buzz


def zzz(x, zz=0):
    return x


def bar(y, scale=2):
    y = zzz(y)
    return y ** scale
