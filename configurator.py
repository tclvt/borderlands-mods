"""French desktop interface for the Borderlands 4 difficulty mod builder."""
import json
import math
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from difficulty import ROOT, DEFAULTS, build, validate

BG, PANEL, CARD = '#101317', '#191e25', '#202630'
LINE, TEXT, MUTED, GOLD = '#303844', '#f2f3f5', '#98a5b7', '#f4cc53'
FONT = 'Segoe UI'
FIELDS = {
    'enemy_health': ('Santé des ennemis', 'Multiplie les points de vie des ennemis.', 'ENNEMIS'),
    'enemy_damage': ('Dégâts reçus', 'Inclut les attaques, les dangers et les dégâts auto-infligés.', 'SURVIE'),
    'player_damage': ('Vos dégâts', 'Ajuste les dégâts que vous infligez.', 'JOUEUR'),
    'player_durability': ('Votre résistance', 'Divise les dégâts reçus, bouclier compris. Ne change pas les PV max.', 'SURVIE'),
    'experience': ('Expérience', 'Ajuste les points d’expérience gagnés.', 'PROGRESSION'),
    'cash': ('Argent', 'Ajuste les gains d’argent.', 'RESSOURCES'),
    'eridium': ('Éridium', 'Ajuste les gains d’Éridium.', 'RESSOURCES'),
}
PRESETS = {
    'Neutre': dict.fromkeys(DEFAULTS, 1.0),
    'Défi en duo': DEFAULTS,
    'Brutal': DEFAULTS | dict(enemy_health=4, enemy_damage=2, player_damage=0.8),
    'Harder 2 d’origine': DEFAULTS | dict(enemy_health=1, enemy_damage=1.99, player_damage=0.5),
}
HINTS = ('Tous les multiplicateurs à 1', 'Ennemis ×2 · dégâts reçus ×1,5', 'Ennemis ×4 · dégâts reçus ×2', 'Les réglages du mod fourni')

def number(value):
    return f'{value:.6g}'.replace('.', ',')

def label(parent, text='', size=10, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent, text=text, fg=color, bg=parent.cget('bg'),
                    font=(FONT, size, 'bold' if bold else 'normal'), **kwargs)

def button(parent, text, command, primary=False):
    return tk.Button(parent, text=text, command=command, bg=GOLD if primary else CARD,
                     fg=BG if primary else TEXT, activebackground='#ffe28c' if primary else LINE,
                     activeforeground=BG if primary else TEXT, relief='flat', bd=0,
                     font=(FONT, 10, 'bold'), cursor='hand2', padx=12, pady=10,
                     highlightthickness=1, highlightbackground=GOLD if primary else LINE,
                     highlightcolor=TEXT)

class MultiplierSlider(tk.Canvas):
    """Logarithmic control: neutral at the centre, 0.01–100 at the edges."""
    def __init__(self, parent, variable, command):
        super().__init__(parent, height=22, width=200, bg=CARD, highlightthickness=0,
                         takefocus=True, cursor='hand2')
        self.variable, self.command = variable, command
        self.bind('<Configure>', self.draw)
        self.bind('<Button-1>', self.move)
        self.bind('<B1-Motion>', self.move)
        self.bind('<Left>', lambda _: self.nudge(-0.025))
        self.bind('<Right>', lambda _: self.nudge(0.025))
        self.bind('<Home>', lambda _: self.command(-2))
        self.bind('<End>', lambda _: self.command(2))
        self.bind('<FocusIn>', self.draw)
        self.bind('<FocusOut>', self.draw)
        variable.trace_add('write', self.draw)

    def draw(self, *_):
        self.delete('all')
        width = max(24, self.winfo_width())
        left, right, y = 8, width-8, 11
        x = left + (self.variable.get()+2)/4 * (right-left)
        centre = (left+right)/2
        self.create_line(left, y, right, y, fill=LINE, width=4, capstyle='round')
        self.create_line(centre, y, x, y, fill=GOLD, width=4, capstyle='round')
        self.create_line(centre, y-5, centre, y+5, fill=MUTED)
        if self.focus_get() == self:
            self.create_oval(x-9, y-9, x+9, y+9, outline=GOLD)
        self.create_oval(x-6, y-6, x+6, y+6, fill=GOLD, outline=GOLD)

    def move(self, event):
        self.focus_set()
        fraction = (event.x-8)/max(1, self.winfo_width()-16)
        self.command(4*min(1, max(0, fraction))-2)

    def nudge(self, delta):
        self.command(min(2, max(-2, self.variable.get()+delta)))

