import argparse
import importlib
import inspect
import json
import logging
import os
from abc import abstractmethod
from collections import deque
from datetime import datetime
from functools import wraps
from types import FunctionType


class Match:

    def __init__(
        self,
        target=None,
        func=None,
        where=None,
        identifier=None,
        value=None,
        matcher_type=None,
    ):
        self.target = target
        self.func = func
        self.where = where
        self.identifier = identifier
        self.value = value
        self.type = type(self.value)
        self.timestamp = datetime.now()
        self.matcher_type = matcher_type
        self.stack = None

    def __repr__(self):
        vars_ = ', '.join(f'{k}={v}' for k, v in vars(self).items())
        return f'{self.__class__.__name__}({vars_})'


class LoggingMixin:
    LEVEL = logging.INFO
    FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setFormatter(FORMATTER)

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


class ModuleTree(LoggingMixin):

    def __init__(self, top_package, entry_mod_name):
        self.top_package = top_package
        self.entry_mod_name = entry_mod_name
        self.entry_mod = None
        self._imported = set()

    def _parse_mod_imports(self, src, mod_name):
        names = []
        for ln in src.split('\n'):
            ln = ln.strip()
            if ln.startswith('import') or ln.startswith('from'):
                name = ln.split()[1]
                if name.startswith('.'):
                    self._logger.warning(f'got relative import `{ln}` in module `{mod_name}`, ignoring.')
                    continue

                if name.startswith(self.top_package):
                    names.append(name)

        return names

    def _get_mod_path(self, mod_name):
        mod_path = mod_name.replace('.', os.path.sep) + '.py'

        if not os.path.exists(mod_path):
            self._logger.debug(f'guessing __init__ of module `{mod_name}`.')
            mod_path, _ = os.path.split(mod_path)
            mod_path = os.path.join(mod_path, '__init__.py')

        if not os.path.exists(mod_path):
            msg = f'no module `{mod_name}` at inferred path `{mod_path}`.'
            raise Exception(msg)

        return mod_path

    def _get_imports(self, mod_name):
        mod_path = self._get_mod_path(mod_name)
        with open(mod_path, 'r') as f:
            src = f.read()
            imps = self._parse_mod_imports(src, mod_name=mod_name)
        return imps

    def _import_mod(self, mod_name):
        mod = importlib.import_module(mod_name)
        self._imported.add(mod_name)
        self._logger.debug(f'imported module `{mod_name}`.')
        return mod

    def __iter__(self):
        imports = deque([self.entry_mod_name])
        while imports:
            mod_name = imports.popleft()
            mod = self._import_mod(mod_name)
            yield mod

            mod_imports = self._get_imports(mod_name)
            imports.extend(mod_imports)

            if self.entry_mod is None:
                self.entry_mod = mod


class BaseMatcher(LoggingMixin):

    def __init__(self, targets):
        self.targets = targets
        self.matches = []

    @abstractmethod
    def _match_val(self, value, target):
        raise NotImplementedError

    def _match_val_iter(self, obj_name, val_iter, where):
        matches = []
        for val_ident, val in val_iter:
            for t in self.targets:
                if self._match_val(value=val, target=t):
                    match = Match(
                        func=obj_name,
                        where=where,
                        identifier=val_ident,
                        target=t,
                        value=val,
                        matcher_type=type(self)
                    )
                    matches.append(match)

        for m in matches:
            self._logger.debug(f'matched `{m}`.')

        self.matches.extend(matches)
        return matches

    def _match_args(self, obj_name, *args):
        return self._match_val_iter(obj_name, val_iter=enumerate(args), where='args')

    def _match_kwargs(self, obj_name, **kwargs):
        return self._match_val_iter(obj_name, val_iter=kwargs.items(), where='kwargs')

    def _match_retval(self, obj_name, rv):
        return self._match_val_iter(obj_name, val_iter=zip([None], [rv]), where='return')

    def match(self, obj_name, rv, *args, **kwargs):
        matches = []
        arg_matches = self._match_args(obj_name, *args)
        matches.extend(arg_matches)
        kwargs_matches = self._match_kwargs(obj_name, **kwargs)
        matches.extend(kwargs_matches)
        rv_matches = self._match_retval(obj_name, rv)
        matches.extend(rv_matches)
        return matches


class EqualsMatcher(BaseMatcher):

    def _match_val(self, value, target):
        return value == target


class ContainsMatcher(BaseMatcher):

    def _match_val(self, value, target):
        return target in value if hasattr(value, '__contains__') else False


class AttrEqualsMatcher(BaseMatcher):

    def __init__(self, attr_name, targets):
        super().__init__(targets=targets)
        self.attr_name = attr_name

    def _match_val(self, value, target):
        return getattr(value, self.attr_name) == target if hasattr(value, self.attr_name) else False


