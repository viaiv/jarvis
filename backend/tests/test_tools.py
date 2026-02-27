import pytest

from jarvis.tools import calculator, current_time, evaluate_expression


class TestEvaluateExpression:
    def test_addition(self):
        assert evaluate_expression("2 + 3") == 5.0

    def test_subtraction(self):
        assert evaluate_expression("10 - 4") == 6.0

    def test_multiplication(self):
        assert evaluate_expression("6 * 7") == 42.0

    def test_division(self):
        assert evaluate_expression("15 / 4") == 3.75

    def test_modulo(self):
        assert evaluate_expression("10 % 3") == 1.0

    def test_power(self):
        assert evaluate_expression("2 ** 10") == 1024.0

    def test_parentheses(self):
        assert evaluate_expression("(2 + 3) * 4") == 20.0

    def test_nested_parentheses(self):
        assert evaluate_expression("((1 + 2) * (3 + 4))") == 21.0

    def test_unary_negative(self):
        assert evaluate_expression("-5 + 3") == -2.0

    def test_unary_positive(self):
        assert evaluate_expression("+5") == 5.0

    def test_float_numbers(self):
        assert evaluate_expression("1.5 + 2.5") == 4.0

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            evaluate_expression("1 / 0")

    def test_rejects_boolean(self):
        with pytest.raises(ValueError, match="Somente numeros"):
            evaluate_expression("True")

    def test_rejects_string(self):
        with pytest.raises((ValueError, SyntaxError)):
            evaluate_expression("'hello'")

    def test_rejects_function_call(self):
        with pytest.raises((ValueError, SyntaxError)):
            evaluate_expression("__import__('os')")

    def test_rejects_variable(self):
        with pytest.raises(ValueError, match="Expressao nao suportada"):
            evaluate_expression("x + 1")


class TestCalculatorTool:
    def test_integer_result(self):
        result = calculator.invoke({"expression": "2 + 3"})
        assert result == "5"

    def test_float_result(self):
        result = calculator.invoke({"expression": "7 / 2"})
        assert result == "3.5"

    def test_complex_expression(self):
        result = calculator.invoke({"expression": "(15 + 7) * 3"})
        assert result == "66"


class TestCurrentTimeTool:
    def test_utc(self):
        result = current_time.invoke({"timezone_name": "UTC"})
        assert "T" in result  # formato ISO

    def test_sao_paulo(self):
        result = current_time.invoke({"timezone_name": "America/Sao_Paulo"})
        assert "T" in result

    def test_invalid_timezone(self):
        result = current_time.invoke({"timezone_name": "Invalid/Zone"})
        assert "invalido" in result
