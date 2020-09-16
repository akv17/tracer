import unittest
import inspect
from abc import abstractmethod
from pathlib import Path

from tracer.core import _get_frame_qual_name


def foo():
    return inspect.currentframe()


class Foo:

    def regular_method(self):
        return inspect.currentframe()

    @staticmethod
    def static_method():
        return inspect.currentframe()

    @classmethod
    def class_method(cls):
        return inspect.currentframe()

    @staticmethod
    @abstractmethod
    def double_deco_static_method():
        return inspect.currentframe()


class TestQualNames(unittest.TestCase):

    def setUp(self) -> None:
        frame = inspect.currentframe()
        self.root = Path(frame.f_code.co_filename)
        self.obj = Foo()

    def test_func(self):
        frame = foo()
        qn = _get_frame_qual_name(root=self.root, frame=frame)
        self.assertEqual(qn, 'foo')

    def test_regular_method(self):
        frame = self.obj.regular_method()
        qn = _get_frame_qual_name(root=self.root, frame=frame)
        self.assertEqual(qn, 'Foo.regular_method')

    def test_static_method(self):
        frame = self.obj.static_method()
        qn = _get_frame_qual_name(root=self.root, frame=frame)
        self.assertEqual(qn, 'Foo.static_method')

    def test_class_method(self):
        frame = self.obj.class_method()
        qn = _get_frame_qual_name(root=self.root, frame=frame)
        self.assertEqual(qn, 'Foo.class_method')

    def test_double_deco_static_method(self):
        frame = self.obj.double_deco_static_method()
        qn = _get_frame_qual_name(root=self.root, frame=frame)
        self.assertEqual(qn, 'Foo.double_deco_static_method')
