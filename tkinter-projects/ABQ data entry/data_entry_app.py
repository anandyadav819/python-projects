import tkinter as tk
from tkinter import ttk
from datetime import datetime
import os
import csv
from decimal import Decimal, InvalidOperation

# Base Label-Entry Class
class LabelInput(tk.Frame):

    def __init__(self, parent, label='',
    input_class=ttk.Entry,
    input_var=None,
    input_args=None,
    label_args=None,
    **kwargs):
        super().__init__(parent, **kwargs)
        input_args = input_args or {}
        label_args = label_args or {}
        self.variable = input_var

        if input_class in (ttk.Checkbutton, ttk.Button, ttk.Radiobutton):
            input_args["text"] = label
            input_args["variable"] = input_var
        else:
            self.label = ttk.Label(self, text=label, **label_args)
            self.label.grid(row=0, column=0, sticky=(tk.W + tk.E))
            input_args["textvariable"] = input_var

        self.input = input_class(self, **input_args)
        self.input.grid(row=1, column=0, sticky=(tk.W + tk.E))

        self.columnconfigure(0, weight=1)

        self.error = getattr(self.input, 'error', tk.StringVar())
        self.error_label = ttk.Label(self, textvariable=self.error)
        self.error_label.grid(row=2, column=0, sticky=(tk.W + tk.E))

    def grid(self, sticky=(tk.E + tk.W), **kwargs):
        super().grid(sticky=sticky, **kwargs)

    def get(self):
        try:
            if self.variable:
                return self.variable.get()
            elif type(self.input) == tk.Text:
                return self.input.get('1.0', tk.END)
            else:
                return self.input.get()
        except(TypeError, tk.TclError):
            return ''
    
    def set(self, value, *args, **kwargs):
        if type(self.variable) == tk.BooleanVar:
            self.variable.set(bool(value))
        elif self.variable:
            self.variable.set(value, *args, **kwargs)
        elif type(self.input) in (ttk.Checkbutton, ttk.Radiobutton):
            if value:
                self.input.select()
            else:
                self.input.deselect()
        elif type(self.input) == tk.Text:
            self.input.delete('1.0', tk.END)
            self.input.insert('1.0', value)
        else:
            self.input.delete(0, tk.END)
            self.input.insert(0, value)    

# Validation Class
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

class RequiredEntry(ValidatedMixin, ttk.Entry):
    def _focusout_validate(self, event):
        valid=True
        if not self.get():
            valid = False
            self.error.set('A value is required')
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

class ValidatedCombobox(ValidatedMixin, ttk.Combobox):

    def _key_validate(self, proposed, action, **kwargs):
        valid = True
        if action == '0':
            self.set('')
            return True
        values = self.cget('values')
        matching = [
            x for x in values
            if x.lower().startswith(proposed.lower())
        ]
        if len(matching) == 0:
            valid = False
        elif len(matching) == 1:
            self.set(matching[0])
            self.icursor(tk.END)
            valid = True
        return valid
    
    def _focusout_validate(self, **kwargs):
        valid = True
        if not self.get():
            valid = False
            self.error.set('A value is required')
        return valid
    
class ValidatedSpinbox(ValidatedMixin, tk.Spinbox):
    
    def __init__(self, *args, min_var=None, max_var=None,
    focus_update_var=None, from_='-Infinity',
    to='Infinity', **kwargs):
        super().__init__(*args, from_=from_, to=to, **kwargs)
        self.resolution = Decimal(str(kwargs.get('increment', '1.0')))

        self.precision = (
            self.resolution.normalize().as_tuple().exponent
        )

        self.variable = kwargs.get('textvariable') or tk.DoubleVar()

        if min_var:
            self.min_var = min_var
            self.min_var.trace('w', self._set_mimimum)
        if max_var:
            self.max_var = max_var
            self.max_var.trace('w', self._set_maximum)
        self.focus_update_var = focus_update_var
        self.bind('<FocusOut>', self._set_focus_update_var)
    
    def _set_focus_update_var(self, event):
        value = self.get()
        if self.focus_update_var and not self.error.get():
            self.focus_update_var.set(value)

    def _set_mimimum(self, *args):
        current = self.get()
        try:
            new_min = self.min_var.get()
            self.config(from_=new_min)
        except (tk.TclError, ValueError):
            pass
        if not current:
            self.delete(0, tk.END)
        else:
            self.variable.set(current)
        self.trigger_focusout_validation()
    
    def _set_maximum(self, *args):
        current = self.get()
        try:
            new_max = self.max_var.get()
            self.config(to = new_max)
        except (tk.TclError, ValueError):
            pass
        if not current:
            self.delete(0, tk.END)
        else:
            self.variable.set(current)
        self.trigger_focusout_validation()

    def _key_validate(self, char, index, current, proposed,
    action, event, *kwargs):
        valid = True
        min_val = self.cget('from')
        max_val = self.cget('to')
        no_negative = min_val >= 0
        no_decimal = self.precision >= 0

        if action == '0':
            return True
        
        if any([
            (char not in ('-1234567890.')),
            (char == '-' and (no_negative or index !=0)),
            (char == '.' and (no_decimal or '.' in current))
        ]):

            return False
        
        if proposed in  '-.':
            return True
        
        proposed = Decimal(proposed)
        proposed_precision = proposed.as_tuple().exponent

        if any([
            (proposed > max_val),
            (proposed_precision < self.precision)
        ]):
            return False
        
        return valid

    def _focusout_validate(self, **kwargs):
        valid = True
        value = self.get()
        min_val = self.cget('from')
        try:
            value = Decimal(value)
        except InvalidOperation:
            self.error.set('Invalid number string: {}'.format(value))
            return False
        
        if value < min_val:
            self.error.set('Value is too low (min {})'.format(min_val))
            valid = False
        max_val = self.cget('to')
        if value > max_val:
            self.error.set('Value is too high (max {})'.format(max_val))

        return valid

