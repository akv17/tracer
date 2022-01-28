import sys; sys.path.insert(0, '.')  # noqa

import streamlit as st

from app.profile_ import app as profile_app


if __name__ == '__main__':
    action, script = sys.argv[-2:]
    if action == 'profile':
        st.set_page_config(page_title='Profile', layout='wide')
        profile_app.run(script)
    else:
        raise ValueError(action)
