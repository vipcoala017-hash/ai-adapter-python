from __future__ import annotations

import ast
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext
import tkinter as tk
from tkinter import messagebox

getcontext().prec = 28


class CalculatorError(ValueError):
    """Responsibility: Signal user-facing expression evaluation errors.

    Contract: Callers may catch this exception to render a friendly message
    instead of exposing a raw traceback.
    Side effects: None.
    Error behavior: Carries only a human-readable message.
    """


def safe_evaluate(expression: str) -> Decimal:
    """Responsibility: Evaluate a basic arithmetic expression safely.

    Contract: Accepts digits, decimal points, parentheses, unary +/- and the
    binary operators +, -, *, /. The expression must already use ASCII
    operators.
    Parameters: expression is a non-empty calculator expression string.
    Returns: The evaluated Decimal result.
    Side effects: None.
    Error behavior: Raises CalculatorError for invalid syntax, unsupported
    nodes, or division by zero.
    """

    text = expression.strip()
    if not text:
        raise CalculatorError("表达式不能为空")
    try:
        tree = ast.parse(text, mode="eval")
        return _eval_node(tree.body)
    except (SyntaxError, ValueError, InvalidOperation, DivisionByZero) as exc:
        raise CalculatorError("表达式无效") from exc


def format_decimal(value: Decimal) -> str:
    """Responsibility: Render Decimal values into a compact display string.

    Contract: Preserves the numeric value while trimming trailing zeros and the
    decimal point when it is not needed.
    Parameters: value is a finite Decimal result.
    Returns: A display-friendly string.
    Side effects: None.
    Error behavior: Never raises for normal finite values.
    """

    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text


def _eval_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _eval_node(node.operand)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise CalculatorError("不能除以 0")
            return left / right
    raise CalculatorError("表达式包含不支持的内容")


