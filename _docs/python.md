## Decorators

#### `@dataclass`
É um decorator do Python que gera automaticamente `__init__`, `__repr__` e `__eq__` pra uma classe, a partir dos atributos declarados (evita escrever esse boilerplate na mão).
`frozen=True` — deixa a instância imutável depois de criada: qualquer tentativa de reatribuir um atributo levanta FrozenInstanceError, em vez de simplesmente sobrescrever o valor como uma classe normal permitiria.

#### `@staticmethod`
Marca um método que não recebe self — não acessa nem depende dos atributos da instância. É basicamente uma função normal que só está agrupada dentro da classe por organização/semântica.

## Commands

#### `python manage.py migrate --noinput`
Faz o migrate rodar sem pedir confirmação interativa (aquelas perguntas tipo "yes/no" que o Django às vezes mostra).


## Models

### `models.ForeignKey`

#### `on_delete`
`CASCADE` — deleta o registro relacionado junto.
`PROTECT` — bloqueia a exclusão, lança erro.
`RESTRICT` — bloqueia a exclusão direta, mas permite se for parte de um CASCADE de outro relacionamento.
`SET_NULL` — define o campo como NULL (precisa de `null=True`).
`SET_DEFAULT` — define o campo com um valor padrão (precisa de default).
`SET(...)` — define um valor customizado (função ou objeto).
`DO_NOTHING` — não faz nada automaticamente (risco de erro no banco).

#### `settings.AUTH_USER_MODEL`
É a forma recomendada de referenciar o model de usuário em ForeignKey/OneToOneField, em vez de importar User direto.