# Core Form  
class DataRecorderForm(tk.Frame):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.inputs = {}

        """ Record Information """
        recordInfo = tk.LabelFrame(self, text="Record Information")

        self.inputs['Date'] = LabelInput(recordInfo, "Date",
        input_class=DateEntry, input_var=tk.StringVar())

        self.inputs['Date'].grid(row=0, column=0)

        self.inputs['Time'] = LabelInput(recordInfo, "Time",
        input_class=ValidatedCombobox, input_var=tk.StringVar(),
        input_args={"values":["8:00", "12:00", "16:00", "20:00"]})

        self.inputs['Time'].grid(row=0, column=1)

        self.inputs['Technician'] = LabelInput(recordInfo, "Technician",
        input_class=RequiredEntry, input_var=tk.StringVar())

        self.inputs['Technician'].grid(row=0, column=2)

        self.inputs['Lab'] = LabelInput(recordInfo, "Lab", 
        input_class=ttk.Combobox, input_var=tk.StringVar(),
        input_args={"values":["A", "B", "C", "D", "E"]})

        self.inputs['Lab'].grid(row=1, column=0)
        
        self.inputs['Plot'] = LabelInput(recordInfo, "Plot",
        input_class=ValidatedCombobox, input_var=tk.StringVar(),
        input_args={"values": list(str(x) for x in range(1, 21))})

        self.inputs['Plot'].grid(row=1, column=1)

        self.inputs['Seed sample'] = LabelInput(
            recordInfo, "Seed sample", RequiredEntry, input_var=tk.StringVar()
        )

        self.inputs['Seed sample'].grid(row=1, column=2)
        recordInfo.grid(row=0, column=0, sticky=tk.W + tk.E)
        
        """ Record Information End"""

        """ Environment Information"""
        
        environmentInfo = tk.LabelFrame(self, text="Environment Data")

        self.inputs['Humidity'] = LabelInput(
            environmentInfo, "Humidity (g/m**3)",
            input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
            input_args={"from_":'0.5', "to":'52.0', "increment":'.01'})

        self.inputs['Humidity'].grid(row=0, column=0)

        self.inputs['Light'] = LabelInput(environmentInfo,
        "Light", input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
        input_args={"from_":'0', "to":'100.0', "increment":'0.01'})

        self.inputs['Light'].grid(row=0, column=1)
        
        self.inputs['Temperature'] = LabelInput(environmentInfo,
        "Temperature", input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
        input_args={"from_":'4', "to":'40', "increment":'0.01'}
        )

        self.inputs['Temperature'].grid(row=0, column=2)

        self.inputs['Equipment Fault'] = LabelInput(environmentInfo,
        "Equipment Fault", input_class=ttk.Checkbutton, 
        input_var=tk.BooleanVar())

        self.inputs['Equipment Fault'].grid(row=1, column=0, columnspan=3)
        environmentInfo.grid(row=1, column=0, sticky=tk.W + tk.E)
        
        """ Environment Information End"""

        plantInfo = tk.LabelFrame(self, text="Plant Data")

        self.inputs['Plants'] = LabelInput(plantInfo,
        "Plants", input_class=ValidatedSpinbox, input_var=tk.IntVar(),
        input_args={"from_":'0', "to":'20'})

        self.inputs['Plants'].grid(row=0, column=0)

        self.inputs['Blossoms'] = LabelInput(
            plantInfo, "Blossoms", input_class=ValidatedSpinbox,
            input_var=tk.IntVar(),
            input_args={"from_":'0', "to":'1000'}
        )

        self.inputs['Blossoms'].grid(row=0, column=1)

        self.inputs['Fruit'] = LabelInput(plantInfo,
        "Fruit", input_class=ValidatedSpinbox, input_var=tk.IntVar(),
        input_args={"from_":'0', "to":'1000'})

        self.inputs['Fruit'].grid(row=0, column=2)

        min_height_var = tk.DoubleVar(value='infinity')
        max_height_var = tk.DoubleVar(value='infinity')

        self.inputs['Min Height'] = LabelInput(plantInfo,
        "Min Height (cm)", input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
        input_args={"from_":'0', "to":'1000', "increment":'0.01',
        "max_var":max_height_var, "focus_update_var":min_height_var})

        self.inputs['Min Height'].grid(row=1, column=0)
        
        self.inputs['Max Height'] = LabelInput(plantInfo,
        "Max Height (cm)", input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
        input_args={"from_":0, "to":1000, "increment":0.01, 
        "min_var":min_height_var, "focus_update_var":max_height_var})

        self.inputs['Max Height'].grid(row=1, column=1)

        

        self.inputs['Median Height'] = LabelInput(plantInfo,
        "Median Height (cm)", input_class=ValidatedSpinbox, input_var=tk.DoubleVar(),
        input_args={"from_":0, "to":1000, "increment":0.01,
        "min_var": min_height_var, "max_var":max_height_var})

        self.inputs['Median Height'].grid(row=1, column=2)

        plantInfo.grid(row=2, column=0, sticky=tk.W + tk.E)
        self.inputs['Notes'] = LabelInput(
            self, "Notes",
            input_class=tk.Text,
            input_args={"width":75, "height":10}
        )

        self.inputs['Notes'].grid(sticky="w", row=3, column=0)
        self.reset()

    def get(self):
        data={}
        for key, widget in self.inputs.items():
            data[key] = widget.get()
        return data

    def reset(self):
        lab = self.inputs['Lab'].get()
        time = self.inputs['Time'].get()
        technician = self.inputs['Technician'].get()
        plot = self.inputs['Plot'].get()
        plot_values = self.inputs['Plot'].input.cget('values') 
        for widget in self.inputs.values():
            #print(key)
            widget.set(value="")
        current_date = datetime.today().strftime('%Y-%m-%d')
        self.inputs['Date'].set(current_date)

        self.inputs['Time'].input.focus()
        if plot not in ('', plot_values[-1]):
            self.inputs['Lab'].set(lab)
            self.inputs['Time'].set(time)
            self.inputs['Technician'].set(technician)
            next_plot_index = plot_values.index(plot) + 1
            self.inputs['Plot'].set(plot_values[next_plot_index])
            self.inputs['Seed sample'].input.focus()


    def get_errors(self):
        errors = {}
        for key, widget in self.inputs.items():
            if hasattr(widget.input, 'trigger_focusout_validation'):
                widget.input.trigger_focusout_validation()
            if widget.error.get():
                errors[key] = widget.error.get()
        return errors