class CalculatorApp:
    """Layer: ui

    Responsibility: Provide the calculator window, layout, and input flow.
    Contract: The app owns the Tk root, updates the display, and never exposes
    direct AST or Decimal details to the user.
    Side effects: Creates and runs a Tkinter window, binds keyboard shortcuts,
    and mutates the display state during interaction.
    Error behavior: Shows a friendly message box for evaluation failures and
    keeps the UI responsive.
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("计算器")
        self.root.resizable(False, False)
        self.root.configure(bg="#e8f1ff")

        self.expression = tk.StringVar(value="")
        self._error_state = False
        self._build_styles()
        self._build_layout()
        self._bind_keys()

    def run(self) -> None:
        """Responsibility: Enter the Tk event loop.

        Contract: Call after initialization; this method blocks until the
        window closes.
        Side effects: Starts the GUI event loop.
        Error behavior: Lets unexpected Tk errors surface to the caller.
        """

        self.root.mainloop()

    def _build_styles(self) -> None:
        self.display_bg = "#f7fbff"
        self.button_bg = "#dcecff"
        self.button_active_bg = "#b8d8ff"
        self.accent_bg = "#2b6cb0"
        self.accent_active_bg = "#245a93"
        self.text_fg = "#17324d"
        self.accent_fg = "#ffffff"

    def _build_layout(self) -> None:
        container = tk.Frame(self.root, bg="#e8f1ff", padx=14, pady=14)
        container.grid(row=0, column=0)

        display = tk.Entry(
            container,
            textvariable=self.expression,
            font=("Arial", 22),
            justify="right",
            bd=0,
            relief="flat",
            bg=self.display_bg,
            fg=self.text_fg,
            insertbackground=self.text_fg,
        )
        display.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 12), ipady=10)
        display.focus_set()

        buttons = [
            ("C", self.clear, self.button_bg, self.text_fg),
            ("⌫", self.backspace, self.button_bg, self.text_fg),
            ("÷", lambda: self.append_operator("/"), self.button_bg, self.text_fg),
            ("×", lambda: self.append_operator("*"), self.button_bg, self.text_fg),
            ("7", lambda: self.append_text("7"), self.button_bg, self.text_fg),
            ("8", lambda: self.append_text("8"), self.button_bg, self.text_fg),
            ("9", lambda: self.append_text("9"), self.button_bg, self.text_fg),
            ("-", lambda: self.append_operator("-"), self.button_bg, self.text_fg),
            ("4", lambda: self.append_text("4"), self.button_bg, self.text_fg),
            ("5", lambda: self.append_text("5"), self.button_bg, self.text_fg),
            ("6", lambda: self.append_text("6"), self.button_bg, self.text_fg),
            ("+", lambda: self.append_operator("+"), self.button_bg, self.text_fg),
            ("1", lambda: self.append_text("1"), self.button_bg, self.text_fg),
            ("2", lambda: self.append_text("2"), self.button_bg, self.text_fg),
            ("3", lambda: self.append_text("3"), self.button_bg, self.text_fg),
            ("=", self.calculate, self.accent_bg, self.accent_fg),
            ("0", lambda: self.append_text("0"), self.button_bg, self.text_fg),
            (".", lambda: self.append_text("."), self.button_bg, self.text_fg),
        ]
        layout = [
            buttons[0:4],
            buttons[4:8],
            buttons[8:12],
            buttons[12:16],
            [buttons[16], buttons[17], None, None],
        ]

        for row_index, row in enumerate(layout, start=1):
            for column_index, item in enumerate(row):
                if item is None:
                    spacer = tk.Frame(container, bg="#e8f1ff", width=1, height=1)
                    spacer.grid(row=row_index, column=column_index, padx=6, pady=6, sticky="nsew")
                    continue
                label, callback, background, foreground = item
                button = tk.Button(
                    container,
                    text=label,
                    command=callback,
                    font=("Arial", 16, "bold"),
                    bd=0,
                    relief="flat",
                    bg=background,
                    fg=foreground,
                    activebackground=self.button_active_bg if background == self.button_bg else self.accent_active_bg,
                    activeforeground=foreground,
                    padx=14,
                    pady=10,
                )
                button.grid(row=row_index, column=column_index, padx=6, pady=6, sticky="nsew")

        for index in range(4):
            container.columnconfigure(index, weight=1)

    def _bind_keys(self) -> None:
        self.root.bind("<Return>", lambda _event: self.calculate())
        self.root.bind("<KP_Enter>", lambda _event: self.calculate())
        self.root.bind("<BackSpace>", lambda _event: self.backspace())
        self.root.bind("<Escape>", lambda _event: self.clear())
        self.root.bind("<Key>", self._handle_key)

    def _handle_key(self, event: tk.Event) -> str | None:
        char = event.char
        if char.isdigit() or char == ".":
            self.append_text(char)
            return "break"
        if char in "+-*/":
            self.append_operator(char)
            return "break"
        return None

    def append_text(self, text: str) -> None:
        if self._error_state:
            self.expression.set("")
            self._error_state = False
        self.expression.set(self.expression.get() + text)

    def append_operator(self, operator: str) -> None:
        current = self.expression.get()
        if self._error_state:
            self._error_state = False
            current = ""
        if not current and operator != "-":
            return
        if current and current[-1] in "+-*/":
            current = current[:-1]
        self.expression.set(current + operator)

    def clear(self) -> None:
        self.expression.set("")
        self._error_state = False

    def backspace(self) -> None:
        current = self.expression.get()
        if self._error_state:
            self.clear()
            return
        self.expression.set(current[:-1])

    def calculate(self) -> None:
        current = self.expression.get().strip()
        if not current:
            return
        try:
            result = safe_evaluate(current)
        except CalculatorError as exc:
            self._error_state = True
            messagebox.showerror("计算错误", str(exc))
            self.expression.set("错误")
            return
        self.expression.set(format_decimal(result))
        self._error_state = False


def main() -> int:
    """Responsibility: Launch the calculator application.

    Contract: Can be used as the script entry point or imported and called from
    a launcher.
    Side effects: Opens the calculator window and blocks until it closes.
    Error behavior: Propagates unexpected startup failures to the caller.
    """

    app = CalculatorApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
