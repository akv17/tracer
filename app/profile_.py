import sys; sys.path.insert(0, '.')  # noqa

import streamlit as st

from tracer.profile import Profile


class Model:

    def __init__(self):
        self.script = None
        self._profile = None

    def run(self):
        if self._profile is None:
            with Profile() as profile:
                with open(self.script, 'r') as f:
                    code = f.read()
                    exec(code, {'__name__': '__main__'})
            self._profile = profile
        return self._profile


class View:

    def __init__(self):
        self.profile = None

    def _render_global(self):
        funcs = self.profile.stats.list_funcs()
        data = [
            {
                'name': f.name,
                'runtime': f.runtime,
                'num_calls': f.num_calls,
                'module': f.module,
            }
            for f in funcs
        ]
        st.write('### Global')
        st.dataframe(data)

    def _render_func(self):
        funcs = self.profile.stats.list_funcs()
        qualname_map = {f.qualname: f for f in funcs}
        options = sorted(qualname_map)
        options = [''] + options
        st.write('### Function')
        func = st.selectbox('Select function to display detailed info:', options=options)
        if func:
            st.write('#### Info')
            func = qualname_map[func]
            data = {
                'name': func.name,
                'module': func.module,
                'calls': func.num_calls,
                'runtime': func.runtime
            }
            st.write(data)
            st.write('#### Callees')
            data = [
                {
                    'name': call.dst.name,
                    'module': call.dst.module,
                    'calls': call.num_calls,
                    'runtime': call.runtime
                }
                for call in func.callees
            ]
            st.write(data)
            st.write('#### Callers')
            data = [
                {
                    'name': call.src.name,
                    'module': call.src.module,
                    'calls': call.num_calls,
                    'runtime': call.runtime
                }
                for call in func.callers
            ]
            st.write(data)

    def run(self):
        self._render_global()
        self._render_func()


class App:

    def __init__(self):
        self.model = Model()
        self.view = View()

    def run(self, script):
        self.model.script = script
        profile = self.model.run()
        self.view.profile = profile
        self.view.run()


app = App()
