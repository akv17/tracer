# Description
a pure python tool for runtime tracing of a particular value as an argument / return value of any callable.

# Example
- this is an extremely useful example of GUI usage.
```
from tracer.gui import TracerGUI
from tests.test_proj.main import main

tracer = TracerGUI()
tracer.trace(main, args=(2,))
```
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
- run an extremely useful tracing of int `2` when executing `foo.foo(val=-2)`.
```
from tracer import trace, EqualsMatcher
from foo import foo

trace(
    foo,
    args=(),
    kwargs={'val': -2},
    matchers=[EqualsMatcher(targets=[2])],
)
```
- finally, grab those extremely useful traces. 
```
>>> cat traces.json
{
  "2": [
    {
      "target": 2,
      "func": "foo.buzz",
      "where": "return",
      "identifier": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-26 00:05:26.481093",
      "matcher_type": "<class 'tracer.tracer.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.bar",
      "where": "kwargs",
      "identifier": "val",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-26 00:05:26.481154",
      "matcher_type": "<class 'tracer.tracer.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.bar",
      "where": "kwargs",
      "identifier": "pw",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-26 00:05:26.481157",
      "matcher_type": "<class 'tracer.tracer.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.Baz.__call__",
      "where": "return",
      "identifier": null,
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-26 00:05:26.481245",
      "matcher_type": "<class 'tracer.tracer.EqualsMatcher'>",
      "stack": null
    },
    {
      "target": 2,
      "func": "foo.buzz",
      "where": "kwargs",
      "identifier": "val",
      "value": 2,
      "type": "<class 'int'>",
      "timestamp": "2020-07-26 00:05:26.481288",
      "matcher_type": "<class 'tracer.tracer.EqualsMatcher'>",
      "stack": null
    }
  ]
}
```
# Limitations
- no tracing of nested functions
