#### `uv lock`
Gera/atualiza o arquivo uv.lock a partir do pyproject.toml — resolve todas as versões exatas das dependências (e sub-dependências) e trava elas no lockfile, sem instalar nada.

#### `uv add <package>[@<version>]` | `uv add -- dev <package>[@<version>]`
Instala dependências.

#### `uv remove <package>`
Remove dependências.

#### `uv sync --frozen`
Instala as deps do projeto (lê pyproject.toml + uv.lock).
O `--frozen` não recalcula/atualiza o lockfile antes; usa ele como está. Se estiver dessincronizado, instala mesmo assim (não dá erro, só ignora a checagem).

#### `uv run <command>`
Executa um comando dentro do .venv do projeto, sem precisar ativar (source .venv/bin/activate) manualmente antes.

