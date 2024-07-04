from typing import Any, TypeGuard
import os
from numbers import Real
from lark import Lark, ParseTree, Token, Transformer
import math
from functools import cache


def _is_real(*values: object) -> TypeGuard[Real]:
    return all(isinstance(value, Real) for value in values)


class _ScalingTransformer(Transformer[Any, Any]):
    x: int | float

    def __init__(self, x: int | float):
        self.x = x

    def INT(self, token: Token):
        return int(token)

    def FLOAT(self, token: Token):
        return float(token)

    def HEX(self, token: Token):
        # TODO: Endianness?
        return bytes.fromhex(token[2:])

    def BITS(self, token: Token):
        # TODO: Endianness?
        return int(token, base=0).to_bytes(byteorder="big")

    def CNAME(self, token: Token):
        if token.value in ("x", "X"):
            return self.x
        return token.value

    def atom(self, tokens: list[Any]):
        assert len(tokens) == 1
        return tokens[0]

    def call(self, tokens: list[str | int | float]):
        fn_name, arg = tokens
        assert _is_real(arg)
        match fn_name:
            case "ln":
                return math.log(arg)
            case _:
                raise ValueError(f"Unknown function: {fn_name}")

    def add(self, tokens: list[float | int]):
        assert len(tokens) == 2
        l, r = tokens
        assert _is_real(l, r)
        return l + r

    def sub(self, tokens: list[float | int]):
        assert len(tokens) == 2
        l, r = tokens
        assert _is_real(l, r)
        return l - r

    def neg(self, tokens: list[float | int]):
        assert len(tokens) == 1
        return -tokens[0]

    def div(self, tokens: list[float | int]):
        assert len(tokens) == 2
        l, r = tokens
        assert _is_real(l, r)
        return l / r

    def mul(self, tokens: list[float | int]):
        assert len(tokens) == 2
        l, r = tokens
        assert _is_real(l, r)
        return l * r

    def band(self, tokens: list[float | int | bytes]):
        assert len(tokens) == 2
        l, r = tokens
        assert isinstance(l, int) or isinstance(l, bytes)
        assert isinstance(r, int) or isinstance(r, bytes)
        l_int = l if isinstance(l, int) else int.from_bytes(l)
        r_int = r if isinstance(r, int) else int.from_bytes(r)
        return l_int & r_int


@cache
def evaluate(tree: ParseTree, x: int | float) -> int | float:
    transformer = _ScalingTransformer(x)
    return transformer.transform(tree)


class ScalingParser:
    _parser: Lark

    def __init__(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "_scaling.lark"), "r") as f:
            self._parser = Lark(
                f,
                start="start",
                parser="lalr",
                lexer="contextual",
                cache=True,
            )

    def parse(self, expression: str) -> ParseTree:
        return self._parser.parse(expression)
