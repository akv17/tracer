import importlib
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
        obj_name=None,
        args_spec=None,
        arg_id=None,
        target=None,
        value=None,
        matcher_type=None
    ):
        self.obj_name = obj_name
        self.args_spec = args_spec
        self.arg_id = arg_id
        self.target = target
        self.value = value
        self.matcher_type = matcher_type
        self.timestamp = datetime.now()
        self.arg_type = type(self.value)

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

    def _get_imports(self, mod_name):
        mod_path = mod_name.replace('.', os.path.sep) + '.py'
        if not os.path.exists(mod_path):
            msg = f'no module `{mod_name}` at inferred path `{mod_path}`.'
            raise Exception(msg)

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
    def _match_arg(self, arg_val, target):
        raise NotImplementedError

    def _match_args_iter(self, obj_name, args_iter, args_spec):
        matches = []
        for arg_id, arg_val in args_iter:
            for t in self.targets:
                if self._match_arg(arg_val=arg_val, target=t):
                    match = Match(
                        obj_name=obj_name,
                        args_spec=args_spec,
                        arg_id=arg_id,
                        target=t,
                        value=arg_val,
                        matcher_type=type(self)
                    )
                    matches.append(match)

        for m in matches:
            self._logger.debug(f'matched `{m}`.')

        self.matches.extend(matches)
        return matches

    def _match_args(self, obj_name, *args):
        return self._match_args_iter(obj_name, args_iter=enumerate(args), args_spec='args')

    def _match_kwargs(self, obj_name, **kwargs):
        return self._match_args_iter(obj_name, args_iter=kwargs.items(), args_spec='kwargs')

    def match(self, obj_name, *args, **kwargs):
        matches = []
        arg_matches = self._match_args(obj_name, *args)
        matches.extend(arg_matches)
        kwargs_matches = self._match_kwargs(obj_name, **kwargs)
        matches.extend(kwargs_matches)
        return matches


class GenericMatcher(BaseMatcher):

    def _match_arg(self, arg_val, target):
        return arg_val == target


class Patcher(LoggingMixin):

    def __init__(self, top_package, matchers):
        self.top_package = top_package
        self.matchers = matchers
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

    def _match_targets(self, obj_name, *args, **kwargs):
        matches = []
        for matcher in self.matchers:
            cur_matches = matcher.match(obj_name, *args, **kwargs)
            matches.extend(cur_matches)
        return matches

    def _wrap(self, obj):
        obj_name = self._get_full_obj_name(obj)

        @wraps(obj)
        def wrapper(*args, **kwargs):
            self._logger.debug(f'tracing `{obj_name}`.')
            rv = obj(*args, **kwargs)
            self._match_targets(obj_name, *args, **kwargs)
            return rv

        return wrapper

    def _dispatch_wrap(self, obj, name):
        was_wrapped = False
        if name not in self._wrapped:
            obj = self._wrap(obj)
            self._wrapped.add(name)
            was_wrapped = True
        return obj, was_wrapped

    def patch_obj(self, obj):
        obj_name = self._get_full_obj_name(obj)
        if not obj_name.startswith(self.top_package):
            return obj

        was_wrapped = False
        log_msg = ''

        # wrap a function straight away.
        if isinstance(obj, FunctionType):
            obj, was_wrapped = self._dispatch_wrap(obj, obj_name)
            log_msg = f'patching function `{obj_name}`.'

        # wrap any callable attr of an instance.
        else:
            for attr_name in dir(obj):
                attr_obj = getattr(obj, attr_name)
                if callable(attr_obj) and not self._is_dunder(attr_name):
                    attr_full_name = self._get_full_obj_name(attr_obj)
                    attr_obj, was_wrapped = self._dispatch_wrap(attr_obj, attr_full_name)
                    log_msg = f'patching method `{attr_name}` of `{obj_name}`.'
                    if was_wrapped:
                        setattr(obj, attr_name, attr_obj)

        if was_wrapped:
            self._logger.debug(log_msg)

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

    def _setup(self):
        for mod in self.tree:
            self.patcher.patch_mod(mod)
        msg = f'setup tracer of package `{self.tree.top_package}` patching {self.patcher.num_patched} objects.'
        self._logger.debug(msg)

    def exec(self, fcall):
        self._setup()
        co = f'from {self.tree.entry_mod_name} import *; {fcall}'
        exec(co)

    def report(self, fp=None):
        rv = {}
        trg_map = {}
        for m in self.matches:
            trg_map.setdefault(str(m.target), []).append(m)

        for trg, trg_matches in trg_map.items():
            rv[trg] = [{k: str(v) for k, v in vars(m).items()} for m in trg_matches]

        fp = fp or self._REPORT_FP
        with open(fp, 'w') as f:
            json.dump(rv, f)


def trace(
    mn,
    fcall,
    targets,
    report_fp=None,
    debug=False,
    do_report=True
):
    if debug:
        LoggingMixin.LEVEL = logging.DEBUG

    top_package = mn.split('.')[0]
    tree = ModuleTree(top_package=top_package, entry_mod_name=mn)
    patcher = Patcher(top_package=top_package, matchers=[GenericMatcher(targets)])
    tracer = Tracer(tree=tree, patcher=patcher)
    tracer.exec(fcall)

    if do_report:
        tracer.report(fp=report_fp)

    return tracer
