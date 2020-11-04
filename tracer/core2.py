import sys
import importlib
import inspect
import json
import logging
import os
import re
from abc import abstractmethod
from collections import deque
from datetime import datetime
from functools import wraps
from types import FunctionType, MethodType
from copy import copy
from pathlib import Path
from time import time
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any

# from tracer.core import Run


class _LoggingMixin:
    LEVEL = logging.INFO
    FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setFormatter(FORMATTER)
    LOG_CALLS = False
    LOG_MATCHING_EXC = False
    _UNBOUND_LOGGER = None

    @staticmethod
    def logger():
        if _LoggingMixin._UNBOUND_LOGGER is None:
            logger = logging.getLogger(__name__)
            logger.setLevel(_LoggingMixin.LEVEL)
            logger.addHandler(_LoggingMixin.STREAM_HANDLER)
            _LoggingMixin._UNBOUND_LOGGER = logger
        return _LoggingMixin._UNBOUND_LOGGER

    @property
    def _logger(self):
        return self._get_logger()

    def _get_logger(self):
        if not hasattr(self, '__logger'):
            cls = self.__class__
            name = f'{cls.__module__}.{cls.__name__}'
            self.__logger = logging.getLogger(name)
            self.__logger.setLevel(self.LEVEL)
            self.__logger.addHandler(self.STREAM_HANDLER)

        return self.__logger


CLASS_NAME_REGEXP = re.compile(r'class\s+([\w_\d]+):')
SELF_ARG_REGEXP = re.compile(r'\(\s*self[\s,)]+')


def _is_dunder_name(name):
    return name.startswith('__') and name.endswith('__')


def _is_staticmethod(obj):
    prms = inspect.signature(obj).parameters
    return 'self' not in prms and not isinstance(obj, MethodType)


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


def _find_method_class_name(lines):
    for ln in reversed(lines):
        if ln.strip().startswith('class'):
            match = CLASS_NAME_REGEXP.search(ln)
            if match is not None:
                cn = match.group(1)
                return cn


def _get_obj_name(obj):
    mod_name = obj.__module__ if hasattr(obj, '__module__') else ''
    if hasattr(obj, '__qualname__'):
        name = obj.__qualname__
    elif hasattr(obj, '__name__'):
        name = obj.__name__
    else:
        name = repr(obj)
    return f'{mod_name}.{name}'


def _get_root_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    path = os.path.abspath(path)
    root, _ = os.path.split(path)
    return Path(root)


def _path_matches_root(root, path):
    return path.startswith(root.as_posix())


def _is_target_frame(root, frame):
    path = _get_frame_path(frame)
    return _path_matches_root(root, path)


def _get_obj_path(obj):
    return os.path.abspath(obj.__code__.co_filename)


def _get_frame_path(frame):
    return os.path.abspath(frame.f_code.co_filename)


def _get_frame_locals(frame):
    return copy(frame.f_locals)


def _get_frame_args(frame):
    args = copy(inspect.getargvalues(frame))
    args = {name: copy(args.locals[name]) for name in args.args}
    return args


def _get_frame_local_name(frame):
    fp = _get_frame_path(frame)
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


def _get_caller_frame():
    stack = inspect.stack()
    names = [f.function for f in stack]
    try:
        wrapper_idx = names.index('__trace_wrapper__')
    except ValueError:
        msg = 'no `__trace_wrapper__` in stack.'
        raise Exception(msg)

    caller_idx = wrapper_idx + 1
    caller_frame = stack[caller_idx].frame
    return caller_frame


# =========
# = PATHS =
# =========

def _path_to_name(path):
    if not os.path.exists(path):
        msg = f'path does not exist `{path}`.'
        raise Exception(msg)
    name, ext = os.path.splitext(path)
    if ext != '.py':
        msg = f'cannot convert non .py path `{path}`.'
        raise Exception(msg)
    name = name.replace(os.path.sep, '.')
    return name


def _name_to_path(name):
    return name.replace('.', os.path.sep) + '.py'


@dataclass
class Paths:
    entry_fp: str
    entry_root: str
    proj_root: str
    targets: set = field(default_factory=set)

    def is_target(self, path):
        path = os.path.abspath(path)
        print(path, self.targets)
        return any(path.startswith(tp) for tp in self.targets)

    def is_target_name(self, name):
        path = _name_to_path(name)
        return self.is_target(path)


