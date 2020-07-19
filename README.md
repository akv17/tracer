# Description
a pure python tool for runtime tracing of a particular value as any function argument.

# Example
- this is an extremely useful module `foo.py`. 
```
def foo(val):
    return -val


def bar(val, pw=2):
    return val ** pw


def baz(val):
    return int(val ** 0.5)


def buzz(val):
    val = foo(val)
    val = bar(val)
    val = baz(val)
    val = foo(val)
    return val
```
- this is an extremely useful tracing of integer value `2` when calling `foo.buzz(val=-2)`.
```
>>> python tracer.py -e "foo.buzz(val=-2)" -t 2 --ttype int
{
  "2": [
    {
      "obj_name": "foo.bar",
      "arg_name": "val",
      "target": 2,
      "value": 2,
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "timestamp": "2020-07-19 16:55:37.171571",
      "arg_type": "<class 'int'>",
      "stack": null
    },
    {
      "obj_name": "foo.bar",
      "arg_name": "pw",
      "target": 2,
      "value": 2,
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "timestamp": "2020-07-19 16:55:37.171578",
      "arg_type": "<class 'int'>",
      "stack": null
    },
    {
      "obj_name": "foo.foo",
      "arg_name": "val",
      "target": 2,
      "value": 2,
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "timestamp": "2020-07-19 16:55:37.171681",
      "arg_type": "<class 'int'>",
      "stack": null
    }
  ]
}
```