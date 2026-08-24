"""Motorola_Intel_Calc_64 — CAN FD bit-field calculator (64 bytes / 512 bits).

Run with:  python Motorola_Intel_Calc_64.py
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


BYTE_COUNT = 64
BIT_COUNT = BYTE_COUNT * 8
APP_NAME = "Motorola_Intel_Calc_64"
APP_ICON = "Motorola_Intel_Calc_64.ico"
ACTIVE = "#e85d2a"
HEADER = "#4daac1"
ALT_ROW = "#f0f2df"


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

        self._make_ui()
        self._draw_values()
        self._center_window()
        self.deiconify()
        self._toggle_topmost()

    def _set_window_icon(self) -> None:
        """Use the bundled application icon in both source and frozen builds."""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        try:
            self.iconbitmap(str(base / APP_ICON))
        except tk.TclError:
            pass

    def _center_window(self) -> None:
        """Place the initial window in the centre of the active screen."""
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

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
        self.header_canvas.bind("<Configure>", self._draw_header)
        self.canvas.bind("<Configure>", self._draw_table)
        self.canvas.bind_all("<MouseWheel>", self._mousewheel)

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

        self.status = ttk.Label(outer, text="范围：0–511 bit；数值可输入十进制或 0x 十六进制。")
        self.status.grid(row=2, column=0, sticky="w", pady=(4, 0))

    def _entry(self, parent: ttk.LabelFrame, label: str | ttk.Label, variable: tk.StringVar,
               column: int, width: int = 9) -> None:
        if isinstance(label, str):
            label = ttk.Label(parent, text=label)
        label.grid(row=0, column=column, padx=(0, 6))
        entry = ttk.Entry(parent, textvariable=variable, width=width, justify="center")
        entry.grid(row=0, column=column + 1, padx=(0, 10))
        entry.bind("<Return>", self.apply_field)
        entry.bind("<FocusOut>", self.apply_field)

    def _draw_header(self, event: tk.Event | None = None) -> None:
        """Draw the fixed table header; it does not participate in scrolling."""
        width = self.header_canvas.winfo_width() if event is None else event.width
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

    def _draw_table(self, event: tk.Event | None = None) -> None:
        """Draw the grid as canvas items, rather than hundreds of widgets.

        This keeps wheel scrolling and resizing responsive even for 64 CAN FD bytes.
        """
        width = self.canvas.winfo_width() if event is None else event.width
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
        self.canvas.create_window((x0 + x1) / 2, (y0 + y1) / 2, window=label,
                                  width=x1 - x0 - 3, height=y1 - y0 - 3, tags="grid")
        label.bind("<Double-Button-1>", lambda _event, b=byte_index: self.copy_byte(b))
        return label

    def _mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    @staticmethod
    def _parse(text: str) -> int:
        return int(text.strip(), 0)

    def apply_field(self, _event: tk.Event | None = None) -> None:
        if not all((self.lsb.get().strip(), self.size.get().strip(), self.value.get().strip())):
            return
        try:
            lsb, size, value = self._parse(self.lsb.get()), self._parse(self.size.get()), self._parse(self.value.get())
            positions = self._positions(lsb, size)
            if value < 0 or value >= (1 << size):
                raise ValueError("Value does not fit in Size")
        except ValueError as exc:
            self.status.configure(text=f"输入无效：{exc}")
            return
        self.bytes = [0] * BYTE_COUNT
        # MSB formats take their start bit from the most-significant bit of Value.
        value_bits = range(size - 1, -1, -1) if self.mode.get().endswith("MSB") else range(size)
        for value_bit, target_bit in zip(value_bits, positions):
            if value & (1 << value_bit):
                self.bytes[target_bit // 8] |= 1 << (target_bit % 8)
        self.status.configure(text=f"已写入 {size} bit（{self.mode.get()}）。")
        self._draw_values()
        self._ensure_result_visible(lsb, positions)

    def _positions(self, lsb: int, size: int) -> list[int]:
        if not 0 <= lsb < BIT_COUNT or not 1 <= size <= BIT_COUNT:
            raise ValueError("Lsb 必须为 0–511，Size 必须为 1–512")
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
            raise ValueError("该字段越过 CAN FD 的 64 Byte 边界")
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
        self.status.configure(text=f"已切换 bit {bit}。")

    def copy_byte(self, byte: int) -> None:
        self.clipboard_clear()
        self.clipboard_append(f"0x{self.bytes[byte]:02X}")
        self.status.configure(text=f"Byte {byte} 已复制到剪贴板。")

    def _mode_changed(self, _event: tk.Event | None = None) -> None:
        self.title(f"{APP_NAME} - {self.mode.get()}")
        self.apply_field()

    def _toggle_topmost(self) -> None:
        self.attributes("-topmost", self.always_on_top.get())

    def clear(self) -> None:
        self.bytes = [0] * BYTE_COUNT
        self._draw_values()
        self.status.configure(text="已清除。")

    @staticmethod
    def help() -> None:
        messagebox.showinfo("Help", "单击 Bit 位可切换该位。\n双击 Byte 值可复制。\n支持 64 Byte CAN FD（bit 0–511）。")


if __name__ == "__main__":
    MotorolaIntelCalc64().mainloop()
