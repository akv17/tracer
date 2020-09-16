import sys
import inspect
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
from copy import copy
from time import time
from datetime import datetime
from collections import defaultdict


def _matches_root(root, path):
    return path.startswith(root.as_posix())


def _recognize_frame(root, frame):
    path = _get_frame_path(frame)
    return _matches_root(root, path)


def _get_frame_path(frame):
    return frame.f_code.co_filename


def _get_frame_qual_name(root, frame):
    path = frame.f_code.co_filename
    rel_path = Path(path).relative_to(root)
    qn = '.'.join(rel_path.parts[:-1])
    qn = f'{qn}.{frame.f_code.co_name}'
    return qn


def _get_frame_locals(frame):
    return copy(frame.f_locals)


def _get_frame_args(frame):
    args = copy(inspect.getargvalues(frame))
    args = {name: copy(args.locals[name]) for name in args.args}
    return args


@dataclass
class Call:
    frame: Any = None
    name: Any = None
    args: Any = None
    locals: Any = None
    retval: Any = None
    caller: Any = None
    num: Any = None
    call_timestamp: Any = field(default=None, repr=False)
    ret_timestamp: Any = field(default=None, repr=False)

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

    def as_table(self):
        content = []
        attrs = list(vars(self))
        props = [a for a in dir(self) if isinstance(getattr(self.__class__, a), property)]
        attrs += props
        for attr in attrs:
            val = getattr(self, attr)
            if attr == 'caller':
                val = val.uname
            content.append([str(attr), str(val)])
        return content


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

    def on_return(self, frame, retval):
        call = self.get_call_by_frame(frame)
        if call is None:
            msg = f'got return `{frame}` of untraced frame.'
            raise Exception(msg)

        call.locals = _get_frame_args(frame)
        call.ret_timestamp = time()
        call.retval = copy(retval)

    def create_tree(self):

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


def get_root_path(func):
    mod = func.__module__
    top_pkg = mod.split('.')[0]
    fpath = Path(func.__code__.co_filename)
    parts = fpath.parts
    try:
        top_pkg_ix = parts.index(top_pkg)
        root = Path(*parts[:top_pkg_ix])
        assert fpath.as_posix().startswith(root.as_posix())
        return root
    except (ValueError, AssertionError):
        msg = f'cannot setup tracing at entry `{mod}` at {fpath}.'
        raise Exception(msg)


def trace(func, args, kwargs=None):
    kwargs = kwargs or {}
    root = get_root_path(func)
    run = Run(root=root)

    def tracer(frame, event, arg):
        if _recognize_frame(root, frame):
            if event == 'call':
                run.on_call(frame)
            elif event == 'return':
                run.on_return(frame=frame, retval=copy(arg))

        return tracer

    sys.settrace(tracer)
    func(*args, **kwargs)
    sys.settrace(None)
    return run
