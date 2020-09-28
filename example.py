from tracer.gui_qt import Tracer
from tests.test_proj.main import main

tracer = Tracer()
tracer.trace(main, args=(2,))
