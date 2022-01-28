from app.handlers import ProfileHandler
from app.app import App

_APP = None


def create_app(frontend):
    global _APP
    if _APP is None:
        handlers = [
            ProfileHandler(name='Profile', frontend=frontend)
        ]
        app = App(handlers=handlers, frontend=frontend)
        _APP = app
    return _APP
