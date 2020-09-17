# Description
a pure python tool for runtime tracing of a particular value as an argument / return value of any callable.

# Example
- this is an extremely useful example of tracing.
```
from tracer.gui_qt import Tracer
from tests.test_proj.main import main

tracer = Tracer()
tracer.trace(main, args=(2,))
```
![](examples/example.jpg)