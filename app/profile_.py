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

    def run(self):
        funcs = self.profile.stats.list_funcs()
        df_recs = [
            {
                'name': f.name,
                'runtime': f.runtime,
                'num_calls': f.num_calls,
                'module': f.module,
            }
            for f in funcs
        ]
        st.write('## Global runtime')
        st.dataframe(df_recs)

        st.write('## Function runtime')
        qualname_map = {f.qualname: f for f in funcs}
        target_funcs = sorted(qualname_map)
        target_funcs = [''] + target_funcs
        target_func = st.selectbox('Select Function', options=target_funcs)
        if target_func:
            st.write('#### Own')
            func = qualname_map[target_func]
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
