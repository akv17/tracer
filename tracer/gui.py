import tkinter
from tkinter import ttk

from .core import trace


class CallTreeWidget(ttk.Treeview):

    def __init__(self, *args, unfolded=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.unfolded = unfolded

    def build(self, data):
        from collections import deque
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
                label = ttk.Label(
                    self,
                    text=col,
                )
                label.grid(row=i, column=j, sticky="nsew", padx=1, pady=1)


class CallSourceWidget(tkinter.Frame):

    def __init__(self, parent, call, **kwargs):
        super().__init__(parent, **kwargs)
        import inspect
        src = inspect.getsource(call.frame)
        text = tkinter.Text(self)
        text.insert(tkinter.INSERT, src)
        text.pack()


class Tracer:

    def __init__(self, width=1000, height=1000):
        self.width = width
        self.height = height

        self._root = tkinter.Tk()
        self._root.geometry(f'{self.width}x{self.height}')
        self.wtree = CallTreeWidget(self._root)
        self.wtree.bind('<Double-1>', self.on_double_click)

        self._run = None
        self._state = {
            'wvars': None,
            'wsrc': None,
        }

    def _get_selected_call(self):
        item = self.wtree.selection()[0]
        uname = self.wtree.item(item, 'text')
        call = self._run.get_call_by_uname(uname)
        return call

    def _reset_state(self):
        for w in self._state.values():
            if w is not None:
                w.pack_forget()

    def on_double_click(self, event):
        self._reset_state()
        call = self._get_selected_call()
        wvars = CallVarsWidget(parent=self._root, call=call)
        wsrc = CallSourceWidget(parent=self._root, call=call)
        self._state['wvars'] = wvars
        self._state['wsrc'] = wsrc
        wvars.pack(side='right')
        wsrc.pack(side='left')

    def trace(self, func, args, kwargs=None):
        self._run = trace(func=func, args=args, kwargs=kwargs)
        tree_data = self._run.create_tree()
        self.wtree.build(tree_data)
        self.wtree.pack(fill='both')
        self._root.mainloop()
