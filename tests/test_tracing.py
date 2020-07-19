import unittest

from tracer import trace


class TestTracing(unittest.TestCase):

    def setUp(self) -> None:
        self.mn = 'tests.test_proj.main'
        self.fcall = 'main(x=2)'
        self.targets = [2, -2, 4, -7, -8]
        self.expected_imported = sorted([
            'tests.test_proj.main',
            'tests.test_proj.foo',
            'tests.test_proj.bar',
            'tests.test_proj.baz.baz',
        ])
        self.expected_wrapped = sorted([
            'tests.test_proj.foo.foo',
            'tests.test_proj.foo.Foo.__call__',
            'tests.test_proj.foo.Foo.foo',
            'tests.test_proj.bar.bar',
            'tests.test_proj.baz.baz.buzz',
            'tests.test_proj.main.main'
        ])
        # in reversed function execution order.
        self.expected_matches = [
            {'target': 2, 'func': 'tests.test_proj.foo.Foo.foo', 'where': 'kwargs'},
            {'target': -2, 'func': 'tests.test_proj.foo.Foo.foo', 'where': 'return'},
            {'target': -2, 'func': 'tests.test_proj.bar.bar', 'where': 'kwargs'},
            {'target': 2, 'func': 'tests.test_proj.bar.bar', 'where': 'kwargs'},
            {'target': 4, 'func': 'tests.test_proj.bar.bar', 'where': 'return'},
            {'target': 4, 'func': 'tests.test_proj.foo.foo', 'where': 'kwargs'},
            {'target': -8, 'func': 'tests.test_proj.baz.baz.buzz', 'where': 'return'},
            {'target': -8, 'func': 'tests.test_proj.foo.Foo.__call__', 'where': 'kwargs'},
            {'target': -7, 'func': 'tests.test_proj.foo.Foo.__call__', 'where': 'return'},
            {'target': 2, 'func': 'tests.test_proj.main.main', 'where': 'kwargs'},
            {'target': -7, 'func': 'tests.test_proj.main.main', 'where': 'return'},

        ]

    def test_tracing(self):
        tracer = trace(mn=self.mn, fcall=self.fcall, targets=self.targets, do_report=False, debug=True)

        imported = sorted(tracer.tree._imported)
        self.assertEqual(imported, self.expected_imported)

        wrapped = sorted(tracer.patcher._wrapped)
        self.assertEqual(wrapped, self.expected_wrapped)

        matches = tracer.matches
        self.assertEqual(len(self.expected_matches), len(matches))
        for match, exp_match in zip(matches, self.expected_matches):
            for field in exp_match:
                self.assertEqual(exp_match[field], getattr(match, field))
