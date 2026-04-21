from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calculator import CalculatorError, format_decimal, safe_evaluate  # noqa: E402


class CalculatorLogicTest(unittest.TestCase):
    def test_safe_evaluate_supports_operator_precedence(self) -> None:
        self.assertEqual(safe_evaluate("1+2*3"), Decimal("7"))

    def test_safe_evaluate_supports_parentheses_and_unary_minus(self) -> None:
        self.assertEqual(safe_evaluate("-(2+3)"), Decimal("-5"))

    def test_safe_evaluate_supports_decimal_division(self) -> None:
        self.assertEqual(safe_evaluate("7.5/2"), Decimal("3.75"))

    def test_safe_evaluate_rejects_division_by_zero(self) -> None:
        with self.assertRaises(CalculatorError):
            safe_evaluate("1/0")

    def test_safe_evaluate_rejects_unsupported_code(self) -> None:
        with self.assertRaises(CalculatorError):
            safe_evaluate("__import__('os').system('echo hi')")

    def test_format_decimal_trims_trailing_zeros(self) -> None:
        self.assertEqual(format_decimal(Decimal("2.5000")), "2.5")
        self.assertEqual(format_decimal(Decimal("3.0")), "3")


if __name__ == "__main__":
    unittest.main()
