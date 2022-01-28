import sys; sys.path.insert(0, '.')  # noqa

import streamlit as st

from app.factory import create_app

if __name__ == '__main__':
    app = create_app(st)
    app.run()

