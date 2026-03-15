"""
Priorityly – main tkinter application.

Layout
------
Left  : Task tree panel  (add / edit / delete tasks & subtasks)
Right : Notebook with four tabs
        1. Matriz Eisenhower  – visual 2×2 grid
        2. Lista Priorizada   – flat sorted list with quadrant badges
        3. Comparar           – pairwise comparison wizard
        4. Acerca de          – brief instructions
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Optional

from .models import Task, QUADRANT_COLORS, QUADRANT_NAMES
from .storage import Storage
from .priority import ComparisonEngine, sorted_flat, sorted_by_priority


# ======================================================================
# Helpers
# ======================================================================

PAD = 6
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BADGE = ("Segoe UI", 9, "bold")

BG = "#f5f5f5"
PANEL_BG = "#ffffff"
ACCENT = "#1565c0"
ACCENT_LIGHT = "#e3f2fd"


def _badge(parent: tk.Widget, text: str, bg: str, fg: str = "white") -> tk.Label:
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=FONT_BADGE, padx=6, pady=2, relief="flat")


# ======================================================================
# Task dialog (add / edit)
# ======================================================================

class TaskDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, title: str, task: Optional[Task] = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: Optional[dict] = None
        self._build(task)
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _build(self, task: Optional[Task]):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(frame, text="Título *", font=FONT_SMALL).grid(row=0, column=0, sticky="w")
        self._title_var = tk.StringVar(value=task.title if task else "")
        ttk.Entry(frame, textvariable=self._title_var, width=44).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # Description
        ttk.Label(frame, text="Descripción", font=FONT_SMALL).grid(row=2, column=0, sticky="w")
        self._desc = tk.Text(frame, width=44, height=4, font=FONT_NORMAL, wrap="word")
        self._desc.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        if task:
            self._desc.insert("1.0", task.description)

        # Importance / Urgency sliders
        ttk.Label(frame, text="Importancia (1–10)", font=FONT_SMALL).grid(
            row=4, column=0, sticky="w")
        self._imp_var = tk.IntVar(value=task.importance if task else 5)
        self._imp_lbl = ttk.Label(frame, text=str(self._imp_var.get()), width=3)
        ttk.Scale(frame, from_=1, to=10, variable=self._imp_var, orient="horizontal",
                  command=lambda v: self._imp_lbl.config(text=str(int(float(v))))).grid(
            row=4, column=1, sticky="ew")
        self._imp_lbl.grid(row=4, column=2, padx=4)

        ttk.Label(frame, text="Urgencia (1–10)", font=FONT_SMALL).grid(
            row=5, column=0, sticky="w", pady=(6, 0))
        self._urg_var = tk.IntVar(value=task.urgency if task else 5)
        self._urg_lbl = ttk.Label(frame, text=str(self._urg_var.get()), width=3)
        ttk.Scale(frame, from_=1, to=10, variable=self._urg_var, orient="horizontal",
                  command=lambda v: self._urg_lbl.config(text=str(int(float(v))))).grid(
            row=5, column=1, sticky="ew", pady=(6, 0))
        self._urg_lbl.grid(row=5, column=2, padx=4)

        frame.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Guardar", command=self._save).pack(side="right")

    def _save(self):
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Campo requerido", "El título no puede estar vacío.",
                                   parent=self)
            return
        self.result = {
            "title": title,
            "description": self._desc.get("1.0", "end-1c").strip(),
            "importance": int(self._imp_var.get()),
            "urgency": int(self._urg_var.get()),
        }
        self.destroy()


# ======================================================================
# Left panel: Task Tree
# ======================================================================

class TaskTreePanel(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "App"):
        super().__init__(parent, padding=PAD)
        self.app = app
        self._build()

    def _build(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, PAD))

        ttk.Label(toolbar, text="Tareas", font=FONT_TITLE).pack(side="left")

        btn_add_root = ttk.Button(toolbar, text="+ Tarea", width=9,
                                  command=self._add_root)
        btn_add_root.pack(side="right", padx=2)

        btn_add_child = ttk.Button(toolbar, text="+ Sub", width=7,
                                   command=self._add_child)
        btn_add_child.pack(side="right", padx=2)

        # Tree view
        cols = ("quadrant", "imp", "urg")
        self.tree = ttk.Treeview(self, columns=cols, selectmode="browse",
                                  show="tree headings")
        self.tree.heading("#0", text="Título")
        self.tree.heading("quadrant", text="Q")
        self.tree.heading("imp", text="IMP")
        self.tree.heading("urg", text="URG")
        self.tree.column("#0", width=180, stretch=True)
        self.tree.column("quadrant", width=30, anchor="center")
        self.tree.column("imp", width=36, anchor="center")
        self.tree.column("urg", width=36, anchor="center")

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        # Context menu
        self._ctx = tk.Menu(self, tearoff=False)
        self._ctx.add_command(label="Editar", command=self._edit)
        self._ctx.add_command(label="Agregar subtarea", command=self._add_child)
        self._ctx.add_separator()
        self._ctx.add_command(label="Eliminar", command=self._delete)

        self.tree.bind("<Button-3>", self._show_ctx)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        # Tag colours per quadrant
        for q, colour in QUADRANT_COLORS.items():
            self.tree.tag_configure(f"q{q}", foreground=colour)

    # ---------------------------------------------------------------- #
    def refresh(self):
        """Rebuild tree from app.tasks."""
        self.tree.delete(*self.tree.get_children())
        self._insert_children(None, "")

    def _insert_children(self, parent_id: Optional[str], tree_parent: str):
        tasks = self.app.tasks
        children = [t for t in tasks.values() if t.parent_id == parent_id]
        children.sort(key=lambda t: t.priority_score, reverse=True)
        for task in children:
            node = self.tree.insert(
                tree_parent, "end",
                iid=task.id,
                text=task.title,
                values=(task.quadrant, task.importance, task.urgency),
                tags=(f"q{task.quadrant}",),
                open=True,
            )
            self._insert_children(task.id, node)

    # ---------------------------------------------------------------- #
    def _selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _show_ctx(self, event: tk.Event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._ctx.post(event.x_root, event.y_root)

    def _add_root(self):
        dlg = TaskDialog(self, "Nueva tarea")
        if dlg.result:
            task = Task(**dlg.result)
            self.app.tasks[task.id] = task
            self.app.save_and_refresh()

    def _add_child(self):
        parent_id = self._selected_id()
        if not parent_id:
            messagebox.showinfo("Sin selección",
                                "Selecciona una tarea para agregar una subtarea.")
            return
        parent = self.app.tasks[parent_id]
        dlg = TaskDialog(self, f"Subtarea de: {parent.title}")
        if dlg.result:
            task = Task(**dlg.result, parent_id=parent_id)
            self.app.tasks[task.id] = task
            self.app.save_and_refresh()

    def _edit(self):
        task_id = self._selected_id()
        if not task_id:
            return
        task = self.app.tasks[task_id]
        dlg = TaskDialog(self, "Editar tarea", task)
        if dlg.result:
            task.title = dlg.result["title"]
            task.description = dlg.result["description"]
            task.importance = dlg.result["importance"]
            task.urgency = dlg.result["urgency"]
            self.app.save_and_refresh()

    def _delete(self):
        task_id = self._selected_id()
        if not task_id:
            return
        task = self.app.tasks[task_id]
        if not messagebox.askyesno("Confirmar",
                                   f'¿Eliminar "{task.title}" y todas sus subtareas?'):
            return
        self.app.tasks = self.app.storage.delete_task(self.app.tasks, task_id)
        self.app.save_and_refresh()


# ======================================================================
# Tab 1: Eisenhower Matrix
# ======================================================================

class MatrixTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "App"):
        super().__init__(parent, padding=PAD)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Matriz de Eisenhower", font=FONT_TITLE).pack(pady=(0, PAD))

        grid = ttk.Frame(self)
        grid.pack(fill="both", expand=True)

        # Column / row headers
        ttk.Label(grid, text="", width=14).grid(row=0, column=0)
        ttk.Label(grid, text="IMPORTANTE", font=("Segoe UI", 9, "bold"),
                  foreground="#1565c0").grid(row=0, column=1, padx=4)
        ttk.Label(grid, text="NO IMPORTANTE", font=("Segoe UI", 9, "bold"),
                  foreground="#757575").grid(row=0, column=2, padx=4)

        ttk.Label(grid, text="URGENTE", font=("Segoe UI", 9, "bold"),
                  foreground="#c62828").grid(row=1, column=0, sticky="e", padx=4)
        ttk.Label(grid, text="NO URGENTE", font=("Segoe UI", 9, "bold"),
                  foreground="#424242").grid(row=2, column=0, sticky="e", padx=4)

        # Four quadrant frames
        self._q_frames: Dict[int, tk.Frame] = {}
        positions = {1: (1, 1), 2: (2, 1), 3: (1, 2), 4: (2, 2)}
        labels = {
            1: "Hacer ya",
            2: "Planificar",
            3: "Delegar",
            4: "Eliminar",
        }
        for q, (row, col) in positions.items():
            outer = tk.Frame(grid, bg=QUADRANT_COLORS[q], bd=1, relief="ridge")
            outer.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            tk.Label(outer, text=labels[q], bg=QUADRANT_COLORS[q], fg="white",
                     font=FONT_BADGE).pack(anchor="w", padx=6, pady=3)
            inner = tk.Frame(outer, bg="#fafafa")
            inner.pack(fill="both", expand=True, padx=2, pady=(0, 2))
            self._q_frames[q] = inner

        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)
        grid.rowconfigure(1, weight=1)
        grid.rowconfigure(2, weight=1)

    def refresh(self):
        for frame in self._q_frames.values():
            for w in frame.winfo_children():
                w.destroy()

        for task in sorted_by_priority(self.app.tasks):
            q = task.quadrant
            frame = self._q_frames[q]
            row = tk.Frame(frame, bg="#fafafa")
            row.pack(fill="x", padx=4, pady=1)
            tk.Label(row, text=f"• {task.title}", bg="#fafafa",
                     font=FONT_NORMAL, anchor="w",
                     wraplength=200).pack(side="left")
            tk.Label(row, text=f"I:{task.importance} U:{task.urgency}",
                     bg="#fafafa", font=FONT_SMALL,
                     foreground="#9e9e9e").pack(side="right")


# ======================================================================
# Tab 2: Priority List
# ======================================================================

class PriorityListTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "App"):
        super().__init__(parent, padding=PAD)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Lista Priorizada", font=FONT_TITLE).pack(pady=(0, PAD))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(container, bg=PANEL_BG, highlightthickness=0)
        scroll = ttk.Scrollbar(container, orient="vertical",
                               command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scroll.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._list_frame = tk.Frame(self._canvas, bg=PANEL_BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")

        self._list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def refresh(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        rank = 1
        last_parent = None
        for depth, task in sorted_flat(self.app.tasks):
            if depth == 0:
                last_parent = task.id
                # Root task row
                row = tk.Frame(self._list_frame, bg=PANEL_BG, pady=3)
                row.pack(fill="x", padx=6)

                tk.Label(row, text=f"{rank:>3}.", font=("Segoe UI", 11, "bold"),
                         bg=PANEL_BG, fg="#424242", width=4).pack(side="left")

                badge_color = QUADRANT_COLORS[task.quadrant]
                tk.Label(row, text=f"Q{task.quadrant}", bg=badge_color, fg="white",
                         font=FONT_BADGE, padx=5, pady=1).pack(side="left", padx=4)

                tk.Label(row, text=task.title, font=("Segoe UI", 11),
                         bg=PANEL_BG, anchor="w").pack(side="left", fill="x", expand=True)

                tk.Label(row, text=f"IMP {task.importance}  URG {task.urgency}",
                         font=FONT_SMALL, bg=PANEL_BG,
                         foreground="#9e9e9e").pack(side="right", padx=6)

                ttk.Separator(self._list_frame, orient="horizontal").pack(
                    fill="x", padx=6)
                rank += 1

            else:
                # Subtask row (indented)
                indent = depth * 20
                row = tk.Frame(self._list_frame, bg="#f9f9f9", pady=1)
                row.pack(fill="x", padx=6)

                tk.Label(row, text="", width=indent // 10,
                         bg="#f9f9f9").pack(side="left")
                tk.Label(row, text=f"↳ {task.title}", font=FONT_SMALL,
                         bg="#f9f9f9", anchor="w",
                         foreground="#555555").pack(side="left", fill="x", expand=True)
                tk.Label(row, text=f"I:{task.importance} U:{task.urgency}",
                         font=FONT_SMALL, bg="#f9f9f9",
                         foreground="#bdbdbd").pack(side="right", padx=6)


# ======================================================================
# Tab 3: Pairwise Comparison
# ======================================================================

class CompareTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "App"):
        super().__init__(parent, padding=PAD)
        self.app = app
        self._engine: Optional[ComparisonEngine] = None
        self._task_a: Optional[Task] = None
        self._task_b: Optional[Task] = None
        self._build()

    def _build(self):
        ttk.Label(self, text="Comparación por Pares", font=FONT_TITLE).pack(pady=(0, 4))
        ttk.Label(
            self,
            text="Compara dos tareas a la vez para afinar su importancia y urgencia.",
            font=FONT_SMALL, foreground="#666666",
        ).pack(pady=(0, PAD))

        self._status_lbl = ttk.Label(self, text="", font=FONT_SMALL,
                                     foreground="#1565c0")
        self._status_lbl.pack()

        # Card area
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill="x", expand=False, pady=PAD)
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(2, weight=1)

        self._card_a = self._make_card(cards_frame)
        self._card_a.grid(row=0, column=0, padx=8, sticky="nsew")

        ttk.Label(cards_frame, text="vs", font=("Segoe UI", 16, "bold"),
                  foreground="#9e9e9e").grid(row=0, column=1)

        self._card_b = self._make_card(cards_frame)
        self._card_b.grid(row=0, column=2, padx=8, sticky="nsew")

        # Importance question
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(self, text="¿Cuál es MÁS IMPORTANTE?",
                  font=("Segoe UI", 10, "bold")).pack()

        imp_frame = ttk.Frame(self)
        imp_frame.pack(pady=4)
        self._btn_imp_a = ttk.Button(imp_frame, text="A", width=14,
                                     command=lambda: self._set_imp("A"))
        self._btn_imp_a.pack(side="left", padx=4)
        ttk.Button(imp_frame, text="Igual", width=10,
                   command=lambda: self._set_imp("TIE")).pack(side="left", padx=4)
        self._btn_imp_b = ttk.Button(imp_frame, text="B", width=14,
                                     command=lambda: self._set_imp("B"))
        self._btn_imp_b.pack(side="left", padx=4)

        self._imp_choice_lbl = ttk.Label(self, text="", font=FONT_SMALL,
                                         foreground="#1565c0")
        self._imp_choice_lbl.pack()

        # Urgency question
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(self, text="¿Cuál es MÁS URGENTE?",
                  font=("Segoe UI", 10, "bold")).pack()

        urg_frame = ttk.Frame(self)
        urg_frame.pack(pady=4)
        self._btn_urg_a = ttk.Button(urg_frame, text="A", width=14,
                                     command=lambda: self._set_urg("A"))
        self._btn_urg_a.pack(side="left", padx=4)
        ttk.Button(urg_frame, text="Igual", width=10,
                   command=lambda: self._set_urg("TIE")).pack(side="left", padx=4)
        self._btn_urg_b = ttk.Button(urg_frame, text="B", width=14,
                                     command=lambda: self._set_urg("B"))
        self._btn_urg_b.pack(side="left", padx=4)

        self._urg_choice_lbl = ttk.Label(self, text="", font=FONT_SMALL,
                                         foreground="#1565c0")
        self._urg_choice_lbl.pack()

        # Action row
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=8)
        action_frame = ttk.Frame(self)
        action_frame.pack()
        self._btn_confirm = ttk.Button(action_frame, text="Confirmar y seguir",
                                       command=self._confirm, state="disabled")
        self._btn_confirm.pack(side="left", padx=6)
        ttk.Button(action_frame, text="Saltar", command=self._skip).pack(side="left", padx=6)
        ttk.Button(action_frame, text="Reiniciar comparaciones",
                   command=self._restart).pack(side="left", padx=6)

        self._imp_winner: Optional[str] = None
        self._urg_winner: Optional[str] = None

    def _make_card(self, parent: tk.Widget) -> tk.Frame:
        card = tk.Frame(parent, bg=ACCENT_LIGHT, bd=1, relief="solid",
                        padx=10, pady=10)
        card.title_lbl = tk.Label(card, text="", font=("Segoe UI", 11, "bold"),
                                   bg=ACCENT_LIGHT, wraplength=200, justify="left")
        card.title_lbl.pack(anchor="w")
        card.desc_lbl = tk.Label(card, text="", font=FONT_SMALL,
                                  bg=ACCENT_LIGHT, foreground="#555555",
                                  wraplength=200, justify="left")
        card.desc_lbl.pack(anchor="w", pady=(4, 0))
        card.scores_lbl = tk.Label(card, text="", font=FONT_SMALL,
                                    bg=ACCENT_LIGHT, foreground="#1565c0")
        card.scores_lbl.pack(anchor="w", pady=(6, 0))
        return card

    def _fill_card(self, card: tk.Frame, task: Task, letter: str):
        card.title_lbl.config(text=f"[{letter}]  {task.title}")
        card.desc_lbl.config(text=task.description[:120] if task.description else "")
        card.scores_lbl.config(
            text=f"IMP: {task.importance}   URG: {task.urgency}   {task.quadrant_label}")

    # ---------------------------------------------------------------- #
    def refresh(self):
        """Called whenever tasks change."""
        if len(self.app.tasks) < 2:
            self._status_lbl.config(
                text="Agrega al menos 2 tareas para poder comparar.")
            self._clear_cards()
            return
        if self._engine is None:
            self._engine = ComparisonEngine(self.app.tasks)
        else:
            self._engine.refresh(self.app.tasks)
        self._load_next()

    def _load_next(self):
        self._imp_winner = None
        self._urg_winner = None
        self._imp_choice_lbl.config(text="")
        self._urg_choice_lbl.config(text="")
        self._btn_confirm.config(state="disabled")

        if self._engine is None or not self._engine.has_pairs():
            self._status_lbl.config(
                text="Todas las comparaciones completadas. Revisa la Lista Priorizada.")
            self._clear_cards()
            return

        pair = self._engine.next_pair()
        if pair is None:
            self._status_lbl.config(text="Sin más pares disponibles.")
            self._clear_cards()
            return

        self._task_a, self._task_b = pair
        self._fill_card(self._card_a, self._task_a, "A")
        self._fill_card(self._card_b, self._task_b, "B")
        remaining = self._engine.pairs_remaining()
        self._status_lbl.config(
            text=f"Comparación activa  |  {remaining} pares restantes en esta ronda")

    def _clear_cards(self):
        for card in (self._card_a, self._card_b):
            card.title_lbl.config(text="—")
            card.desc_lbl.config(text="")
            card.scores_lbl.config(text="")
        self._task_a = self._task_b = None

    def _set_imp(self, choice: str):
        self._imp_winner = choice
        label = {"A": self._task_a.title if self._task_a else "A",
                 "B": self._task_b.title if self._task_b else "B",
                 "TIE": "Igual"}.get(choice, "")
        self._imp_choice_lbl.config(text=f"Seleccionaste: {label}")
        self._check_ready()

    def _set_urg(self, choice: str):
        self._urg_winner = choice
        label = {"A": self._task_a.title if self._task_a else "A",
                 "B": self._task_b.title if self._task_b else "B",
                 "TIE": "Igual"}.get(choice, "")
        self._urg_choice_lbl.config(text=f"Seleccionaste: {label}")
        self._check_ready()

    def _check_ready(self):
        if self._imp_winner and self._urg_winner:
            self._btn_confirm.config(state="normal")

    def _confirm(self):
        if not (self._task_a and self._task_b and
                self._imp_winner and self._urg_winner):
            return
        a, b = self._task_a, self._task_b

        def winner_loser(choice):
            return (a.id, b.id) if choice == "A" else (b.id, a.id)

        if self._imp_winner == "TIE" and self._urg_winner == "TIE":
            self._engine.record_tie(a.id, b.id)
        else:
            wi, li = winner_loser(self._imp_winner) if self._imp_winner != "TIE" \
                else (a.id, a.id)
            wu, lu = winner_loser(self._urg_winner) if self._urg_winner != "TIE" \
                else (a.id, a.id)
            self._engine.record(wi, li, wu, lu)

        self.app.save_and_refresh(refresh_compare=False)
        self._load_next()

    def _skip(self):
        self._load_next()

    def _restart(self):
        if self._engine:
            self._engine.refresh(self.app.tasks)
        self._load_next()


# ======================================================================
# Tab 4: About
# ======================================================================

class AboutTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, app: "App"):
        super().__init__(parent, padding=24)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Priorityly", font=("Segoe UI", 18, "bold")).pack()
        ttk.Label(self, text="Asistente de planificación basado en el Cuadrante de Eisenhower",
                  font=FONT_NORMAL, foreground="#555").pack(pady=4)

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=12)

        help_text = (
            "CÓMO USAR\n\n"
            "1. Agrega tus tareas, metas e intenciones en el panel izquierdo.\n"
            "   Puedes organizarlas en árbol: tarea → subtarea → sub-subtarea.\n\n"
            "2. Asigna manualmente IMPORTANCIA y URGENCIA al crear/editar cada tarea\n"
            "   (escala 1–10).  >=6 = sí;  <=5 = no.\n\n"
            "3. Usa la pestaña COMPARAR para refinar las prioridades mediante\n"
            "   comparación directa de pares: el sistema te muestra dos tareas\n"
            "   y tú decides cuál es más importante y cuál más urgente.\n\n"
            "4. Consulta la MATRIZ DE EISENHOWER para ver tus tareas agrupadas\n"
            "   en los 4 cuadrantes.\n\n"
            "5. La LISTA PRIORIZADA muestra todas las tareas de mayor a menor\n"
            "   prioridad, con subtareas anidadas bajo su tarea padre.\n\n"
            "CUADRANTES\n\n"
            "  Q1  Urgente + Importante   → Hacer ya\n"
            "  Q2  No Urgente + Importante → Planificar / Agendar\n"
            "  Q3  Urgente + No Importante → Delegar\n"
            "  Q4  No Urgente + No Import  → Eliminar / Ignorar\n\n"
            "Los datos se guardan automáticamente en:\n"
            "  ~/.priorityly/tasks.json"
        )

        text = tk.Text(self, font=FONT_NORMAL, wrap="word",
                       bg=BG, relief="flat", state="normal",
                       height=28, width=62)
        text.insert("1.0", help_text)
        text.config(state="disabled")
        text.pack(fill="both", expand=True)

    def refresh(self):
        pass


# ======================================================================
# Main Application
# ======================================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Priorityly – Planificación por Prioridades")
        self.geometry("1100x700")
        self.minsize(800, 560)
        self.configure(bg=BG)

        self.storage = Storage()
        self.tasks: Dict[str, Task] = self.storage.load()

        self._setup_style()
        self._build_layout()
        self.save_and_refresh()

    # ---------------------------------------------------------------- #
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, font=FONT_NORMAL)
        style.configure("TButton", font=FONT_NORMAL, padding=4)
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(10, 4))

    def _build_layout(self):
        # Horizontal paned window
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Left: task tree
        left_frame = ttk.Frame(paned, padding=0)
        self._task_panel = TaskTreePanel(left_frame, self)
        self._task_panel.pack(fill="both", expand=True)
        paned.add(left_frame, weight=1)

        # Right: notebook
        right_frame = ttk.Frame(paned)
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill="both", expand=True)

        self._matrix_tab = MatrixTab(notebook, self)
        self._list_tab = PriorityListTab(notebook, self)
        self._compare_tab = CompareTab(notebook, self)
        self._about_tab = AboutTab(notebook, self)

        notebook.add(self._matrix_tab, text="  Matriz  ")
        notebook.add(self._list_tab, text="  Lista Priorizada  ")
        notebook.add(self._compare_tab, text="  Comparar  ")
        notebook.add(self._about_tab, text="  Ayuda  ")

        right_frame.pack(fill="both", expand=True)
        paned.add(right_frame, weight=2)

    # ---------------------------------------------------------------- #
    def save_and_refresh(self, refresh_compare: bool = True):
        self.storage.save(self.tasks)
        self._task_panel.refresh()
        self._matrix_tab.refresh()
        self._list_tab.refresh()
        if refresh_compare:
            self._compare_tab.refresh()


def run():
    app = App()
    app.mainloop()
