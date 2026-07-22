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


_VALID_DDDS = frozenset({
    11, 12, 13, 14, 15, 16, 17, 18, 19,
    21, 22, 24,
    27, 28,
    31, 32, 33, 34, 35, 37, 38,
    41, 42, 43, 44, 45, 46, 47, 48, 49,
    51, 53, 54, 55,
    61, 62, 63, 64, 65, 66, 67, 68, 69,
    71, 73, 74, 75, 77, 79,
    81, 82, 83, 84, 85, 86, 87, 88, 89,
    91, 92, 93, 94, 95, 96, 97, 98, 99,
})


@dataclass(frozen=True)
class Phone:

    value: str

    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValueError(f'Invalid phone: {self.value}')

    @staticmethod
    def _is_valid(phone: str) -> bool:
        if not phone.isdigit() or len(phone) not in (10, 11):
            return False
        if int(phone[:2]) not in _VALID_DDDS:
            return False
        number = phone[2:]
        if len(number) == 9:
            return number[0] == '9'
        return number[0] in '2345'

    def __str__(self) -> str:
        return self.value

