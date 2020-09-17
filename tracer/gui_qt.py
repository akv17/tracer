import sys
import inspect
from collections import deque

from PySide2 import QtCore, QtWidgets, QtGui

from .core import trace


class TreeWidget(QtWidgets.QTreeWidget):

    def __init__(self, parent=None, header='', expanded=False):
        super().__init__(parent=parent)
        self.expanded = expanded

        self.setColumnCount(1)
        self.setHeaderLabels([header])

    def build(self, data):
        q = deque([(self, data)])
        while q:
            par_item, par_leaves = q.popleft()
            for ch_name, ch_leaves in par_leaves.items():
                ch_item = QtWidgets.QTreeWidgetItem(par_item)
                ch_item.setText(0, ch_name)
                ch_item.setExpanded(self.expanded)
                q.append((ch_item, ch_leaves))


class CallInfoWidget(QtWidgets.QTableWidget):

    def __init__(self, call, parent=None):
        super().__init__(parent=parent)
        self.call = call
        self._table_content = self._get_table_content(call)

        self.setRowCount(len(self._table_content))
        self.setColumnCount(2)
        self._set_table_content(self._table_content)
        self.setHorizontalHeaderLabels(['Info', ''])
        self.setVerticalHeaderLabels([''] * self.rowCount())
        self.resizeColumnsToContents()

    def _get_table_content(self, call):
        return [
            ['name', call.uname],
            ['caller', call.caller.uname],
            ['runtime', str(call.runtime)],
            ['call_time', str(call.calltime)],
            ['return_time', str(call.rettime)],
        ]

    def _set_table_content(self, content):
        for i, row in enumerate(content):
            for j, cell in enumerate(row):
                item = QtWidgets.QTableWidgetItem(cell)
                self.setItem(i, j, item)


class CallSourceLineFormatHandler:

    def __init__(self, color=(29, 128, 110)):
        self.color = color

    def apply(self, cursor, line_num):
        for i in range(line_num + 1):
            if i == line_num:
                break
            cursor.movePosition(QtGui.QTextCursor.NextBlock)
            cursor.movePosition(QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)

        doc = cursor.document()
        block = doc.findBlockByNumber(line_num)
        fmt = block.blockFormat()
        brush = QtGui.QBrush(QtGui.QColor(*self.color))
        fmt.setBackground(brush)
        cursor.setBlockFormat(fmt)


class CallVarsWidget(QtWidgets.QTabWidget):

    def __init__(self, call, line_num, parent=None):
        super().__init__(parent=parent)
        self.call = call
        self.line_num = line_num

        for vars_name in ('locals', 'args', 'retval'):
            w_vars_tree = TreeWidget(expanded=True)
            tree_data = self._create_tree_data(which_vars=vars_name)
            w_vars_tree.build(tree_data)
            self.addTab(w_vars_tree, vars_name)

    def _create_tree_data(self, which_vars):
        if which_vars == 'retval':
            vars_ = {'value': getattr(self.call, which_vars)}
        elif which_vars == 'locals':
            if self.line_num is not None:
                # TODO: watch out for None line.
                line = self.call.get_line(self.line_num)
                vars_ = getattr(line, which_vars, {})
            else:
                vars_ = getattr(self.call, which_vars)
        else:
            vars_ = getattr(self.call, which_vars)

        tree_data = {}
        for k, v in vars_.items():
            tree_data[str(k)] = {f'value: {str(v)}\ntype: {type(v)}': {}}
        return tree_data


