import sys; sys.path.insert(0, '.')  # noqa

import streamlit as st

from tracer.trace import Trace


class Model:

    def __init__(self):
        self.script = None
        self._traces = None

    def run(self):
        if self._traces is None:
            with Trace() as trace:
                with open(self.script, 'r') as f:
                    code = f.read()
                    exec(code, {'__name__': '__main__'})
            self._traces = trace.traces
        return self._traces


class View:

    def __init__(self):
        self.traces = None

    def run(self):
        st.write(self.traces)


class App:

    def __init__(self):
        self.model = Model()
        self.view = View()

    def run(self, script):
        self.model.script = script
        traces = self.model.run()
        self.view.traces = traces
        self.view.run()


app = App()