class Patcher(LoggingMixin):

    def __init__(self, top_package, matchers, track_stack=False):
        self.top_package = top_package
        self.matchers = matchers
        self.track_stack = track_stack
        self._wrapped = set()

    @property
    def matches(self):
        return [m for matcher in self.matchers for m in matcher.matches]

    @property
    def num_patched(self):
        return len(self._wrapped)

    @staticmethod
    def _is_dunder(name):
        return name.startswith('__') and name.endswith('__')

    @staticmethod
    def _get_full_obj_name(obj):
        mod_name = obj.__module__ if hasattr(obj, '__module__') else ''

        if hasattr(obj, '__qualname__'):
            name = obj.__qualname__
        elif hasattr(obj, '__name__'):
            name = obj.__name__
        else:
            name = repr(obj)

        return f'{mod_name}.{name}'

    @staticmethod
    def _set_stack(matches):
        stack = inspect.stack()
        frames = [
            {'filename': f.filename, 'lineno': f.lineno, 'function': f.frame.f_locals.get('obj_name', f.function)}
            for f in stack[1:]
        ]
        for m in matches:
            m.stack = frames

    def _match_targets(self, obj_name, rv, *args, **kwargs):
        return [
            m
            for matcher in self.matchers
            for m in matcher.match(obj_name, rv, *args, **kwargs)
        ]

    def _wrap(self, obj):
        obj_name = self._get_full_obj_name(obj)
        sig = inspect.signature(obj.__call__) if inspect.isclass(obj) else inspect.signature(obj)

        @wraps(obj)
        def wrapper(*args, **kwargs):
            self._logger.debug(f'tracing `{obj_name}`.')
            args_ = sig.bind(*args, **kwargs)
            args_.apply_defaults()
            kwargs_ = args_.arguments
            rv = obj(*args, **kwargs)
            kwargs_.pop('self', None)  # avoid binding self twice.
            matches = self._match_targets(obj_name, rv, **kwargs_)
            if self.track_stack:
                self._set_stack(matches=matches)
            return rv

        return wrapper

    def _dispatch_wrap(self, obj, name, log_msg=None):
        was_wrapped = False
        if name not in self._wrapped:
            obj = self._wrap(obj)
            self._wrapped.add(name)
            was_wrapped = True

        if was_wrapped:
            self._logger.debug(log_msg or f'patching object `{name}`.')

        return obj, was_wrapped

    def patch_obj(self, obj):
        obj_name = self._get_full_obj_name(obj)
        if not obj_name.startswith(self.top_package):
            return obj

        # wrap a function straight away.
        if isinstance(obj, FunctionType):
            log_msg = f'patching function `{obj_name}`.'
            obj, was_wrapped = self._dispatch_wrap(obj, obj_name, log_msg=log_msg)

        # wrap any callable attr of a class including __call__ (the only dunder patched).
        # never patch exception classes.
        elif inspect.isclass(obj) and not issubclass(obj, Exception):
            for attr_name in dir(obj):
                attr_obj = getattr(obj, attr_name)
                if callable(attr_obj) and (attr_name == '__call__' or not self._is_dunder(attr_name)):
                    attr_full_name = self._get_full_obj_name(attr_obj)
                    log_msg = f'patching method `{attr_name}` of `{obj_name}`.'
                    attr_obj, was_wrapped = self._dispatch_wrap(attr_obj, attr_full_name, log_msg=log_msg)
                    if was_wrapped:
                        setattr(obj, attr_name, attr_obj)

        return obj

    def patch_mod(self, mod):
        for attr_name, attr_val in vars(mod).items():
            if not self._is_dunder(attr_name):
                setattr(mod, attr_name, self.patch_obj(attr_val))

        return mod


class Tracer(LoggingMixin):
    _REPORT_FP = 'traces.json'

    def __init__(self, tree, patcher):
        self.tree = tree
        self.patcher = patcher

    @property
    def matches(self):
        return self.patcher.matches

    def setup(self):
        for mod in self.tree:
            self.patcher.patch_mod(mod)
        msg = f'setup tracer of package `{self.tree.top_package}` with {self.patcher.num_patched} patched objects.'
        self._logger.debug(msg)

    def exec(self, fcall):
        self.setup()
        co = f'from {self.tree.entry_mod_name} import *; {fcall}'
        exec(co)

    def report(self, fp=None):
        def _serialize(val):
            if isinstance(val, datetime):
                val = str(val)
            try:
                json.dumps(val)
            except TypeError:
                val = repr(val)
            return val

        rv = {}
        trg_map = {}
        for m in self.matches:
            key = _serialize(m.target)
            trg_map.setdefault(key, []).append(m)

        for trg, trg_matches in trg_map.items():
            rv[trg] = [
                {k: _serialize(v) for k, v in vars(m).items()}
                for m in trg_matches
            ]

        fp = fp or self._REPORT_FP
        with open(fp, 'w') as f:
            json.dump(rv, f)


def trace(
    func,
    args,
    kwargs,
    targets,
    matchers=None,
    debug=False,
    track_stack=False,
    do_report=True,
    report_fp=None
):
    if debug:
        LoggingMixin.LEVEL = logging.DEBUG

    mn = func.__module__
    top_package = mn.split('.')[0]
    tree = ModuleTree(top_package=top_package, entry_mod_name=mn)
    matchers = matchers or []
    matchers = [
        *matchers,
        EqualsMatcher(targets),
        ContainsMatcher(targets),
        AttrEqualsMatcher(attr_name='value', targets=targets),
    ]
    patcher = Patcher(top_package=top_package, matchers=matchers, track_stack=track_stack)
    tracer = Tracer(tree=tree, patcher=patcher)
    tracer.setup()

    func = getattr(tree.entry_mod, func.__name__)
    func(*args, **kwargs)

    if do_report:
        tracer.report(fp=report_fp)

    return tracer