class Configurator:
    def __init__(self, window):
        self.window, self._batch = window, False
        self.values = {k: tk.StringVar(value=number(v)) for k, v in DEFAULTS.items()}
        self.preset = tk.StringVar(value='Personnalisé')
        self.status = tk.StringVar(value='Prêt à créer votre mod.')
        self.preview = tk.StringVar()
        self.scales, self.entries, self.effects, self.summary, self.tiles = {}, {}, {}, {}, {}
        self.saved_settings = None
        window.title('Borderlands 4 • Atelier de difficulté')
        window.geometry('1220x850')
        window.minsize(1080, 720)
        window.configure(bg=BG)
        window.columnconfigure(1, weight=1)
        window.rowconfigure(0, weight=1)
        style = ttk.Style(window)
        style.theme_use('clam')
        style.configure('TScale', background=CARD, troughcolor=BG, borderwidth=0,
                        lightcolor=GOLD, darkcolor=GOLD, sliderlength=16)
        style.configure('Vertical.TScrollbar', background=LINE, troughcolor=BG, borderwidth=0, arrowcolor=MUTED)
        self.sidebar()
        self.workspace()
        self.load_startup()
        for key, value in self.values.items():
            value.trace_add('write', lambda *_, k=key: self.changed(k))
        window.bind('<Control-Return>', lambda _: self.generate())
        self.update_preview()

    def sidebar(self):
        side = tk.Frame(self.window, bg=PANEL, width=228, padx=20, pady=25)
        side.grid(row=0, column=0, sticky='nsew')
        side.grid_propagate(False)
        label(side, 'BORDERLANDS', 19, GOLD, True).pack(anchor='w')
        label(side, '04 / ATELIER DE DIFFICULTÉ', 9, MUTED, True).pack(anchor='w', pady=(3, 22))
        label(side, 'VOTRE POINT DE DÉPART', 9, MUTED, True).pack(anchor='w', pady=(0, 12))
        for name, hint in zip(PRESETS, HINTS):
            tile = tk.Frame(side, bg=PANEL, highlightthickness=1, highlightbackground=LINE,
                            padx=12, pady=10, cursor='hand2', takefocus=True)
            tile.pack(fill='x', pady=(0, 8))
            title = label(tile, name, 11, bold=True)
            title.pack(anchor='w')
            subtitle = label(tile, hint, 9, MUTED, wraplength=155, justify='left')
            subtitle.pack(anchor='w', pady=(4, 0))
            for widget in (tile, title, subtitle):
                widget.bind('<Button-1>', lambda _, n=name: self.apply_preset(n))
            tile.bind('<Return>', lambda _, n=name: self.apply_preset(n))
            tile.bind('<space>', lambda _, n=name: self.apply_preset(n))
            self.tiles[name] = (tile, title, subtitle)
        tools = tk.Frame(side, bg=PANEL)
        tools.pack(side='bottom', fill='x')
        label(tools, 'PROFILS', 9, MUTED, True).pack(anchor='w', pady=(0, 10))
        button(tools, 'Charger un profil', self.load_profile).pack(fill='x', pady=(0, 8))
        button(tools, 'Enregistrer le profil', self.save_profile).pack(fill='x')
        label(tools, 'LOCAL / SANS SDK', 9, MUTED, True).pack(anchor='w', pady=(16, 5))
        label(tools, 'Réglages appliqués au prochain\ndémarrage du jeu.', 9, MUTED, justify='left').pack(anchor='w')

    def workspace(self):
        main = tk.Frame(self.window, bg=BG, padx=26, pady=24)
        main.grid(row=0, column=1, sticky='nsew')
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        header = tk.Frame(main, bg=BG)
        header.grid(row=0, column=0, sticky='ew')
        label(header, 'À VOUS DE FIXER LES RÈGLES', 9, GOLD, True).pack(anchor='w')
        label(header, 'Votre partie. Votre difficulté.', 24, bold=True).pack(anchor='w', pady=(6, 4))
        label(header, 'Préparez le prochain défi avec votre partenaire.', 11, MUTED).pack(anchor='w')
        bar = tk.Frame(main, bg=BG)
        bar.grid(row=1, column=0, sticky='ew', pady=(22, 18))
        self.tab_buttons = {}
        for name in ('Combat', 'Progression'):
            tab = button(bar, name, lambda n=name: self.select_tab(n))
            tab.pack(side='left', padx=(0, 8))
            self.tab_buttons[name] = tab
        label(bar, '1 = normal · 2 = double', 10, MUTED).pack(side='right')
        body = tk.Frame(main, bg=BG)
        body.grid(row=2, column=0, sticky='nsew')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        area = tk.Frame(body, bg=BG)
        area.grid(row=0, column=0, sticky='nsew', padx=(0, 20))
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(area, bg=BG, highlightthickness=0, width=400)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(area, orient='vertical', command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        self.cards = tk.Frame(self.canvas, bg=BG)
        item = self.canvas.create_window(0, 0, window=self.cards, anchor='nw')
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(item, width=e.width))
        self.cards.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.window.bind_all('<MouseWheel>', self.scroll)
        self.groups = {}
        for tab, keys in [('Combat', list(FIELDS)[:4]), ('Progression', list(FIELDS)[4:])]:
            group = tk.Frame(self.cards, bg=BG)
            self.groups[tab] = group
            for key in keys:
                self.field_card(group, key)
        self.preview_panel(body)
        footer = tk.Frame(main, bg=BG)
        footer.grid(row=3, column=0, sticky='ew', pady=(16, 0))
        label(footer, textvariable=self.status, size=9, color=MUTED, wraplength=600, justify='left').pack(side='left')
        guide = label(footer, 'Guide d’installation ↗', 9, GOLD, cursor='hand2')
        guide.pack(side='right')
        guide.bind('<Button-1>', lambda _: self.open_path(ROOT/'README.md'))
        self.select_tab('Combat')

    def field_card(self, parent, key):
        title, hint, tag = FIELDS[key]
        card = tk.Frame(parent, bg=CARD, padx=16, pady=12, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill='x', pady=(0, 10))
        card.columnconfigure(0, weight=1)
        label(card, tag, 8, GOLD, True).grid(row=0, column=0, sticky='w')
        reset = label(card, 'Réinitialiser', 8, MUTED, cursor='hand2')
        reset.grid(row=0, column=1, columnspan=2, sticky='e')
        reset.bind('<Button-1>', lambda _: self.values[key].set('1'))
        label(card, title, 13, bold=True).grid(row=1, column=0, sticky='w', pady=(2, 0))
        box = tk.Frame(card, bg=BG, highlightbackground=LINE, highlightthickness=1)
        box.grid(row=1, column=1, columnspan=2, sticky='e')
        label(box, '×', 12, GOLD).pack(side='left', padx=(8, 0))
        entry = tk.Entry(box, textvariable=self.values[key], width=7, bg=BG, fg=TEXT, insertbackground=GOLD,
                         relief='flat', font=(FONT, 13, 'bold'), justify='right', selectbackground=GOLD, selectforeground=BG)
        entry.pack(side='left', padx=7, pady=4)
        self.entries[key] = box
        hint_label = label(card, hint, 9, MUTED, wraplength=370, justify='left')
        hint_label.grid(row=2, column=0, columnspan=3, sticky='w', pady=(7, 3))
        card.bind('<Configure>', lambda e: hint_label.configure(wraplength=max(180, e.width-36)))
        slider_var = tk.DoubleVar(value=0)
        scale = MultiplierSlider(card, slider_var, lambda v, k=key: self.slide(k, v))
        scale.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(2, 0))
        self.scales[key] = slider_var
        label(card, '0,01', 8, MUTED).grid(row=4, column=0, sticky='w')
        effect = tk.StringVar()
        label(card, textvariable=effect, size=8, color=GOLD).grid(row=4, column=0, columnspan=3)
        label(card, '100', 8, MUTED).grid(row=4, column=2, sticky='e')
        self.effects[key] = effect

    def preview_panel(self, parent):
        panel = tk.Frame(parent, bg=PANEL, width=252, padx=18, pady=14, highlightthickness=1, highlightbackground=LINE)
        panel.grid(row=0, column=1, sticky='ns')
        panel.pack_propagate(False)
        label(panel, 'APERÇU DU MOD', 9, MUTED, True).pack(anchor='w')
        label(panel, textvariable=self.preset, size=15, bold=True, wraplength=210, justify='left').pack(anchor='w', pady=(6, 10))
        for key, title in [('health', 'SANTÉ ENNEMIE'), ('damage', 'VOS DÉGÂTS'), ('incoming', 'DÉGÂTS REÇUS FINAUX')]:
            label(panel, title, 8, MUTED, True).pack(anchor='w')
            var = tk.StringVar(value='—')
            label(panel, textvariable=var, size=22, color=GOLD if key == 'incoming' else TEXT, bold=True).pack(anchor='w', pady=(0, 6))
            self.summary[key] = var
        self.formula = tk.StringVar()
        label(panel, textvariable=self.formula, size=9, color=MUTED, wraplength=210, justify='left').pack(anchor='w')
        bottom = tk.Frame(panel, bg=PANEL)
        bottom.pack(side='bottom', fill='x')
        self.generate_button = button(bottom, 'Générer mon mod →', self.generate, primary=True)
        self.generate_button.pack(fill='x', pady=(12, 8))
        button(bottom, 'Ouvrir le dossier', self.open_output).pack(fill='x')
        label(bottom, 'Mode Normal · même mod sur les 2 PC\nRedémarrage du jeu nécessaire', 8, MUTED,
              justify='left', wraplength=210).pack(anchor='w', pady=(14, 0))

    def scroll(self, event):
        hovered = self.window.winfo_containing(event.x_root, event.y_root)
        if hovered is not None and str(hovered).startswith(str(self.canvas)):
            self.canvas.yview_scroll(-int(event.delta/120), 'units')

    def select_tab(self, name):
        for tab, group in self.groups.items():
            group.pack_forget()
            self.tab_buttons[tab].configure(bg=GOLD if tab == name else CARD, fg=BG if tab == name else MUTED)
        self.groups[name].pack(fill='x')
        self.canvas.yview_moveto(0)

    def settings(self):
        result = {}
        for key, var in self.values.items():
            try:
                value = float(var.get().strip().replace(',', '.'))
            except ValueError:
                raise ValueError(f'« {FIELDS[key][0]} » : saisissez un nombre.') from None
            if not math.isfinite(value) or not 0.01 <= value <= 100:
                raise ValueError(f'« {FIELDS[key][0]} » : choisissez une valeur de 0,01 à 100.')
            result[key] = value
        return validate(result)

    def changed(self, key):
        if not self._batch:
            self.update_preview()

    def slide(self, key, value):
        if not self._batch:
            self.values[key].set(number(round(10 ** float(value), 2)))

    def set_values(self, settings):
        self._batch = True
        try:
            for key, value in validate(settings).items():
                self.values[key].set(str(value).replace('.', ','))
        finally:
            self._batch = False
        self.update_preview()

    def apply_preset(self, name=None):
        name = name if isinstance(name, str) else self.preset.get()
        if name in PRESETS:
            self.set_values(PRESETS[name])

    def update_preview(self, *_):
        self._batch = True
        try:
            for key, var in self.values.items():
                try:
                    value = float(var.get().replace(',', '.'))
                    valid = math.isfinite(value) and 0.01 <= value <= 100
                except ValueError:
                    valid = False
                self.entries[key].configure(highlightbackground=LINE if valid else '#ef867f')
                if valid:
                    self.scales[key].set(math.log10(value))
                    delta = (value-1)*100
                    effect = 'Valeur normale' if abs(delta) < 0.001 else f'{"+" if delta > 0 else ""}{number(delta)} %'
                    if key == 'player_durability' and value != 1:
                        effect = f'Dégâts reçus ÷ {number(value)}'
                    self.effects[key].set(effect)
                else:
                    self.effects[key].set('De 0,01 à 100')
            try:
                settings = self.settings()
            except ValueError as exc:
                self.preset.set('Personnalisé')
                for var in self.summary.values():
                    var.set('—')
                self.formula.set(str(exc))
                self.generate_button.configure(state='disabled')
                self.preview.set(str(exc))
            else:
                name = next((n for n, s in PRESETS.items() if all(math.isclose(settings[k], s[k]) for k in settings)), 'Personnalisé')
                self.preset.set(name)
                incoming = settings['enemy_damage']/settings['player_durability']
                for key, value in [('health', settings['enemy_health']), ('damage', settings['player_damage']), ('incoming', incoming)]:
                    self.summary[key].set('×'+number(value))
                self.formula.set(f"Dégâts reçus {number(settings['enemy_damage'])}\n÷ résistance {number(settings['player_durability'])}")
                self.preview.set(f"PV ennemis ×{number(settings['enemy_health'])} · dégâts reçus ×{number(incoming)}")
                self.generate_button.configure(state='normal')
                if self.saved_settings is not None and settings != self.saved_settings:
                    self.status.set('Réglages modifiés · générez à nouveau pour mettre à jour le mod.')
                elif self.saved_settings is not None:
                    self.status.set('Réglages identiques au dernier mod généré.')
            for name, (tile, title, subtitle) in self.tiles.items():
                selected = name == self.preset.get()
                color = '#302c20' if selected else PANEL
                tile.configure(bg=color, highlightbackground=GOLD if selected else LINE)
                title.configure(bg=color, fg=GOLD if selected else TEXT)
                subtitle.configure(bg=color)
        finally:
            self._batch = False

    def load_startup(self):
        path = ROOT/'settings.json'
        if path.exists():
            try:
                self.set_values(json.loads(path.read_text(encoding='utf-8-sig')))
            except (OSError, ValueError) as exc:
                self.status.set(f'Profil précédent illisible : {exc}')

    def load_profile(self):
        path = filedialog.askopenfilename(parent=self.window, title='Charger un profil', filetypes=[('Profil de difficulté', '*.json')])
        if path:
            try:
                self.set_values(json.loads(Path(path).read_text(encoding='utf-8-sig')))
                self.status.set('Profil chargé · vous pouvez maintenant générer votre mod.')
            except (OSError, ValueError) as exc:
                messagebox.showerror('Profil illisible', str(exc), parent=self.window)

    def save_profile(self):
        try:
            settings = self.settings()
        except ValueError as exc:
            messagebox.showerror('Réglages à corriger', str(exc), parent=self.window)
            return
        path = filedialog.asksaveasfilename(parent=self.window, title='Enregistrer le profil', defaultextension='.json',
                                           initialfile='mon-profil.json', filetypes=[('Profil de difficulté', '*.json')])
        if path:
            try:
                Path(path).write_text(json.dumps(settings, indent=2)+'\n', encoding='utf-8')
                self.status.set('Profil enregistré.')
            except OSError as exc:
                messagebox.showerror('Enregistrement impossible', str(exc), parent=self.window)

    def generate(self):
        try:
            settings = self.settings()
            build(settings)
            (ROOT/'settings.json').write_text(json.dumps(settings, indent=2)+'\n', encoding='utf-8')
            self.saved_settings = settings.copy()
            self.status.set('✓ Mod généré dans output · fermez le jeu puis copiez les 3 fichiers. Installation : voir le guide.')
        except (OSError, ValueError) as exc:
            messagebox.showerror('Génération impossible', str(exc), parent=self.window)

    def open_path(self, path):
        try:
            os.startfile(path)
        except OSError as exc:
            messagebox.showerror('Ouverture impossible', str(exc), parent=self.window)

    def open_output(self):
        try:
            path = ROOT/'output'
            path.mkdir(exist_ok=True)
            self.open_path(path)
        except OSError as exc:
            messagebox.showerror('Dossier inaccessible', str(exc), parent=self.window)

if __name__ == '__main__':
    root = tk.Tk()
    Configurator(root)
    root.mainloop()
