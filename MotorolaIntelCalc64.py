"""MotorolaIntelCalc64 — CAN FD bit-field calculator (64 bytes / 512 bits).

Run with:  python MotorolaIntelCalc64.py
"""

from __future__ import annotations

import sys
import tkinter as tk
from ctypes import POINTER, Structure, byref, c_long, c_ulong, c_void_p, windll, wintypes
from pathlib import Path
from tkinter import messagebox, ttk


BYTE_COUNT = 64
BIT_COUNT = BYTE_COUNT * 8
APP_NAME = "MotorolaIntelCalc64"
APP_ICON = "MotorolaIntelCalc64.ico"
ACTIVE = "#e85d2a"
HEADER = "#4daac1"
ALT_ROW = "#f0f2df"
RESIZE_CORNER = 16
WM_NCLBUTTONDOWN = 0x00A1
HTBOTTOMRIGHT = 17


class MotorolaIntelCalc64(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.withdraw()
        self.title(APP_NAME)
        self._set_window_icon()
        # Header + eight 28 px byte rows match the original tool's initial view.
        self.geometry("730x350")
        self.minsize(730, 350)
        self.bytes = [0] * BYTE_COUNT
        self.mode = tk.StringVar(value="Motorola LSB")
        self.always_on_top = tk.BooleanVar(value=True)
        self.lsb = tk.StringVar()
        self.size = tk.StringVar()
        self.value = tk.StringVar()
        self.bit_labels: dict[int, int] = {}
        self.byte_labels: list[tk.Label] = []
        self._header_width = 0
        self._table_width = 0
        self._grid_width = 0
        self._table_redraw_job: str | None = None
        self._value_windows: list[int] = []
        self._cursor_sync_job: str | None = None

        self._make_ui()
        self._draw_values()
        self.deiconify()
        self._toggle_topmost()
        self._center_window()

    def _set_window_icon(self) -> None:
        """Use the bundled application icon in both source and frozen builds."""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        try:
            self.iconbitmap(str(base / APP_ICON))
        except tk.TclError:
            pass

    def _center_window(self) -> None:
        """Place the mapped window in the centre of Tk's primary display."""
        self.update_idletasks()
        client_width, client_height = self.winfo_width(), self.winfo_height()
        outer_width, outer_height = client_width, client_height
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        if sys.platform == "win32":
            class Rect(Structure):
                _fields_ = [("left", c_long), ("top", c_long), ("right", c_long), ("bottom", c_long)]

            user32 = windll.user32
            user32.GetAncestor.argtypes = [c_void_p, c_ulong]
            user32.GetAncestor.restype = c_void_p
            user32.GetWindowRect.argtypes = [c_void_p, c_void_p]
            user32.GetWindowRect.restype = c_long
            # winfo_id() identifies Tk's client window.  Use its root ancestor
            # so measurements include the title bar and resize border.
            window = user32.GetAncestor(c_void_p(self.winfo_id()), 2) or c_void_p(self.winfo_id())
            window_rect = Rect()
            if user32.GetWindowRect(window, byref(window_rect)):
                outer_width = window_rect.right - window_rect.left
                outer_height = window_rect.bottom - window_rect.top
        x = max(0, (screen_width - outer_width) // 2)
        y = max(0, (screen_height - outer_height) // 2)
        self.geometry(f"{client_width}x{client_height}+{x}+{y}")

    def _make_ui(self) -> None:
        outer = ttk.Frame(self, padding=(5, 5, 5, 4))
        outer.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        table_host = ttk.Frame(outer)
        table_host.grid(row=0, column=0, sticky="nsew")
        table_host.columnconfigure(0, weight=1)
        table_host.rowconfigure(1, weight=1)
        self.header_canvas = tk.Canvas(table_host, height=28, highlightthickness=0, background="white")
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.canvas = tk.Canvas(table_host, highlightthickness=0, background="white")
        ybar = ttk.Scrollbar(table_host, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=ybar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        ybar.grid(row=1, column=1, sticky="ns")
        self.header_canvas.bind("<Configure>", self._header_resized)
        self.canvas.bind("<Configure>", self._table_resized)
        self.canvas.bind("<MouseWheel>", self._mousewheel)

        controls = tk.Frame(outer, bg="#f3f3f3", relief="groove", borderwidth=1, padx=10, pady=12)
        controls.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        ttk.Label(controls, text="Mode:").grid(row=0, column=0, padx=(0, 6))
        mode_holder = tk.Frame(controls, width=107, height=23)
        mode_holder.grid(row=0, column=1, padx=(0, 12))
        mode_holder.grid_propagate(False)
        self.mode_select = ttk.Combobox(mode_holder, textvariable=self.mode, state="readonly",
                                        values=("Motorola LSB", "Motorola MSB", "Intel LSB", "Intel MSB"))
        self.mode_select.place(x=0, y=0, width=107, height=23)
        self.mode_select.bind("<<ComboboxSelected>>", self._mode_changed)
        self.start_label = ttk.Label(controls, text="StartBit:")
        self._entry(controls, self.start_label, self.lsb, 2, width=8)
        self._entry(controls, "Size:", self.size, 4, width=8)
        self._entry(controls, "Value:", self.value, 6, width=12)
        ttk.Button(controls, text="Clear", command=self.clear).grid(row=0, column=8, padx=(0, 4))
        ttk.Checkbutton(controls, text="Top", variable=self.always_on_top,
                        command=self._toggle_topmost).grid(row=0, column=9, sticky="w")

        self.status = ttk.Label(outer, text="Range: 0-511 bit; value accepts decimal or 0x hexadecimal.")
        self.status.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # Windows only shows the resize arrow over its non-client border, which
        # lies in the invisible margin outside this window's visible frame.
        # This colour-matched corner patch extends the hotspot into the client
        # area and starts the same native resize as the window border.
        corner_background = ttk.Style(self).lookup("TFrame", "background") or self.cget("background")
        self.resize_corner = tk.Frame(self, width=RESIZE_CORNER, height=RESIZE_CORNER,
                                      background=corner_background, borderwidth=0,
                                      highlightthickness=0, cursor="size_nw_se")
        self.resize_corner.place(relx=1.0, rely=1.0, anchor="se",
                                 width=RESIZE_CORNER, height=RESIZE_CORNER)
        self.resize_corner.bind("<Button-1>", self._begin_corner_resize)
        self.bind("<Configure>", self._window_configured, add="+")

    def _window_configured(self, event: tk.Event) -> None:
        """Keep the corner cursor in step with maximize and restore."""
        if event.widget is not self:
            return
        if self._cursor_sync_job is None:
            self._cursor_sync_job = self.after_idle(self._sync_resize_cursor)

    def _sync_resize_cursor(self) -> None:
        self._cursor_sync_job = None
        cursor = "arrow" if self.state() == "zoomed" else "size_nw_se"
        if self.resize_corner.cget("cursor") != cursor:
            self.resize_corner.configure(cursor=cursor)

    def _begin_corner_resize(self, _event: tk.Event | None = None) -> str:
        """Hand a bottom-right press over to the native non-client resize loop.

        The message is posted, not sent: a synchronous WM_NCLBUTTONDOWN starts
        a nested modal loop inside a ctypes call that has released the GIL,
        where Tk callbacks would then run without a valid thread state.
        """
        if sys.platform != "win32" or self.state() == "zoomed":
            return "break"
        user32 = windll.user32
        user32.GetCursorPos.argtypes = [POINTER(wintypes.POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = [c_void_p, c_ulong, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL
        user32.ReleaseCapture.argtypes = []
        user32.ReleaseCapture.restype = wintypes.BOOL
        point = wintypes.POINT()
        if not user32.GetCursorPos(byref(point)):
            return "break"
        try:
            window = int(self.wm_frame(), 16)
        except (tk.TclError, ValueError):
            return "break"
        user32.ReleaseCapture()
        user32.PostMessageW(window, WM_NCLBUTTONDOWN, HTBOTTOMRIGHT,
                            (point.y << 16) | (point.x & 0xFFFF))
        return "break"

    def _entry(self, parent: ttk.LabelFrame, label: str | ttk.Label, variable: tk.StringVar,
               column: int, width: int = 9) -> None:
        if isinstance(label, str):
            label = ttk.Label(parent, text=label)
        label.grid(row=0, column=column, padx=(0, 6))
        entry = ttk.Entry(parent, textvariable=variable, width=width, justify="center")
        entry.grid(row=0, column=column + 1, padx=(0, 10))
        entry.bind("<Return>", self.apply_field)
        entry.bind("<FocusOut>", self.apply_field)

    def _header_resized(self, event: tk.Event) -> None:
        """Redraw the header only when its width changes."""
        if event.width == self._header_width:
            return
        self._header_width = event.width
        self._draw_header(event.width)

    def _draw_header(self, width: int | None = None) -> None:
        """Draw the fixed table header; it does not participate in scrolling."""
        width = self.header_canvas.winfo_width() if width is None else width
        if width <= 1:
            return
        table_width = width - 2
        row_height = 28
        column_width = table_width / 10
        self.header_canvas.delete("all")
        labels = ["Byte", "Bit7", "Bit6", "Bit5", "Bit4", "Bit3", "Bit2", "Bit1", "Bit0", "Value"]
        for col, title in enumerate(labels):
            x0, x1 = col * column_width, (col + 1) * column_width
            self.header_canvas.create_rectangle(x0, 0, x1, row_height, fill=HEADER, outline="")
            self.header_canvas.create_text((x0 + x1) / 2, row_height / 2, text=title, font=("宋体", 15, "bold"))
        self.header_canvas.create_rectangle(0.5, 0.5, table_width - 0.5, row_height - 0.5, outline="black", width=1)
        for column in range(1, 10):
            x = column * column_width
            self.header_canvas.create_line(x, 0, x, row_height, fill="black", width=1)
        self.header_canvas.create_line(0, row_height - 1, table_width, row_height - 1, fill="black", width=1)

    def _table_resized(self, event: tk.Event) -> None:
        """Stretch the drawn grid while resizing, then rebuild it when settled.

        Rebuilding the 64-row grid takes over 100 ms, which would freeze the
        drag and leave the canvas blank.  Scaling the existing items is cheap
        and keeps their content visible; the deferred rebuild removes the
        accumulated rounding afterwards.
        """
        if event.width <= 1 or event.width == self._table_width:
            return
        self._table_width = event.width
        table_width = event.width - 2
        if self._grid_width > 1 and table_width > 1:
            ratio = table_width / self._grid_width
            if abs(ratio - 1.0) > 1e-4:
                self.canvas.scale("grid", 0, 0, ratio, 1.0)
                cell_width = table_width / 10
                for item in self._value_windows:
                    self.canvas.itemconfigure(item, width=max(cell_width - 3, 1))
                self.canvas.configure(scrollregion=(0, 0, table_width, BYTE_COUNT * 28))
                self._grid_width = table_width
        if self._table_redraw_job is not None:
            self.after_cancel(self._table_redraw_job)
        delay = 0 if self._grid_width <= 1 else 120
        self._table_redraw_job = self.after(delay, self._draw_table)

    def _draw_table(self) -> None:
        """Draw the grid as canvas items, rather than hundreds of widgets.

        The full rebuild is deferred until a resize settles; during the drag
        `_table_resized` stretches the existing items instead.
        """
        self._table_redraw_job = None
        width = self.canvas.winfo_width()
        if width <= 1:  # Canvas has not been laid out yet.
            return
        table_width = width - 2  # Keep the final black outline inside the viewport.
        row_height = 28
        column_width = table_width / 10
        for label in self.byte_labels:
            label.destroy()
        self.canvas.delete("grid")
        self.bit_labels.clear()
        self.byte_labels.clear()
        self._value_windows.clear()
        for byte_index in range(BYTE_COUNT):
            y0, y1 = byte_index * row_height, (byte_index + 1) * row_height
            byte_background = ALT_ROW if byte_index % 2 else "white"
            self._canvas_cell(0, y0, y1, str(byte_index), byte_background, ("宋体", 15), None)
            for col, bit_in_byte in enumerate(range(7, -1, -1), start=1):
                bit = byte_index * 8 + bit_in_byte
                self.bit_labels[bit] = self._canvas_cell(col, y0, y1, f"{bit:03d}", "white",
                                                          ("宋体", 15, "bold"), lambda _event, b=bit: self.toggle_bit(b))
            self.byte_labels.append(self._value_cell(y0, y1, byte_index))
        table_height = BYTE_COUNT * row_height
        # A single outer frame avoids the dark dots caused when every row line
        # terminates on the right-hand border of the Value column.
        self.canvas.create_rectangle(0.5, 0.5, table_width - 0.5, table_height - 0.5,
                                     outline="black", width=1, tags="grid")
        for column in range(1, 10):
            x = column * column_width
            self.canvas.create_line(x, 0, x, table_height, fill="black", width=1, tags="grid")
        for row in range(1, BYTE_COUNT):
            y = row * row_height
            self.canvas.create_line(0.5, y, table_width - 0.5, y, fill="black", width=1, tags="grid")
        self.canvas.configure(scrollregion=(0, 0, table_width, table_height))
        self._grid_width = table_width
        self._draw_values()

    def _canvas_cell(self, column: int, y0: float, y1: float, text: str, background: str,
                     font: tuple[str, int, str] | tuple[str, int], callback, double: bool = False) -> int:
        width = self.canvas.winfo_width() - 2
        x0, x1 = column * width / 10, (column + 1) * width / 10
        rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=background, outline="", tags="grid")
        item = self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=text, font=font, tags="grid")
        if callback:
            sequence = "<Double-Button-1>" if double else "<Button-1>"
            self.canvas.tag_bind(rect, sequence, callback)
            self.canvas.tag_bind(item, sequence, callback)
        return item

    def _value_cell(self, y0: float, y1: float, byte_index: int) -> tk.Label:
        """Use a native label for Value text to avoid Canvas colored-text artifacts."""
        width = self.canvas.winfo_width() - 2
        x0, x1 = 9 * width / 10, width
        label = tk.Label(self.canvas, text="0x00", font=("宋体", 15, "bold italic"),
                         bg="white", fg="black", borderwidth=0, highlightthickness=0)
        item = self.canvas.create_window((x0 + x1) / 2, (y0 + y1) / 2, window=label,
                                         width=x1 - x0 - 3, height=y1 - y0 - 3, tags="grid")
        self._value_windows.append(item)
        label.bind("<Double-Button-1>", lambda _event, b=byte_index: self.copy_byte(b))
        return label

    def _mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    @staticmethod
    def _parse(text: str) -> int:
        """Parse decimal (including leading zeroes) or a 0x hexadecimal value."""
        value = text.strip()
        if value.lower().lstrip("+-").startswith("0x"):
            return int(value, 16)
        return int(value, 10)

    def apply_field(self, _event: tk.Event | None = None) -> None:
        if not all((self.lsb.get().strip(), self.size.get().strip(), self.value.get().strip())):
            return
        try:
            lsb, size, value = self._parse(self.lsb.get()), self._parse(self.size.get()), self._parse(self.value.get())
            positions = self._positions(lsb, size)
            if value < 0 or value >= (1 << size):
                raise ValueError("Value does not fit in Size")
        except ValueError as exc:
            self.status.configure(text=f"Invalid input: {exc}")
            return
        self.bytes = [0] * BYTE_COUNT
        # MSB formats take their start bit from the most-significant bit of Value.
        value_bits = range(size - 1, -1, -1) if self.mode.get().endswith("MSB") else range(size)
        for value_bit, target_bit in zip(value_bits, positions):
            if value & (1 << value_bit):
                self.bytes[target_bit // 8] |= 1 << (target_bit % 8)
        self.status.configure(text=f"Wrote {size} bit ({self.mode.get()}).")
        self._draw_values()
        self._ensure_result_visible(lsb, positions)

    def _positions(self, lsb: int, size: int) -> list[int]:
        if not 0 <= lsb < BIT_COUNT or not 1 <= size <= BIT_COUNT:
            raise ValueError("StartBit must be in 0-511, Size must be in 1-512")
        mode = self.mode.get()
        if mode == "Intel LSB":
            positions = list(range(lsb, lsb + size))
        elif mode == "Intel MSB":
            positions = list(range(lsb, lsb - size, -1))
        elif mode == "Motorola LSB":
            # Retains the original program's Motorola LSB convention: crossing a byte
            # boundary continues in the preceding byte at bit 0.
            positions = []
            byte, bit = divmod(lsb, 8)
            for _ in range(size):
                positions.append(byte * 8 + bit)
                bit += 1
                if bit == 8:
                    bit = 0
                    byte -= 1
        else:  # Motorola MSB: DBC sawtooth order (bit 0 -> next byte's bit 7).
            positions = []
            byte, bit = divmod(lsb, 8)
            for _ in range(size):
                positions.append(byte * 8 + bit)
                bit -= 1
                if bit < 0:
                    bit = 7
                    byte += 1
        if any(bit < 0 or bit >= BIT_COUNT for bit in positions):
            raise ValueError("Field crosses the 64-byte CAN FD boundary")
        return positions

    def _draw_values(self) -> None:
        for byte_index, byte_value in enumerate(self.bytes):
            if byte_index >= len(self.byte_labels):
                return
            self.byte_labels[byte_index].configure(text=f"0x{byte_value:02X}", fg=ACTIVE if byte_value else "black")
            for bit_in_byte in range(8):
                bit = byte_index * 8 + bit_in_byte
                self.canvas.itemconfigure(self.bit_labels[bit], fill=ACTIVE if byte_value & (1 << bit_in_byte) else "black")

    def _ensure_result_visible(self, start_bit: int, positions: list[int]) -> None:
        """Reveal a clipped field, aligning its start row with its bit-order direction."""
        self.update_idletasks()
        row_height = 28
        start_byte = start_bit // 8
        field_bytes = [bit // 8 for bit in positions]
        field_top = min(field_bytes) * row_height
        field_bottom = (max(field_bytes) + 1) * row_height
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        if field_top >= visible_top and field_bottom <= visible_bottom:
            return
        total_height = BYTE_COUNT * row_height
        start_top = start_byte * row_height
        start_bottom = start_top + row_height
        # Intel LSB and Motorola MSB expand toward later Byte rows; the two
        # opposite formats expand toward earlier rows.
        if self.mode.get() in ("Intel LSB", "Motorola MSB"):
            target_top = start_top
        else:
            target_top = start_bottom - self.canvas.winfo_height()
        target_top = max(0, min(target_top, total_height - self.canvas.winfo_height()))
        self.canvas.yview_moveto(min(target_top / total_height, 1.0))

    def toggle_bit(self, bit: int) -> None:
        byte, bit_in_byte = divmod(bit, 8)
        self.bytes[byte] ^= 1 << bit_in_byte
        self._draw_values()
        self.status.configure(text=f"Toggled bit {bit}.")

    def copy_byte(self, byte: int) -> None:
        self.clipboard_clear()
        self.clipboard_append(f"0x{self.bytes[byte]:02X}")
        self.status.configure(text=f"Byte {byte} copied to clipboard.")

    def _mode_changed(self, _event: tk.Event | None = None) -> None:
        self.title(f"{APP_NAME} - {self.mode.get()}")
        self.apply_field()

    def _toggle_topmost(self) -> None:
        self.attributes("-topmost", self.always_on_top.get())

    def clear(self) -> None:
        self.bytes = [0] * BYTE_COUNT
        self._draw_values()
        self.status.configure(text="Cleared.")

    @staticmethod
    def help() -> None:
        messagebox.showinfo("Help", "Click a bit cell to toggle it.\nDouble-click a byte value to copy it.\nSupports 64-byte CAN FD (bit 0-511).")


if __name__ == "__main__":
    MotorolaIntelCalc64().mainloop()
