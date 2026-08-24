# Motorola Intel Calc 64

一个用于 CAN FD 报文字段的 64 Byte（512 bit）位计算器，支持 Intel 和 Motorola 两种字节序及 LSB/MSB 起始位约定。

## 运行

需要 Windows、Python（含标准库 Tkinter）。

```powershell
python Motorola_Intel_Calc_64.py
```

## 使用

1. 选择 `Mode`。
2. 输入 `StartBit`（0–511）、`Size`（1–512）和 `Value`。
3. 按 Enter 或离开输入框，程序会计算并点亮对应位。

`Value` 可输入十进制（允许前导零，如 `008`）或 `0x` 前缀的十六进制（如 `0x2A`）。值必须能容纳于指定的字段长度。

- 单击 Bit 单元格：切换该位。
- 双击 Value 单元格：复制该 Byte 的十六进制值。
- `Clear`：清除全部 64 Byte。
- `Top`：使窗口保持在最前。

## 打包

安装 PyInstaller 后，在项目根目录运行：

```powershell
.\build.bat
```

生成的单文件程序位于 `release\Motorola_Intel_Calc_64.exe`。构建过程的临时文件位于 `build\`。

## 位序说明

Motorola MSB 使用 DBC sawtooth 规则：字节内从 bit 7 向 bit 0 行进，越过 bit 0 后进入下一 Byte 的 bit 7。Motorola LSB 使用原工具的相反约定。越过 64 Byte 报文边界的字段会被拒绝。
