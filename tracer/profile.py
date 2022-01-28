import os
import inspect
import cProfile
import pstats
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Function:
    name: str
    module: str
    file: str = field(repr=False)
    line: int = field(repr=False)
    num_calls: int = field(repr=False)
    _runtime_inner: float = field(repr=False)
    callers: Any = field(repr=False, default_factory=list)
    callees: Any = field(repr=False, default_factory=list)

    @property
    def id(self):
        return self.file, self.line, self.name

    @property
    def runtime(self):
        value = self._runtime_inner + sum([c.runtime for c in self.callees] or [0])
        return value

    @property
    def qualname(self):
        rv = self.name if self.module == '<builtins>' else f'{self.module}.{self.name}'
        return rv

    def add_caller(self, call):
        self.callers.append(call)

    def add_callee(self, call):
        self.callees.append(call)


@dataclass(frozen=True)
class Call:
    src: Function
    dst: Function
    num_calls: int
    runtime: float


class Stats:

    def __init__(self, funcs):
        self._funcs = funcs

    def list_funcs(self):
        return self._funcs


class _CreateStatsCommand:

    def __init__(self, profiler, fs_root):
        self.profiler = profiler
        self.fs_root = fs_root
        self.pstats = pstats.Stats(profiler).stats  # noqa

    def __call__(self):
        funcs = self._create_funcs()
        funcs = self._set_calls(funcs)
        stats = Stats(funcs)
        return stats

    def _create_module_name(self, file):
        if file == '~':
            mod = '<builtins>'
        elif self.fs_root not in file:
            # TODO: figure out real module
            mod = '<packages>'
        else:
            mod = file.replace(self.fs_root, '')
            mod = mod.lstrip(os.path.sep)
            mod = mod.replace('.py', '')
            mod = '.'.join(mod.split(os.path.sep))
        return mod

    def _create_funcs(self):
        funcs = []
        for id_, (_, nc, tt, _, callers) in self.pstats.items():
            file, line, name = id_
            mod_name = self._create_module_name(file)
            func = Function(
                name=name,
                file=file,
                line=line,
                num_calls=nc,
                module=mod_name,
                _runtime_inner=tt
            )
            funcs.append(func)
        return funcs

    def _set_calls(self, funcs):
        funcs_map = {f.id: f for f in funcs}
        for dst_id, (*_, callers) in self.pstats.items():
            func_dst = funcs_map[dst_id]
            for src_id, (_, nc_, _, ct_) in callers.items():
                func_src = funcs_map[src_id]
                call = Call(
                    src=func_src,
                    dst=func_dst,
                    runtime=ct_,
                    num_calls=nc_,
                )
                func_src.add_callee(call)
                func_dst.add_caller(call)
        return funcs


class Profile:

    def __init__(self):
        self.stats = None
        self._profiler = None
        self._fs_root = None

    def __enter__(self):
        self._set_fs_root()
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._profiler.disable()
        if exc_type is None:
            self.stats = _CreateStatsCommand(
                profiler=self._profiler,
                fs_root=self._fs_root
            )()
        self._profiler = None
        self._fs_root = None
        return False

    def _set_fs_root(self):
        # frames:
        #   0: here
        #   1: self.__enter__
        #   2: Profile entry point
        caller = inspect.stack()[2]
        root, _ = os.path.split(caller.filename)
        self._fs_root = root
