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
                    code = compile(code, self.script, 'exec')
                    exec(code, {'__name__': '__main__'})
            self._traces = trace.traces
        return self._traces


class View:

    def __init__(self):
        self._traces = None
        self._func = None
        self._call = 0
        self._line = 0
        self._calls_map = None

    def _on_click_decr_call(self):
        self._call -= 1
        self._call = max(0, self._call)

    def _on_click_incr_call(self):
        self._call += 1

    def _on_click_decr_line(self):
        self._line -= 1
        self._line = max(0, self._line)

    def _on_click_incr_line(self):
        self._line += 1

    def _render_menu(self):
        self._func = st.selectbox('Function', options=list(self._calls_map))

    def _render_controls(self):
        st.write('_' * 10)
        col0, col1, *_ = st.columns(10)
        with col0:
            st.button('Previous Call', on_click=self._on_click_decr_call, key='pc')
        with col1:
            st.button('Next Call', on_click=self._on_click_incr_call, key='nc')
        col0, col1, *_ = st.columns(10)
        with col0:
            st.button('Previous Line', on_click=self._on_click_decr_line, key='pln')
        with col1:
            st.button('Next Line', on_click=self._on_click_incr_line, key='nln')
        st.write('_' * 10)

    def _render_call(self):
        calls = self._calls_map[self._func]
        try:
            call = calls[self._call]
        except IndexError:
            call = calls[-1]
            self._call = len(calls) - 1
        col0, col1 = st.columns(2)
        with col0:
            st.subheader('Stack')
            stack = call.stack
            size = len(stack)
            stack = [f'{size - i}. -> {f}' for i, f in enumerate(stack)]
            stack = '\n'.join(stack)
            st.code(stack)
        with col1:
            st.subheader('Info')
            st.table([
                ['func', call.func],
                ['call#', f'{self._call+1}/{len(calls)}'],
                ['line#', f'{self._line+1}/{len(call.lines)}'],
                ['file', call.file],
            ])

    def _render_line(self):
        calls = self._calls_map[self._func]
        call = calls[self._call]
        lines = call.lines
        try:
            line = lines[self._line]
        except IndexError:
            line = lines[-1]
            self._line = len(lines) - 1
        prev_lines = lines[max(0, self._line - 5):self._line]
        next_lines = lines[self._line+1:self._line + 5 + 1]
        col0, col1 = st.columns(2)
        with col0:
            st.subheader('Context')
            ctx = [f'def {line.func}:']
            for ln in prev_lines:
                text = f'    {ln.lineno}\t{ln.get_src()}'.rstrip()
                ctx.append(text)
            ctx.append(f'->  {line.lineno}\t{line.get_src()}'.rstrip())
            for ln in next_lines:
                text = f'    {ln.lineno}\t{ln.get_src()}'.rstrip()
                ctx.append(text)
            ctx = '\n'.join(ctx)
            st.code(ctx)
        with col1:
            st.subheader('Vars')
            st.write(line.vars)

    def set_traces(self, traces):
        calls_map = {}
        for call in traces:
            calls_map.setdefault(call.func, []).append(call)
        self._calls_map = calls_map
        self._traces = traces

    def run(self):
        self._render_menu()
        self._render_controls()
        self._render_call()
        self._render_line()


class App:

    def __init__(self):
        self.model = Model()
        self.view = View()

    def run(self, script):
        self.model.script = script
        traces = self.model.run()
        self.view.set_traces(traces)
        self.view.run()


app = App()