def _create_paths(entry_fp, targets_prefixes=None):
    targets_prefixes = targets_prefixes or []
    if not entry_fp:
        msg = 'got empty entry path.'
        raise Exception(msg)
    if entry_fp == '.':
        entry_root = os.path.abspath(entry_fp)
        proj_root = entry_root
    else:
        path_parts = entry_fp.split(os.path.sep)
        entry_root = os.path.abspath(path_parts[0])
        proj_root, _ = os.path.split(entry_root)
    targets = {entry_root}
    for pref in targets_prefixes:
        tp = os.path.abspath(pref)
        if not os.path.exists(tp):
            _LoggingMixin.logger().warning(f'target path does not exist: `{tp}`.')
        else:
            targets.add(tp)
    paths = Paths(
        entry_fp=entry_fp,
        entry_root=entry_root,
        proj_root=proj_root,
        targets=targets
    )
    return paths



# MODULE TREE

# class KnownPackagesMixin:
#
#     def __init__(self, top_package, known_packages=None):
#         self.top_package = top_package
#         self.known_packages = known_packages or set()
#         self.known_packages = set(self.known_packages)
#         self.known_packages.add(self.top_package)
#
#     def is_known_package(self, name):
#         return name in self.known_packages
#
#     def is_from_known_package(self, name):
#         return any(name.startswith(pkg) for pkg in self.known_packages)


# ===============
# = MODULE TREE =
# ===============


class ModuleTree(_LoggingMixin):

    # def __init__(
    #     self,
    #     root,
    #     top_package,
    #     entry_func_name,
    #     entry_mod_name,
    #     known_packages=None
    # ):
    #     super().__init__(top_package=top_package, known_packages=known_packages)
    #     self.root = root
    #     self.entry_func_name = entry_func_name
    #     self.entry_mod_name = entry_mod_name
    #     self.entry_mod = None
    #     self._imported = set()

    def __init__(self, paths):
        self.paths = paths
        self._imported = set()

    def _resolve_relative_import(self, from_name, what_name, is_init_mod=False):
        if what_name.count('.') > 1:
            msg = f'got multi-level relative import `{what_name}` in module `{from_name}`, ignoring.'
            self._logger.warning(msg)
            return ''

        if not is_init_mod:
            from_name = '.'.join(from_name.split('.')[:-1])

        resolved_name = f'{from_name}.{what_name.lstrip(".")}'
        msg = f'resolving relative import `{what_name}` in module `{from_name}` as `{resolved_name}`.'
        self._logger.warning(msg)
        return resolved_name

    def _parse_mod_imports(self, src, mod_name, is_init_mod=False):
        imports = []
        for ln in src.split('\n'):
            ln = ln.strip()
            if ln.startswith('import') or ln.startswith('from'):
                name = ln.split()[1]
                if name.startswith('.'):
                    name = self._resolve_relative_import(
                        from_name=mod_name,
                        what_name=name,
                        is_init_mod=is_init_mod
                    )
                if self.paths.is_target_name(name):
                    imports.append(name)

        return imports

    def _get_mod_path(self, mod_name):
        mod_path = mod_name.replace('.', os.path.sep) + '.py'

        if not os.path.exists(mod_path):
            self._logger.debug(f'guessing __init__ of module `{mod_name}`.')
            mod_path, _ = os.path.splitext(mod_path)
            mod_path = os.path.join(mod_path, '__init__.py')

        if not os.path.exists(mod_path):
            msg = f'no module `{mod_name}` at inferred path `{mod_path}`.'
            raise Exception(msg)

        return mod_path

    def _get_imports(self, mod_name):
        mod_path = self._get_mod_path(mod_name)
        is_init_mod = mod_path.endswith('__init__.py')

        with open(mod_path, 'r') as f:
            src = f.read()
            imps = self._parse_mod_imports(src, mod_name=mod_name, is_init_mod=is_init_mod)
        return imps

    def _import_mod(self, mod_name):
        if mod_name in self._imported:
            return None

        mod = importlib.import_module(mod_name)
        self._imported.add(mod_name)
        self._logger.debug(f'imported module `{mod_name}`.')
        return mod

    def __iter__(self):
        imports = deque([_path_to_name(self.paths.entry_fp)])
        while imports:
            mod_name = imports.popleft()
            mod = self._import_mod(mod_name)

            if mod is None:
                continue

            yield mod

            mod_imports = self._get_imports(mod_name)
            imports.extend(mod_imports)

            # if self.entry_mod is None:
            #     self.entry_mod = mod


def _setup(entry_fp, targets=None):
    _LoggingMixin.LEVEL = logging.DEBUG
    paths = _create_paths(entry_fp=entry_fp, targets_prefixes=targets)
    tree = ModuleTree(paths)
    for m in tree:
        pass