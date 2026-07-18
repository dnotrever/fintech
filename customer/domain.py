from dataclasses import dataclass


@dataclass(frozen=True)
class CPF:

    value: str

    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValueError(f'Invalid CPF: {self.value}')

    @staticmethod
    def _is_valid(cpf: str) -> bool:
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        if cpf == cpf[0] * 11:
            return False
        def check_digit(digits: str, weights: range) -> int:
            total = sum(int(d) * w for d, w in zip(digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        digit1 = check_digit(cpf[:9], range(10, 1, -1))
        digit2 = check_digit(cpf[:9] + str(digit1), range(11, 1, -1))
        return cpf[-2:] == f'{digit1}{digit2}'

    def __str__(self) -> str:
        return self.value