# Main Application
class Application(tk.Tk):
    """Application root window"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("ABQ Data Entry Application")
        self.resizable(width=False, height=False)

        ttk.Label(
            self,
            text="ABQ Data Entry Application",
            font=("TkDefaultFont", 16)
        ).grid(row=0)

        self.recordform = DataRecorderForm(self)
        self.recordform.grid(row=1, padx=1)

        self.savebutton = ttk.Button(self, text="save",command=self.on_save)
        self.savebutton.grid(sticky=tk.E, row=2, padx=10)
        
        self.status = tk.StringVar()
        self.statusbar = ttk.Label(self, textvariable=self.status)
        self.statusbar.grid(sticky=(tk.W + tk.E), row=3, padx=10)

        self.records_saved = 0
        

    def on_save(self):
        errors = self.recordform.get_errors()
        if errors:
            self.status.set(
                "Cannot save, error in fields: {}".format(', '.join(errors.keys()))
            )
            return False
        datestring = datetime.today().strftime("%Y-%m-%d")
        filename = "abq_data_record_{}.csv".format(datestring)
        newfile = not os.path.exists(filename)

        data = self.recordform.get()

        with open(filename, "a") as fh:
            csvwriter = csv.DictWriter(fh, fieldnames=data.keys())
            if newfile:
                csvwriter.writeheader()
            csvwriter.writerow(data)
        
        self.records_saved += 1
        self.status.set(
            "{} records saved this session".format(self.records_saved)
        )

        self.recordform.reset()
    




if __name__== "__main__":
    app = Application()
    app.mainloop()



