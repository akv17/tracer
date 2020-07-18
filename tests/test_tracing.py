import unittest

from tracer import trace


class TestTracing(unittest.TestCase):

    def setUp(self) -> None:
        self.mn = 'tests.test_proj.main'
        self.fcall = 'main(x=2)'
        self.targets = [2, -2, 4]
        self.expected_imported = sorted([
            'tests.test_proj.main',
            'tests.test_proj.foo',
            'tests.test_proj.bar',
            'tests.test_proj.baz.baz',
        ])
        self.expected_wrapped = sorted([
            'tests.test_proj.foo.foo',
            'tests.test_proj.foo.Foo.foo',
            'tests.test_proj.bar.bar',
            'tests.test_proj.baz.baz.buzz',
            'tests.test_proj.main.main'
        ])
        # in reversed execution order.
        self.expected_matches = [
            {'target': 2, 'obj_name': 'tests.test_proj.foo.Foo.foo'},
            {'target': -2, 'obj_name': 'tests.test_proj.bar.bar'},
            {'target': 4, 'obj_name': 'tests.test_proj.foo.foo'},
            {'target': 2, 'obj_name': 'tests.test_proj.main.main'},
        ]

    def test_tracing(self):
        tracer = trace(mn=self.mn, fcall=self.fcall, targets=self.targets, do_report=False)

        imported = sorted(tracer.tree._imported)
        self.assertEqual(imported, self.expected_imported)

        wrapped = sorted(tracer.patcher._wrapped)
        self.assertEqual(wrapped, self.expected_wrapped)

        matches = tracer.matches
        self.assertEqual(len(matches), 4)
        for match, exp_match in zip(matches, self.expected_matches):
            for field in exp_match:
                self.assertEqual(exp_match[field], getattr(match, field))
