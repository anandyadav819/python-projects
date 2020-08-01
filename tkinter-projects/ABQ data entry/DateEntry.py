import tkinter as tk
from tkinter import ttk
from datetime import datetime


class ValidatedMixin:
    def __init__(self, *args, error_var=None, **kwargs):
        self.error = error_var or tk.StringVar()
        super().__init__(*args, **kwargs)

        vcmd = self.register(self._validate)
        invcmd = self.register(self._invalid)

        self.config(
            validate='all',
            validatecommand=(vcmd, '%P', '%s', '%S', '%V', '%i', '%d'),
            invalidcommand=(invcmd, '%P', '%s', '%S', '%V', '%i', '%d')
        )

    def _toggle_error(self, on=False):
        self.config(foreground=('red' if on else 'black'))
    
    def _validate(self, proposed, current, char, event, index, action):
        self._toggle_error(False)
        self.error.set('')
        valid = True
        if event == 'focusout':
            valid = self._focusout_validate(event=event)
        elif event == 'key':
            valid = self._key_validate(proposed=proposed,
            current=current, char=char, event=event,
            index=index, action=action)
        return valid
    
    def _focusout_validate(self, **kwargs):
        return True
    def _key_validate(self, **kwargs):
        return True
    
    def _invalid(self, proposed, current, char, event, index, action):
        if event == 'focusout':
            self._focusout_invalid(event=event)
        elif event == 'key':
            self._key_validate(proposed=proposed,
            current=current, char=char, event=event,
            index=index, action=action)
    
    def _focusout_invalid(self, **kwargs):
        return True
    def _key_invalid(self, **kwargs):
        return True

    def trigger_focusout_validation(self):
        valid = self._validate('', '', '', 'focusout', '', '')
        if not valid:
            self._focusout_invalid(event='focusout')
        return valid
    
class DateEntry(ValidatedMixin, ttk.Entry):

    def _key_validate(self, action, index, char, **kwargs):
        valid = True
        
        if action == '0':
            valid = True
        elif index in ('0', '1', '2', '3',
        '5', '6', '8', '9'):
            valid = char.isdigit()
        elif index in ('4', '7'):
            valid = char == '-'
        else:
            valid = False
        return valid
    
    def _focusout_validate(self, event):
        valid = True
        if not self.get():
            self.error.set('A value is required')
            valid = False
        try:
            datetime.strptime(self.get(), '%Y-%m-%d')
        except ValueError:
            self.error.set('Invalid date')
            valid = False
        return valid
    
            
    '''
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.config(
            validate='all',
            validatecommand=(
                self.register(self._validate),
                '%S', '%i', '%V', '%d'
            ),
            invalidcommand = (self.register(self._on_invalid), '%V')
        )
        self.error = tk.StringVar()

    def _toggle_error(self, error=''):
        self.error.set(error)
        if error:
            self.config(foreground='red')
        else:
            self.config(foreground='black')

    def _validate(self, char, index, event, action):
        self._toggle_error()
        valid = True

        if event == 'key':
            if action == '0':
                valid = True
            elif index in ('0', '1', '2', '3',
            '5', '6', '8', '9'):
                valid = char.isdigit()
            elif index in ('4', '7'):
                valid = char == '-'
            else:
                valid = False
        elif event == 'focusout':
            try:
                datetime.strptime(self.get(), '%Y-%m-%d')
            except ValueError:
                valid = False
        return valid
    
    def _on_invalid(self, event):
        if event != 'key':
            self._toggle_error('Not a valid date')
    '''


if __name__=="__main__":
    root = tk.Tk()
    entry = DateEntry(root)
    entry.pack()
    tk.Label(textvariable=entry.error).pack()

    tk.Entry(root).pack()
    root.mainloop()


