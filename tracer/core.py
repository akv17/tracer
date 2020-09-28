import os
import sys
import inspect
import re
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
from copy import copy
from time import time
from datetime import datetime
from collections import defaultdict
from functools import wraps

from .gui import TracerApp

__version__ = '1.0.1'

CLASS_NAME_REGEXP = re.compile(r'class\s+([\w_\d]+):')
SELF_ARG_REGEXP = re.compile(r'\(\s*self[\s,)]+')


def _get_root_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    path = os.path.abspath(path)
    root, _ = os.path.split(path)
    return Path(root)


def _matches_root(root, path):
    return path.startswith(root.as_posix())


def _recognize_frame(root, frame):
    path = _get_frame_path(frame)
    return _matches_root(root, path)


def _get_frame_path(frame):
    return os.path.abspath(frame.f_code.co_filename)


def _get_frame_locals(frame):
    return copy(frame.f_locals)


def _get_frame_args(frame):
    args = copy(inspect.getargvalues(frame))
    args = {name: copy(args.locals[name]) for name in args.args}
    return args


def _find_method_class_name(lines):
    for ln in reversed(lines):
        if ln.strip().startswith('class'):
            match = CLASS_NAME_REGEXP.search(ln)
            if match is not None:
                cn = match.group(1)
                return cn


def _is_any_method(first_lineno, lines):
    if not lines:
        return False

    first_line = lines[first_lineno]
    if SELF_ARG_REGEXP.search(first_line) is not None:
        return True
    for ln in lines[first_lineno:]:
        ln = ln.strip()
        if ln.startswith('@staticmethod') or ln.startswith('@classmethod'):
            return True
        elif not ln.startswith('@'):
            return False


def _get_frame_local_name(frame):
    fp = frame.f_code.co_filename
    with open(fp, 'r') as f:
        lines = f.readlines()

    frame_name = frame.f_code.co_name
    first_lineno = frame.f_code.co_firstlineno - 1

    if _is_any_method(first_lineno=first_lineno, lines=lines):
        lines = lines[:first_lineno]
        cls_name = _find_method_class_name(lines)
        if cls_name is None:
            msg = f'could not find class name of method frame `{frame}`.'
            raise Exception(msg)
        frame_name = f'{cls_name}.{frame_name}'

    return frame_name


def _get_frame_qual_name(root, frame):
    if not os.path.exists(frame.f_code.co_filename):
        return frame.f_code.co_filename

    frame_name = _get_frame_local_name(frame)
    path = _get_frame_path(frame)
    path = Path(path)

    # when this func is used to get caller's name,
    # sometimes caller might not be located under the `root`
    # (i.e. first call of entry point done from `[...]/tracer.core`).
    try:
        path = path.relative_to(root)
    except ValueError:
        return frame_name

    path_name = '.'.join(path.parts[:-1])
    if path_name:
        frame_name = f'{path_name}.{frame_name}'
    return frame_name


@dataclass
class Line:
    frame: Any = field(default=None, repr=False)
    num: Any = None
    src: Any = None
    locals: Any = field(default_factory=dict, repr=False)


@dataclass
class Call:
    frame: Any = field(default=None, repr=False)
    name: Any = None
    args: Any = None
    locals: Any = field(default_factory=dict, repr=False)
    retval: Any = None
    caller: Any = None
    num: Any = None
    call_timestamp: Any = field(default=None, repr=False)
    ret_timestamp: Any = field(default=None, repr=False)
    lines: Any = field(default_factory=dict, repr=False)

    @property
    def calltime(self):
        if self.call_timestamp is not None:
            return datetime.fromtimestamp(self.call_timestamp)
        return -1

    @property
    def rettime(self):
        if self.call_timestamp is not None:
            return datetime.fromtimestamp(self.ret_timestamp)
        return -1

    @property
    def runtime(self):
        if self.call_timestamp is not None and self.ret_timestamp is not None:
            return round(self.ret_timestamp - self.call_timestamp, 5)
        return -1

    @property
    def id(self):
        return id(self.frame)

    @property
    def uname(self):
        return f'{self.name}:{self.id}'

    def add_line(self, line):
        self.lines[line.num] = line

    def get_line(self, num):
        return self.lines.get(num)


@dataclass
class Run:
    root: Any = None
    frames: Any = field(default_factory=list)
    calls: Any = field(default_factory=list)
    _calls_frame_map: Any = field(default_factory=lambda: defaultdict(list))
    _calls_uname_map: Any = field(default_factory=dict)

    def __len__(self):
        return len(self.calls)

    def add_call(self, call):
        call.num = len(self)
        self.calls.append(call)
        self._calls_frame_map[id(call.frame)] = call
        self._calls_uname_map[call.uname] = call

    def get_call_by_frame(self, frame):
        return self._calls_frame_map.get(id(frame))

    def get_call_by_uname(self, uname):
        return self._calls_uname_map.get(uname)

    def _get_caller_call(self, frame):
        caller_frame = frame.f_back
        call = self.get_call_by_frame(caller_frame)
        if call is None:
            name = _get_frame_qual_name(root=self.root, frame=caller_frame)
            call = Call(frame=caller_frame, name=name)
        return call

    def on_call(self, frame):
        name = _get_frame_qual_name(self.root, frame)
        args = _get_frame_args(frame)
        call_timestamp = time()
        caller_call = self._get_caller_call(frame)
        call = Call(
            frame=frame,
            name=name,
            args=args,
            call_timestamp=call_timestamp,
            caller=caller_call
        )
        self.add_call(call)

    def on_line(self, frame):
        locals_ = _get_frame_locals(frame)
        num = frame.f_lineno
        with open(frame.f_code.co_filename, 'r') as f:
            lines = f.readlines()
            src = lines[num - 1] if lines else ''

        ln = Line(frame=frame, num=num, src=src, locals=locals_)
        call = self.get_call_by_frame(frame)
        call.add_line(ln)

    def on_return(self, frame, retval):
        call = self.get_call_by_frame(frame)
        if call is None:
            msg = f'got return `{frame}` of untraced frame.'
            raise Exception(msg)

        call.locals = _get_frame_locals(frame)
        call.ret_timestamp = time()
        call.retval = copy(retval)

    def create_tree_data(self):

        def insert_level(cache, accum, name):
            leaves = cache[name]
            if not leaves:
                accum[name] = {}
                return

            accum[name] = {}
            accum = accum[name]
            for sub_name in leaves:
                insert_level(cache=cache, accum=accum, name=sub_name)

        cache = defaultdict(list)
        for c in self.calls:
            cache[c.caller.uname].append(c.uname)

        if not cache:
            return {}

        accum = {}
        keys = list(cache.keys())
        root = keys[0]
        for name in keys:
            insert_level(cache=cache, accum=accum, name=name)
        data = accum[root]
        return data


def trace(func):
    path = func.__code__.co_filename
    root = _get_root_path(path)
    run = Run(root=root)

    def tracer(frame, event, arg):
        if _recognize_frame(root, frame):
            if event == 'call':
                run.on_call(frame)
            elif event == 'line':
                run.on_line(frame)
            elif event == 'return':
                run.on_return(frame=frame, retval=copy(arg))

        return tracer

    @wraps(func)
    def wrapper(*args, **kwargs):
        sys.settrace(tracer)
        rv = func(*args, **kwargs)
        sys.settrace(None)
        app = TracerApp(run)
        app.exec()
        return rv

    return wrapper
