class App:

    def __init__(self, handlers, frontend):
        self.handlers = handlers
        self.frontend = frontend
        self._dispatch = {h.name: h for h in self.handlers}

    def run(self):
        handler = self.frontend.selectbox('Menu', options=['Profile'])
        handler = self._dispatch[handler]
        handler.run()
