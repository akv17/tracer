# Description
a pure python tool for runtime tracing of a particular value as an argument / return value of any callable.

# Example
- this is an extremely useful module `foo.py`. 
```
class Baz:

    def __init__(self, pw):
        self.pw = pw

    def __call__(self, val):
        return int(val ** self.pw)


def buzz(val):
    return -val


def bar(val, pw=2):
    return val ** pw


def foo(val):
    val = buzz(val)
    val = bar(val)
    val = Baz(pw=0.5)(val)
    val = buzz(val)
    return val
```
- this is an extremely useful tracing of integer value `2` when calling `foo.foo(val=-2)`.
```
>>> python tracer.py -e "foo.foo(val=-2)" -t 2 --ttype int
>>> cat traces.json
{
  "2": [
    {
      "target": 2,
      "func": "foo.buzz",
      "where": "return",
      "arg_name": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 22:13:38.995245",
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
      "timestamp": "2020-07-19 22:13:38.995307",
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
      "timestamp": "2020-07-19 22:13:38.995310",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.Baz.__call__",
      "where": "return",
      "arg_name": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 22:13:38.995373",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.buzz",
      "where": "kwargs",
      "arg_name": "val",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-19 22:13:38.995408",
      "matcher_type": "<class '__main__.EqualsMatcher'>",
      "stack": null
    }
  ]
}
```