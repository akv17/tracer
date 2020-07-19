# Description
a pure python tool for runtime tracing of a particular value as any function argument / return value.

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
>>> cat traces.json
{
  "2": [
    {
      "target": 2,
      "func": "foo.foo",
      "where": "return",
      "arg_name": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 20:00:54.969932",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.bar",
      "where": "kwargs",
      "arg_name": "val",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 20:00:54.970002",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.bar",
      "where": "kwargs",
      "arg_name": "pw",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 20:00:54.970006",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.baz",
      "where": "return",
      "arg_name": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 20:00:54.970075",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.foo",
      "where": "kwargs",
      "arg_name": "val",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 20:00:54.970116",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    }
  ]
}
```