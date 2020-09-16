import tkinter
import inspect
from collections import deque
from tkinter import ttk

from .core import trace


class CallTreeWidget(ttk.Treeview):

    def __init__(self, *args, unfolded=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.unfolded = unfolded

    def build(self, data):
        q = deque([('', data)])
        while q:
            par_ix, par_data = q.popleft()
            self.item(par_ix, open=self.unfolded)
            for ch_k, ch_data in par_data.items():
                ch_ix = self.insert(par_ix, 'end', text=ch_k)
                q.append((ch_ix, ch_data))


class CallVarsWidget(tkinter.Frame):

    def __init__(self, parent, call, background='black', **kwargs):
        super().__init__(parent, background=background, **kwargs)

        content = call.as_table()
        for i, row in enumerate(content):
            cols = row
            for j, col in enumerate(cols):
                label = ttk.Label(self, text=col)
                label.grid(row=i, column=j, sticky='nsew', padx=1, pady=1)


class CallSourceWidget(tkinter.Frame):

    def __init__(self, parent, call, **kwargs):
        super().__init__(parent, **kwargs)
        first_lineno = call.frame.f_code.co_firstlineno
        src = inspect.getsource(call.frame)
        src = self._prettify_src(src, ln_offset=first_lineno)
        text = tkinter.Text(self)
        text.insert(tkinter.INSERT, src)
        text.pack()

    def _prettify_src(self, src, ln_offset=0):
        lns = src.split('\n')
        src = '\n'.join(f'{i + ln_offset} {i + 1}  {ln}' for i, ln in enumerate(lns))
        return src


class CallInspectWidget(tkinter.Frame):

    def __init__(self, parent, call, **kwargs):
        super().__init__(parent, **kwargs)
        w_vars = CallVarsWidget(parent=self, call=call)
        w_src = CallSourceWidget(parent=self, call=call)
        w_vars.grid(row=0, column=1)
        w_src.grid(row=0, column=0)


class Tracer:

    def __init__(self, width=1000, height=1000):
        self.width = width
        self.height = height

        self._root = tkinter.Tk()
        self._root.geometry(f'{self.width}x{self.height}')
        self.w_call_tree = CallTreeWidget(self._root)
        self.w_call_tree.bind('<Button-1>', self.on_double_click)

        self._run = None
        self._dynamic_widgets = {'w_call_inspect': None}

    def _get_selected_call(self, event):
        item = self.w_call_tree.identify('item', event.x, event.y)
        uname = self.w_call_tree.item(item, 'text')
        call = self._run.get_call_by_uname(uname)
        return call

    def _reset_dynamic_widgets(self):
        for w in self._dynamic_widgets.values():
            if w is not None:
                w.pack_forget()

    def on_double_click(self, event):
        self._reset_dynamic_widgets()
        call = self._get_selected_call(event)
        if call is not None:
            w_call_inspect = CallInspectWidget(parent=self._root, call=call)
            self._dynamic_widgets['w_call_inspect'] = w_call_inspect
            w_call_inspect.pack()

    def trace(self, func, args, kwargs=None):
        self._run = trace(func=func, args=args, kwargs=kwargs)
        tree_data = self._run.create_tree()
        self.w_call_tree.build(tree_data)
        self.w_call_tree.pack(fill='both')
        self._root.mainloop()
