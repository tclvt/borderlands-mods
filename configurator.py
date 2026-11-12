"""Desktop controls for the Borderlands 4 difficulty mod builder."""
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from difficulty import ROOT, DEFAULTS, build, validate

FIELDS = {
    'enemy_health': ('Enemy health', '2 = twice the enemy HP.'),
    'enemy_damage': ('Incoming damage', '2 = twice the damage received, including hazards.'),
    'player_damage': ('Player damage', '0.5 = half your damage output.'),
    'player_durability': ('Player durability', '2 = half incoming damage; affects shields too, not max HP.'),
    'experience': ('Experience', '1 = unchanged XP gains.'),
    'cash': ('Cash', '1 = unchanged cash gains.'),
    'eridium': ('Eridium', '1 = unchanged Eridium gains.'),
}
PRESETS = {
    'Custom': DEFAULTS,
    'Neutral': dict.fromkeys(DEFAULTS, 1.0),
    'Co-op challenge': DEFAULTS,
    'Brutal': DEFAULTS | dict(enemy_health=4, enemy_damage=2, player_damage=0.8),
    'Supplied Harder 2': DEFAULTS | dict(enemy_health=1, enemy_damage=1.99, player_damage=0.5),
}

class Configurator:
    def __init__(self, window):
        self.window = window
        window.title('Borderlands 4 — Difficulty Configurator')
        window.minsize(780, 590)
        frame = ttk.Frame(window, padding=24)
        frame.grid(sticky='nsew')
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        ttk.Label(frame, text='Tune your co-op challenge', font=('Segoe UI', 19, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(frame, text='Multipliers: 1 = normal  ·  0.5 = half  ·  2 = double  ·  range 0.01–100').grid(row=1, column=0, columnspan=3, sticky='w', pady=(8, 18))
        self.preset = tk.StringVar(value='Custom')
        chooser = ttk.Combobox(frame, textvariable=self.preset, values=list(PRESETS), state='readonly', width=24)
        chooser.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 15))
        chooser.bind('<<ComboboxSelected>>', self.apply_preset)
        self.values = {}
        for row, (key, (label, hint)) in enumerate(FIELDS.items(), start=3):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=7, padx=(0, 12))
            value = tk.StringVar(value=str(DEFAULTS[key]))
            ttk.Spinbox(frame, textvariable=value, from_=0.01, to=100, increment=0.1, width=10).grid(row=row, column=1, padx=(0, 16))
            ttk.Label(frame, text=hint, wraplength=420).grid(row=row, column=2, sticky='w')
            self.values[key] = value
            value.trace_add('write', self.update_preview)
        self.preview = tk.StringVar()
        ttk.Label(frame, textvariable=self.preview, font=('Segoe UI', 10, 'bold')).grid(row=10, column=0, columnspan=3, sticky='w', pady=(18, 12))
        ttk.Label(frame, text='Use Normal difficulty. Hard / Easy / UVH can override these values.\nClose the game before replacing files. Install the same build on both PCs.\nPlayer durability changes damage received; it does not change maximum health.', wraplength=740).grid(row=11, column=0, columnspan=3, sticky='w', pady=(0, 16))
        actions = ttk.Frame(frame)
        actions.grid(row=12, column=0, columnspan=3, sticky='w')
        ttk.Button(actions, text='Save settings & generate mod', command=self.generate).pack(side='left', padx=(0, 12))
        ttk.Button(actions, text='Open output folder', command=self.open_output).pack(side='left')
        self.status = tk.StringVar(value='Generated files go to the output folder. Your installed mod stays unchanged.')
        ttk.Label(frame, textvariable=self.status, wraplength=740).grid(row=13, column=0, columnspan=3, sticky='w', pady=16)
        settings_file = ROOT/'settings.json'
        if settings_file.exists():
            try:
                settings = validate(json.loads(settings_file.read_text(encoding='utf-8-sig')))
                for key, value in settings.items():
                    self.values[key].set(str(value))
            except (OSError, ValueError) as exc:
                self.status.set(f'Could not load settings; using defaults. {exc}')
        self.update_preview()

    def settings(self):
        result = {}
        for key, var in self.values.items():
            try:
                result[key] = float(var.get().replace(',', '.'))
            except ValueError:
                raise ValueError(f'Enter a number for {FIELDS[key][0]}.') from None
        return validate(result)

    def apply_preset(self, event=None):
        for key, value in PRESETS[self.preset.get()].items():
            self.values[key].set(str(value))

    def update_preview(self, *_):
        if not hasattr(self, 'preview'):
            return
        try:
            settings = self.settings()
            incoming = settings['enemy_damage'] / settings['player_durability']
            self.preview.set(f"Enemy HP ×{settings['enemy_health']:g}   |   Your damage ×{settings['player_damage']:g}   |   Final incoming damage ×{incoming:g}")
        except ValueError:
            self.preview.set('Enter valid multipliers to see the combined effect.')

    def generate(self):
        try:
            settings = self.settings()
            output = build(settings)
            (ROOT/'settings.json').write_text(json.dumps(settings, indent=2)+'\n', encoding='utf-8')
            self.status.set(f'Generated successfully: {output}')
            messagebox.showinfo('Mod generated', 'Your three mod files are in output.\n\nClose Borderlands 4, back up the old three files outside Paks, then replace them with this complete set.\n\nSee README.md for co-op setup and verification.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Cannot generate mod', str(exc))

    def open_output(self):
        path = ROOT/'output'
        path.mkdir(exist_ok=True)
        os.startfile(path)

if __name__ == '__main__':
    root = tk.Tk()
    Configurator(root)
    root.mainloop()