class CallSourceCodeWidget(QtWidgets.QTextEdit):

    def __init__(self, _par_w, call, parent=None):
        super().__init__(parent=parent)
        self._par_w = _par_w
        self.call = call

        # from local zero-started nums to real src file nums.
        self.text = ''
        self._line_num_map = None
        self._setup_text()

        self.setText(self.text)
        self.setReadOnly(True)
        self.mouseDoubleClickEvent = self.on_double_click
        self.layout = QtWidgets.QHBoxLayout(self)
        self._fmt = CallSourceLineFormatHandler()

    def _setup_text(self):
        ln_offset = self.call.frame.f_code.co_firstlineno
        src = inspect.getsource(self.call.frame)
        lns = src.split('\n')
        self.text = '\n'.join(f'{i + ln_offset}\t| {ln}' for i, ln in enumerate(lns))
        self._line_num_map = {i: i + ln_offset for i in range(len(lns))}

    def _reset_vars_widget(self):
        if self._w_vars is not None:
            self._w_vars.setParent(None)

    def _add_vars_widget(self, line_num):
        self._w_vars = CallVarsWidget(parent=self, call=self.call, line_num=line_num)
        self.layout.addWidget(self._w_vars)

    def highlight_block(self, block_num):
        cursor = self.textCursor()
        self._fmt.apply(cursor, block_num)

    @QtCore.Slot()
    def on_double_click(self, event):
        # TODO: terrible hack.
        cursor = self.textCursor()
        block_num = cursor.blockNumber()
        line_num = self._line_num_map[block_num]
        if line_num is not None:
            self._par_w.active_line_num = line_num
            self._par_w.active_block_num = block_num
            self._par_w._cursor = cursor
            self._par_w.on_double_click()


class CallInspectWidget(QtWidgets.QWidget):

    def __init__(self, call, parent=None):
        super().__init__(parent=parent)
        self.call = call

        self.active_line_num = None
        self.active_block_num = None

        self._w_info = CallInfoWidget(parent=self, call=call)
        self._w_code = CallSourceCodeWidget(_par_w=self, parent=self, call=call)
        self._w_vars = None

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self._w_info)
        self.layout.addWidget(self._w_code)

    def _reset_widgets(self):
        if self._w_vars is not None:
            self._w_vars.setParent(None)
        self._w_code.setParent(None)

    def _add_widgets(self):
        self._w_code = CallSourceCodeWidget(_par_w=self, parent=self, call=self.call)
        self.layout.addWidget(self._w_code)
        if self.active_line_num is not None:
            self._w_vars = CallVarsWidget(
                parent=self,
                call=self.call,
                line_num=self.active_line_num
            )
            self.layout.addWidget(self._w_vars)

    def on_double_click(self):
        # TODO: terrible hack.
        self._reset_widgets()
        self._add_widgets()
        if self.active_block_num is not None:
            self._w_code.highlight_block(self.active_block_num)


class MainWindow(QtWidgets.QWidget):

    def __init__(self, size=(800, 800)):
        super().__init__()
        self.size = size
        self.resize(*size)
        self.w_call_tree = TreeWidget(parent=self, expanded=True)
        self.w_call_tree.itemClicked.connect(self.on_tree_click)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.w_call_tree)

        self._run = None
        self._dynamic_widgets = []

    def _add_dynamic_widgets(self):
        for w in self._dynamic_widgets:
            self.layout.addWidget(w)

    def _reset_dynamic_widgets(self):
        for w in self._dynamic_widgets:
            w.setParent(None)
        self._dynamic_widgets = []

    def on_trace(self, run):
        self._run = run
        call_tree_data = run.create_tree_data()
        self.w_call_tree.build(call_tree_data)

    @QtCore.Slot()
    def on_tree_click(self):
        self._reset_dynamic_widgets()
        item = self.w_call_tree.selectedItems()[0].text(0)
        call = self._run.get_call_by_uname(item)
        w_call_inspect = CallInspectWidget(parent=self, call=call)
        self._dynamic_widgets.append(w_call_inspect)
        self._add_dynamic_widgets()


class Tracer:

    def __init__(self, win_size=(1920, 1080), dark_theme=True):
        super().__init__()
        self._app = QtWidgets.QApplication(sys.argv)
        if dark_theme:
            import qdarkstyle
            self._app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside2'))
        self._win = MainWindow(size=win_size)

    def trace(self, func, args, kwargs=None):
        run = trace(func=func, args=args, kwargs=kwargs)
        self._win.on_trace(run)
        self._win.show()
        self._app.exec_()
