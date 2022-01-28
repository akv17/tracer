import cProfile
import pstats
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Function:
    name: str
    file: str = field(repr=False)
    line: int = field(repr=False)
    callers: Any = field(repr=False, default_factory=list)
    callees: Any = field(repr=False, default_factory=list)
    _runtime_inner: float = field(default=None, repr=False)

    def set_inner_runtime(self, value):
        object.__setattr__(self, '_runtime_inner', value)

    def add_caller(self, call):
        self.callers.append(call)

    def add_callee(self, call):
        self.callees.append(call)

    @property
    def runtime(self):
        value = self._runtime_inner + sum([c.runtime for c in self.callees] or [0])
        return value


@dataclass(frozen=True)
class Call:
    src: Function
    dst: Function
    num: int
    runtime: float


class Stats:

    def __init__(self, funcs):
        self._funcs = funcs


def _create_stats_from_profiler(profiler):
    stats = pstats.Stats(profiler).stats  # noqa
    funcs = {}
    for dst, (_, nc, tt, ct, callers) in stats.items():
        if dst not in funcs:
            file, line, name = dst
            func = Function(
                name=name,
                file=file,
                line=line,
            )
            funcs[dst] = func
        func_dst = funcs[dst]
        func_dst.set_inner_runtime(tt)
        for src, (_, nc_, tt_, ct_) in callers.items():
            if src not in funcs:
                file, line, name = src
                func = Function(
                    name=name,
                    file=file,
                    line=line,
                )
                funcs[src] = func
            func_src = funcs[src]
            call = Call(
                src=func_src,
                dst=func_dst,
                runtime=ct_,
                num=nc_,
            )
            func_src.add_callee(call)
            func_dst.add_caller(call)
    funcs = list(funcs.values())
    obj = Stats(funcs)
    return obj


class Profile:

    def __init__(self):
        self._profiler = None
        self._stats = None

    def __enter__(self):
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._profiler.disable()
        if exc_type is None:
            self._stats = _create_stats_from_profiler(self._profiler)
        self._profiler = None
        return False
