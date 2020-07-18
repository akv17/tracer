import os
import importlib
import logging
from functools import wraps
from collections import deque
from types import FunctionType


def _is_dunder(name):
    return name.startswith('__') and name.endswith('__')


def _spawn_cls_logger(cls, level=logging.DEBUG):
    logging.basicConfig()
    logger = logging.getLogger(cls.__name__)
    logger.setLevel(level)
    return logger


class ProjectTree:

    def __init__(self, entry_mod_name, project_root='src'):
        self.entry_mod_name = entry_mod_name
        self.project_root = project_root
        self.entry_mod = None
        self._cur_mod_name = entry_mod_name
        self._logger = _spawn_cls_logger(self.__class__)

    def _parse_mod_imports(self, src):
        names = []
        for ln in src.split('\n'):
            ln = ln.strip()
            if ln.startswith('import') or ln.startswith('from'):
                name = ln.split()[1]
                if name.startswith(self.project_root):
                    names.append(name)
        return names

    def _get_imports(self, mod_name):
        mod_path = mod_name.replace('.', os.path.sep) + '.py'
        with open(mod_path, 'r') as f:
            src = f.read()
            imps = self._parse_mod_imports(src)
        return imps

    def __iter__(self):
        imports = deque([self.entry_mod_name])
        while imports:
            mod_name = imports.popleft()
            mod = importlib.import_module(mod_name)
            self._logger.debug(f'visiting mod `{mod_name}`.')
            yield mod

            mod_imports = self._get_imports(mod_name)
            imports.extend(mod_imports)

            if self.entry_mod is None:
                self.entry_mod = mod


class Patcher:

    def __init__(self, targets):
        self.targets = targets
        self._logger = _spawn_cls_logger(self.__class__)
        self._already_wrapped = set()

    def _match_targets(self, obj_name, *args, **kwargs):
        for i, a in enumerate(args):
            for t in self.targets:
                if a == t:
                    self._logger.debug(f'matched target `{t}` as argument {i} when tracing `{obj_name}`.')

        for k, v in kwargs.items():
            for t in self.targets:
                if v == t:
                    self._logger.debug(f'matched target `{t}` as keyword argument `{k}` when tracing `{obj_name}`.')

    def _wrap(self, obj):
        obj_name = self._get_full_obj_name(obj)

        @wraps(obj)
        def wrapper(*args, **kwargs):
            self._logger.debug(f'tracing `{obj_name}`.')
            rv = obj(*args, **kwargs)
            self._match_targets(obj_name, *args, **kwargs)
            return rv

        return wrapper

    @staticmethod
    def _get_full_obj_name(obj):
        if hasattr(obj, '__qualname__'):
            name = obj.__qualname__
        elif hasattr(obj, '__name__'):
            name = obj.__name__
        else:
            name = repr(obj)
        return f'{obj.__module__}.{name}'

    def _dispatch_wrap(self, obj, name):
        was_wrapped = False
        if name not in self._already_wrapped:
            obj = self._wrap(obj)
            self._already_wrapped.add(name)
            was_wrapped = True
        return obj, was_wrapped

    def patch_obj(self, obj):
        if not hasattr(obj, '__module__') or not obj.__module__.startswith('src'):
            return obj

        obj_name = self._get_full_obj_name(obj)
        was_wrapped = False
        log_msg = ''

        if isinstance(obj, FunctionType):
            obj, was_wrapped = self._dispatch_wrap(obj, obj_name)
            log_msg = f'patching function `{obj_name}`.'

        for attr_name in dir(obj):
            attr_obj = getattr(obj, attr_name)
            if callable(attr_obj) and not _is_dunder(attr_name):
                attr_full_name = self._get_full_obj_name(attr_obj)
                attr_obj = self._dispatch_wrap(attr_obj, attr_full_name)

                if attr_full_name not in self._already_wrapped:
                    attr_obj, was_wrapped = self._wrap(attr_obj)
                    setattr(obj, attr_name, attr_obj)
                    log_msg = f'patching method `{attr_name}` of `{obj_name}`.'

        if was_wrapped:
            self._logger.debug(log_msg)

        return obj

    def patch_mod(self, mod):
        for attr_name, attr_val in vars(mod).items():
            if not _is_dunder(attr_name):
                setattr(mod, attr_name, self.patch_obj(attr_val))

        return mod


def trace(mn, fn, target, **kwargs):
    tree = ProjectTree(mn)
    patcher = Patcher(targets=[target])
    for mod in tree:
        patcher.patch_mod(mod)
    rv = getattr(tree.entry_mod, fn)(**kwargs)
    return rv
