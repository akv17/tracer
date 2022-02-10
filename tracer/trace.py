import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Line:
    file: str
    func: str
    lineno: int
    vars: dict = field(repr=False)


@dataclass(frozen=True)
class Call:
    file: str
    func: str
    lines: list = field(repr=False, default_factory=list)
    rv: Any = field(repr=False, default=None)
    exc: Any = field(repr=False, default=None)

    def add_line(self, obj):
        self.lines.append(obj)

    def set_rv(self, value):
        object.__setattr__(self, 'rv', value)

    def set_exc(self, e):
        object.__setattr__(self, 'exc', e)


class Stack:

    def __init__(self):
        self._stack = []
        self._order = []

    def __iter__(self):
        return iter(self._order)

    def peek(self):
        return self._stack[-1] if self._stack else None

    def push_call(self, obj):
        self._stack.append(obj)
        self._order.append(obj)

    def push_line(self, obj):
        call = self.peek()
        assert call is not None
        call.add_line(obj)

    def pop_call(self):
        return self._stack.pop()


class Trace:

    def __init__(self):
        self._stack = None
        self._saved_trace_func = None

    @property
    def traces(self):
        rv = list(self._stack or [])
        return rv

    def __enter__(self):
        self._stack = Stack()
        self._saved_trace_func = sys.gettrace()
        sys.settrace(self._trace_func)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.settrace(self._saved_trace_func)
        return False

    def _should_trace(self, func_name, file_name):
        return True

    def _trace_func(self, frame, event, arg):
        file_name = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        flag = self._should_trace(func_name=func_name, file_name=file_name)
        if not flag:
            return None
        if event == 'call':
            call = Call(file=file_name, func=func_name)
            self._stack.push_call(call)
        elif event == 'line':
            line = Line(
                file=file_name,
                func=func_name,
                lineno=frame.f_lineno,
                vars=frame.f_locals.copy()
            )
            self._stack.push_line(line)
        elif event == 'return':
            call = self._stack.pop_call()
            call.set_rv(arg)
        elif event == 'exception':
            call = self._stack.pop_call()
            call.set_exc(arg)
        else:
            pass
        return self._trace_func
