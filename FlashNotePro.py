import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import winsound
from datetime import datetime, timedelta

COLORS = {
    "bg_main": "#FBF8F3",
    "bg_card": "#FFFFFF",
    "bg_input": "#FFFDF9",
    "bg_result": "#FAF4EA",
    "border": "#E6DEC8",
    "accent": "#C87A3B",
    "accent_hover": "#B06528",
    "accent_light": "#F5E6D3",
    "text_primary": "#3D352E",
    "text_secondary": "#7A6E63",
    "text_time": "#A6632B",
    "done_bg": "#EEF4EC",
    "done_fg": "#3E6B48",
    "warn_bg": "#FDF0E6",
    "warn_fg": "#B84A14",
    "danger": "#C95D4B"
}

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_FILE = os.path.join(get_app_dir(), "flashes_pro_data.json")


class FlashNoteProApp:
    def __init__(self, root):
        self.root = root
        self.root.title("拾光闪念 Pro · 闭环与提醒版")
        self.root.geometry("760x880")
        self.root.minsize(640, 700)
        self.root.configure(bg=COLORS["bg_main"])

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.notes = self.load_notes()
        self.filter_mode = "all"
        self.sound_enabled = True
        self.active_reminder_ids = set()

        self.new_reminder_enabled = tk.BooleanVar(value=False)
        self.new_reminder_dt_var = tk.StringVar(
            value=(datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        )

        self.setup_styles()
        self.build_ui()
        self.render_notes()
        self.tick_loop()
        self.input_text.focus_set()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Warm.Vertical.TScrollbar",
            gripcount=0,
            background="#DFD5C5",
            darkcolor="#DFD5C5",
            lightcolor="#DFD5C5",
            troughcolor=COLORS["bg_main"],
            bordercolor=COLORS["bg_main"],
            arrowcolor=COLORS["text_secondary"]
        )

    def load_notes(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                return []
        return []

    def save_notes(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def play_gentle_chime(self):
        if not self.sound_enabled:
            return
        try:
            winsound.Beep(784, 160)
            winsound.Beep(1046, 220)
        except Exception:
            try:
                self.root.bell()
            except Exception:
                pass

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.sound_btn.config(
            text="🔔 提示音：开" if self.sound_enabled else "🔕 提示音：关"
        )

    def set_preset_reminder(self, minutes=None, set_today_18=False, set_tomorrow_9=False):
        now = datetime.now()
        if minutes is not None:
            target = now + timedelta(minutes=minutes)
        elif set_today_18:
            target = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
        elif set_tomorrow_9:
            target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        else:
            target = now + timedelta(hours=1)

        self.new_reminder_enabled.set(True)
        self.new_reminder_dt_var.set(target.strftime("%Y-%m-%d %H:%M"))

    def build_ui(self):
        header = tk.Frame(self.root, bg=COLORS["bg_main"], padx=26, pady=14)
        header.pack(fill=tk.X)

        left_h = tk.Frame(header, bg=COLORS["bg_main"])
        left_h.pack(side=tk.LEFT)

        tk.Label(
            left_h,
            text="✦ 拾光闪念 Pro",
            font=("Microsoft YaHei UI", 16, "bold"),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_main"]
        ).pack(side=tk.LEFT)

        tk.Label(
            left_h,
            text="  随手记录 · 闭环跟进 · 按需提醒",
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(side=tk.LEFT, pady=(5, 0))

        right_h = tk.Frame(header, bg=COLORS["bg_main"])
        right_h.pack(side=tk.RIGHT)

        self.sound_btn = tk.Button(
            right_h,
            text="🔔 提示音：开",
            font=("Microsoft YaHei UI", 8),
            fg=COLORS["text_primary"],
            bg=COLORS["accent_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=3,
            command=self.toggle_sound
        )
        self.sound_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clock_label = tk.Label(
            right_h,
            text="",
            font=("Consolas", 10, "bold"),
            fg=COLORS["text_time"],
            bg=COLORS["accent_light"],
            padx=10,
            pady=4
        )
        self.clock_label.pack(side=tk.LEFT)

        self.alert_banner = tk.Frame(
            self.root,
            bg=COLORS["warn_bg"],
            highlightthickness=1,
            highlightbackground="#E6B89C",
            padx=14,
            pady=8
        )
        self.alert_label = tk.Label(
            self.alert_banner,
            text="",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=COLORS["warn_fg"],
            bg=COLORS["warn_bg"],
            anchor="w",
            justify=tk.LEFT
        )
        self.alert_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            self.alert_banner,
            text="全部延后 15 分钟",
            font=("Microsoft YaHei UI", 8, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=3,
            command=self.snooze_all_due
        ).pack(side=tk.RIGHT)

        input_wrap = tk.Frame(self.root, bg=COLORS["border"], padx=1, pady=1)
        input_wrap.pack(fill=tk.X, padx=26, pady=(0, 10))

        input_card = tk.Frame(input_wrap, bg=COLORS["bg_input"], padx=16, pady=12)
        input_card.pack(fill=tk.BOTH)

        self.input_text = tk.Text(
            input_card,
            height=3,
            font=("Microsoft YaHei UI", 11),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_input"],
            insertbackground=COLORS["accent"],
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.input_text.pack(fill=tk.X)
        self.input_text.bind("<Control-Return>", lambda e: self.add_note())

        row1 = tk.Frame(input_card, bg=COLORS["bg_input"], pady=6)
        row1.pack(fill=tk.X)

        tk.Label(
            row1,
            text="标签：",
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_input"]
        ).pack(side=tk.LEFT)

        self.tag_entry = tk.Entry(
            row1,
            width=12,
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_main"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"]
        )
        self.tag_entry.insert(0, "灵感")
        self.tag_entry.pack(side=tk.LEFT, padx=(4, 12), ipady=2)

        tk.Label(
            row1,
            text="快捷键 Ctrl+Enter 保存",
            font=("Microsoft YaHei UI", 8),
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_input"]
        ).pack(side=tk.LEFT)

        tk.Button(
            row1,
            text="记下一笔",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            activebackground=COLORS["accent_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=4,
            command=self.add_note
        ).pack(side=tk.RIGHT)

        row2 = tk.Frame(input_card, bg=COLORS["bg_input"], pady=4)
        row2.pack(fill=tk.X)

        tk.Checkbutton(
            row2,
            text="设置到期提醒（若未处理则提醒）",
            variable=self.new_reminder_enabled,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_input"],
            activebackground=COLORS["bg_input"],
            selectcolor=COLORS["accent_light"],
            cursor="hand2"
        ).pack(side=tk.LEFT)

        self.reminder_dt_entry = tk.Entry(
            row2,
            textvariable=self.new_reminder_dt_var,
            width=17,
            font=("Consolas", 9),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_main"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"]
        )
        self.reminder_dt_entry.pack(side=tk.LEFT, padx=(8, 8), ipady=2)

        for label, cmd in [
            ("30分后", lambda: self.set_preset_reminder(minutes=30)),
            ("2小时后", lambda: self.set_preset_reminder(minutes=120)),
            ("今晚18点", lambda: self.set_preset_reminder(set_today_18=True)),
            ("明早9点", lambda: self.set_preset_reminder(set_tomorrow_9=True)),
        ]:
            tk.Button(
                row2,
                text=label,
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["accent"],
                bg=COLORS["accent_light"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=6,
                pady=1,
                command=cmd
            ).pack(side=tk.LEFT, padx=2)

        filter_bar = tk.Frame(self.root, bg=COLORS["bg_main"], padx=26, pady=6)
        filter_bar.pack(fill=tk.X)

        self.tab_buttons = {}
        tabs = [
            ("all", "全部"),
            ("pending", "待处理"),
            ("done", "已处理"),
            ("reminded", "⏰ 设提醒"),
        ]
        for key, text in tabs:
            btn = tk.Button(
                filter_bar,
                text=text,
                font=("Microsoft YaHei UI", 8, "bold"),
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=3,
                command=lambda k=key: self.switch_filter(k)
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self.tab_buttons[key] = btn

        self.refresh_tab_styles()

        tk.Button(
            filter_bar,
            text="导出 MD",
            font=("Microsoft YaHei UI", 8),
            fg=COLORS["accent"],
            bg=COLORS["accent_light"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=9,
            pady=3,
            command=self.export_markdown
        ).pack(side=tk.RIGHT, padx=(8, 0))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.render_notes())

        tk.Entry(
            filter_bar,
            textvariable=self.search_var,
            width=18,
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_card"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"]
        ).pack(side=tk.RIGHT, ipady=2)

        tk.Label(
            filter_bar,
            text="搜索：",
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(side=tk.RIGHT)

        list_wrap = tk.Frame(self.root, bg=COLORS["bg_main"], padx=26, pady=6)
        list_wrap.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(list_wrap, bg=COLORS["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            list_wrap,
            orient="vertical",
            command=self.canvas.yview,
            style="Warm.Vertical.TScrollbar"
        )
        self.list_frame = tk.Frame(self.canvas, bg=COLORS["bg_main"])

        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_win = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_win, width=e.width)
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

    def refresh_tab_styles(self):
        for key, btn in self.tab_buttons.items():
            if key == self.filter_mode:
                btn.config(fg="#FFFFFF", bg=COLORS["accent"])
            else:
                btn.config(fg=COLORS["text_secondary"], bg=COLORS["accent_light"])

    def switch_filter(self, mode):
        self.filter_mode = mode
        self.refresh_tab_styles()
        self.render_notes()

    def parse_reminder_str(self, raw):
        if not raw:
            return None
        raw = raw.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def add_note(self):
        content = self.input_text.get("1.0", tk.END).strip()
        if not content:
            return

        reminder_iso = None
        if self.new_reminder_enabled.get():
            parsed_dt = self.parse_reminder_str(self.new_reminder_dt_var.get())
            if not parsed_dt:
                messagebox.showwarning(
                    "提醒时间格式有误",
                    "请输入有效时间，例如：2026-11-20 18:30"
                )
                return
            reminder_iso = parsed_dt.strftime("%Y-%m-%d %H:%M")

        now = datetime.now()
        weekday = WEEKDAYS[now.weekday()]
        tag = self.tag_entry.get().strip() or "随记"

        item = {
            "id": int(now.timestamp() * 1000),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": weekday,
            "tag": tag,
            "content": content,
            "status": "pending",
            "result_note": "",
            "handled_at": "",
            "reminder_at": reminder_iso,
            "reminded_fired": False
        }

        self.notes.insert(0, item)
        self.save_notes()
        self.input_text.delete("1.0", tk.END)
        self.new_reminder_enabled.set(False)
        self.render_notes()
        self.canvas.yview_moveto(0)
        return "break"

    def toggle_done(self, note_id, result_text=None):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for n in self.notes:
            if n["id"] == note_id:
                if result_text is not None:
                    n["result_note"] = result_text.strip()
                if n.get("status") == "done":
                    n["status"] = "pending"
                    n["handled_at"] = ""
                else:
                    n["status"] = "done"
                    n["handled_at"] = now_str
                self.active_reminder_ids.discard(note_id)
                break
        self.save_notes()
        self.render_notes()
        self.check_reminders(play_sound=False)

    def save_result_only(self, note_id, result_text):
        for n in self.notes:
            if n["id"] == note_id:
                n["result_note"] = result_text.strip()
                break
        self.save_notes()
        messagebox.showinfo("已保存", "处理结果已更新。")

    def update_reminder_dialog(self, note):
        win = tk.Toplevel(self.root)
        win.title("设置闪念提醒")
        win.geometry("360x210")
        win.configure(bg=COLORS["bg_main"])
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text="若未标记“已处理”，将在约定时间提醒你：",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", padx=18, pady=12)

        default_str = note.get("reminder_at") or (
            datetime.now() + timedelta(minutes=30)
        ).strftime("%Y-%m-%d %H:%M")
        dt_var = tk.StringVar(value=default_str)

        entry = tk.Entry(
            win,
            textvariable=dt_var,
            font=("Consolas", 10),
            fg=COLORS["text_primary"],
            bg=COLORS["bg_card"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=COLORS["border"]
        )
        entry.pack(fill=tk.X, padx=18, ipady=4)

        preset_row = tk.Frame(win, bg=COLORS["bg_main"], pady=10)
        preset_row.pack(fill=tk.X, padx=18)

        def apply_offset(mins):
            dt_var.set((datetime.now() + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M"))

        for lbl, m in [("30分钟后", 30), ("1小时后", 60), ("3小时后", 180)]:
            tk.Button(
                preset_row,
                text=lbl,
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["accent"],
                bg=COLORS["accent_light"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda mins=m: apply_offset(mins)
            ).pack(side=tk.LEFT, padx=(0, 6))

        btn_row = tk.Frame(win, bg=COLORS["bg_main"], pady=8)
        btn_row.pack(fill=tk.X, padx=18)

        def on_save():
            parsed = self.parse_reminder_str(dt_var.get())
            if not parsed:
                messagebox.showwarning("格式错误", "请使用 YYYY-MM-DD HH:MM 格式。", parent=win)
                return
            note["reminder_at"] = parsed.strftime("%Y-%m-%d %H:%M")
            note["reminded_fired"] = False
            self.active_reminder_ids.discard(note["id"])
            self.save_notes()
            self.render_notes()
            win.destroy()

        def on_clear():
            note["reminder_at"] = None
            note["reminded_fired"] = False
            self.active_reminder_ids.discard(note["id"])
            self.save_notes()
            self.render_notes()
            win.destroy()

        tk.Button(
            btn_row,
            text="取消提醒",
            font=("Microsoft YaHei UI", 9),
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_card"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=4,
            command=on_clear
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_row,
            text="确认保存",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg="#FFFFFF",
            bg=COLORS["accent"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=4,
            command=on_save
        ).pack(side=tk.RIGHT)

    def snooze_all_due(self):
        new_dt = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        for n in self.notes:
            if n["id"] in self.active_reminder_ids:
                n["reminder_at"] = new_dt
                n["reminded_fired"] = False
        self.active_reminder_ids.clear()
        self.save_notes()
        self.alert_banner.pack_forget()
        self.render_notes()

    def delete_note(self, note_id):
        self.active_reminder_ids.discard(note_id)
        self.notes = [n for n in self.notes if n["id"] != note_id]
        self.save_notes()
        self.render_notes()
        self.check_reminders(play_sound=False)

    def copy_note(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def check_reminders(self, play_sound=True):
        now = datetime.now()
        newly_triggered = False

        for n in self.notes:
            if n.get("status") == "done":
                self.active_reminder_ids.discard(n["id"])
                continue
            rem_str = n.get("reminder_at")
            if not rem_str:
                continue
            rem_dt = self.parse_reminder_str(rem_str)
            if rem_dt and now >= rem_dt:
                if n["id"] not in self.active_reminder_ids:
                    self.active_reminder_ids.add(n["id"])
                    if not n.get("reminded_fired"):
                        n["reminded_fired"] = True
                        newly_triggered = True

        if newly_triggered:
            self.save_notes()
            if play_sound:
                self.play_gentle_chime()
            self.render_notes()

        due_notes = [n for n in self.notes if n["id"] in self.active_reminder_ids and n.get("status") != "done"]
        if due_notes:
            titles = "；".join(f"“{n['content'][:18]}”" for n in due_notes[:3])
            extra = f" 等 {len(due_notes)} 条" if len(due_notes) > 3 else ""
            self.alert_label.config(
                text=f"⏰ 提醒到期（尚未处理）：{titles}{extra} —— 请及时处理并填写结果"
            )
            if not self.alert_banner.winfo_ismapped():
                self.alert_banner.pack(fill=tk.X, padx=26, pady=6, before=self.root.winfo_children()[2])
        else:
            if self.alert_banner.winfo_ismapped():
                self.alert_banner.pack_forget()

    def tick_loop(self):
        now = datetime.now()
        weekday = WEEKDAYS[now.weekday()]
        self.clock_label.config(text=now.strftime(f"%Y-%m-%d  %H:%M:%S  {weekday}"))
        self.check_reminders(play_sound=True)
        self.root.after(1000, self.tick_loop)

    def render_notes(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        kw = self.search_var.get().strip().lower()
        filtered = []
        for n in self.notes:
            mode = self.filter_mode
            is_done = n.get("status") == "done"
            has_rem = bool(n.get("reminder_at"))
            if mode == "pending" and is_done:
                continue
            if mode == "done" and not is_done:
                continue
            if mode == "reminded" and not has_rem:
                continue

            hay = f"{n.get('content', '')} {n.get('tag', '')} {n.get('result_note', '')}".lower()
            if kw and kw not in hay:
                continue
            filtered.append(n)

        if not filtered:
            tk.Label(
                self.list_frame,
                text="当前筛选下暂无闪念记录，随时在上方写下一条吧 ~",
                font=("Microsoft YaHei UI", 10),
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_main"],
                pady=36
            ).pack()
            return

        last_date = None
        for n in filtered:
            if n["date"] != last_date:
                last_date = n["date"]
                tk.Label(
                    self.list_frame,
                    text=f"📅 {n['date']} ({n.get('weekday', '')})",
                    font=("Microsoft YaHei UI", 9, "bold"),
                    fg=COLORS["text_secondary"],
                    bg=COLORS["bg_main"],
                    anchor="w"
                ).pack(fill=tk.X, pady=6)

            is_done = n.get("status") == "done"
            is_overdue = (n["id"] in self.active_reminder_ids) and not is_done

            border_color = "#E08E55" if is_overdue else COLORS["border"]
            outer = tk.Frame(self.list_frame, bg=border_color, padx=1, pady=1)
            outer.pack(fill=tk.X, pady=5)

            card = tk.Frame(outer, bg=COLORS["bg_card"], padx=14, pady=10)
            card.pack(fill=tk.X)

            top = tk.Frame(card, bg=COLORS["bg_card"])
            top.pack(fill=tk.X, pady=4)

            status_btn = tk.Button(
                top,
                text="✓ 已处理" if is_done else "○ 待处理",
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=COLORS["done_fg"] if is_done else COLORS["text_secondary"],
                bg=COLORS["done_bg"] if is_done else COLORS["bg_main"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda nid=n["id"]: self.toggle_done(nid)
            )
            status_btn.pack(side=tk.LEFT)

            tk.Label(
                top,
                text=f"🕒 {n['time']}",
                font=("Consolas", 9, "bold"),
                fg=COLORS["text_time"],
                bg=COLORS["bg_card"]
            ).pack(side=tk.LEFT, padx=(10, 8))

            tk.Label(
                top,
                text=f"#{n.get('tag', '随记')}",
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["accent"],
                bg=COLORS["accent_light"],
                padx=6,
                pady=1
            ).pack(side=tk.LEFT)

            if n.get("reminder_at"):
                rem_fg = COLORS["warn_fg"] if is_overdue else COLORS["accent"]
                rem_bg = COLORS["warn_bg"] if is_overdue else COLORS["bg_main"]
                rem_txt = f"⏰ 到期未处理 ({n['reminder_at']})" if is_overdue else f"⏰ 提醒: {n['reminder_at']}"
                tk.Label(
                    top,
                    text=rem_txt,
                    font=("Microsoft YaHei UI", 8, "bold" if is_overdue else "normal"),
                    fg=rem_fg,
                    bg=rem_bg,
                    padx=6,
                    pady=1
                ).pack(side=tk.LEFT, padx=(8, 0))

            tk.Button(
                top,
                text="删除",
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_card"],
                activeforeground=COLORS["danger"],
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda nid=n["id"]: self.delete_note(nid)
            ).pack(side=tk.RIGHT)

            tk.Button(
                top,
                text="复制",
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_card"],
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda txt=n["content"]: self.copy_note(txt)
            ).pack(side=tk.RIGHT, padx=(0, 6))

            tk.Button(
                top,
                text="设提醒",
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["accent"],
                bg=COLORS["bg_card"],
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda note=n: self.update_reminder_dialog(note)
            ).pack(side=tk.RIGHT, padx=(0, 6))

            tk.Label(
                card,
                text=n["content"],
                font=("Microsoft YaHei UI", 10),
                fg=COLORS["text_primary"],
                bg=COLORS["bg_card"],
                justify=tk.LEFT,
                anchor="w",
                wraplength=640
            ).pack(fill=tk.X, pady=6)

            res_box = tk.Frame(
                card,
                bg=COLORS["bg_result"],
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                padx=10,
                pady=8
            )
            res_box.pack(fill=tk.X)

            res_header = tk.Frame(res_box, bg=COLORS["bg_result"])
            res_header.pack(fill=tk.X, pady=2)

            tk.Label(
                res_header,
                text="处理结果 / 应对记录",
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=COLORS["text_secondary"],
                bg=COLORS["bg_result"]
            ).pack(side=tk.LEFT)

            if n.get("handled_at"):
                tk.Label(
                    res_header,
                    text=f"完成于 {n['handled_at']}",
                    font=("Consolas", 8),
                    fg=COLORS["done_fg"],
                    bg=COLORS["bg_result"]
                ).pack(side=tk.LEFT, padx=(10, 0))

            res_entry = tk.Entry(
                res_box,
                font=("Microsoft YaHei UI", 9),
                fg=COLORS["text_primary"],
                bg=COLORS["bg_card"],
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                highlightcolor=COLORS["accent"]
            )
            res_entry.insert(0, n.get("result_note", ""))
            res_entry.pack(fill=tk.X, ipady=3, pady=4)

            res_actions = tk.Frame(res_box, bg=COLORS["bg_result"])
            res_actions.pack(fill=tk.X)

            tk.Button(
                res_actions,
                text="仅保存结果",
                font=("Microsoft YaHei UI", 8),
                fg=COLORS["text_primary"],
                bg=COLORS["bg_card"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda nid=n["id"], e=res_entry: self.save_result_only(nid, e.get())
            ).pack(side=tk.RIGHT)

            tk.Button(
                res_actions,
                text="重新打开处理" if is_done else "保存并标记已处理",
                font=("Microsoft YaHei UI", 8, "bold"),
                fg="#FFFFFF",
                bg=COLORS["text_secondary"] if is_done else COLORS["accent"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=2,
                command=lambda nid=n["id"], e=res_entry: self.toggle_done(nid, e.get())
            ).pack(side=tk.RIGHT, padx=(0, 6))

    def export_markdown(self):
        if not self.notes:
            messagebox.showinfo("提示", "当前没有可导出的闪念记录。")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown 文件", "*.md"), ("文本文件", "*.txt")],
            initialfile=f"拾光闪念Pro归档_{datetime.now().strftime('%Y%m%d')}.md"
        )
        if not path:
            return

        lines = ["# 拾光闪念 Pro 归档\n"]
        cur_date = None
        for n in self.notes:
            if n["date"] != cur_date:
                cur_date = n["date"]
                lines.append(f"\n## {cur_date} ({n.get('weekday', '')})\n")
            mark = "[x]" if n.get("status") == "done" else "[ ]"
            rem = f" | 提醒: `{n['reminder_at']}`" if n.get("reminder_at") else ""
            lines.append(f"- {mark} **{n['time']}** `#{n.get('tag', '随记')}`{rem}：{n['content']}")
            if n.get("result_note"):
                lines.append(f"  - 处理结果：{n['result_note']}")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        messagebox.showinfo("导出成功", f"已导出 {len(self.notes)} 条记录！")


if __name__ == "__main__":
    root = tk.Tk()
    app = FlashNoteProApp(root)
    root.mainloop()