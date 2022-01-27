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

    def add_caller(self, call):
        self.callers.append(call)

    def add_callee(self, call):
        self.callees.append(call)


@dataclass(frozen=True)
class Call:
    src: Function
    dst: Function
    num: int
    runtime: float


class Stats:

    def __init__(self, funcs):
        self._funcs = funcs

    @classmethod
    def from_profiler(cls, profiler):
        stats = pstats.Stats(profiler).stats  # noqa
        funcs = {}
        for dst, (*_, callers) in stats.items():
            if dst not in funcs:
                file, line, name = dst
                func = Function(name=name, file=file, line=line)
                funcs[dst] = func
            func_dst = funcs[dst]
            for src, (_, nc, _, ct) in callers.items():
                if src not in funcs:
                    file, line, name = src
                    func = Function(name=name, file=file, line=line)
                    funcs[src] = func
                func_src = funcs[src]
                call = Call(
                    src=func_src,
                    dst=func_dst,
                    num=nc,
                    runtime=ct,
                )
                func_src.add_callee(call)
                func_dst.add_caller(call)
        funcs = list(funcs.values())
        obj = cls(funcs)
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
            self._stats = Stats.from_profiler(self._profiler)
        self._profiler = None
        return False
