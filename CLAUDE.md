# CLAUDE.md

Guia para agentes de IA operando neste repositório.

## Parte A — Detectado

### Stack
Python 3.12+ (Docker roda 3.13), Django 6.0, Django REST Framework 3.17 + SimpleJWT 5.5, PostgreSQL 17 via psycopg3, uv como gerenciador de pacotes.

### Comandos
Fluxo real é via Docker Compose (host da DB é fixo em `postgres`, só resolve dentro da rede do compose — ver Gotchas).

```bash
# Setup (uma vez)
make network

# Subir stack de dev (build + up -d)
make dev-build

# Migrations
make migrations              # gera (makemigrations)
make dev-migrate             # aplica (migrate)

# Superusuário
make dev-superuser

# Novo app Django
make startapp app=<nome>

# Lint / format (ruff é dependência dev; sem config custom em pyproject.toml)
uv run ruff check .
uv run ruff format .

# Testes — dentro do container, ou local com uv sync feito
docker compose -f _docker/docker-compose.dev.yml --env-file .env exec backend uv run python3 manage.py test
uv run python3 manage.py test account.tests.OpenAccountTests.test_creates_checking_account_for_customer  # teste único
```

VERIFICAR: `pytest` está em `[dependency-groups.dev]` mas não há `pytest.ini`, `conftest.py` nem `pytest-django` no lockfile, e todos os testes existentes usam `django.test.TestCase`/`APIClient`. O comando real de teste é `manage.py test`, não `pytest`.

### Estrutura
- Um app Django por domínio: `customer`, `account`, `authentication`, `notification`. `core` é só configuração de projeto (`settings/base.py` + `settings/dev.py`, `urls.py`, `wsgi/asgi`).
- `customer/domain.py` guarda Value Objects de domínio (ex.: `CPF`) fora de `models.py` — é onde regra de validação de valor primitivo deve entrar, não dentro do model.
- Regra de negócio de escrita fica em `services.py` de cada app (`account/services.py:open_account`, `customer/services.py:register_customer`, `authentication/services.py:send_confirmation_email`), não nas views.
- `notification/` é o único app com `adapters.py` (`ResendEmailAdapter`) + `channels.py` (`Protocol EmailChannel`) — é o exemplo de referência no repo para integração externa via Adapter/DIP (injeção por parâmetro `channel` em `send_email`).
- Não existe `selectors.py` em nenhum app ainda — leituras hoje acontecem direto via ORM em `views.py`/`serializers.py` (ver Divergências).

### Convenções reais (≥2 ocorrências)
- Todas as escritas de domínio usam keyword-only args (`*,`) em funções de `services.py` e nos `dataclass` de `domain.py`.
- Exceções de domínio são classes simples (`class XError(Exception): pass`) definidas no próprio `models.py`/`services.py` do app que as levanta (`InsufficientFundsError`, `InvalidAccountStatusTransitionError`, `AccountNumberGenerationError`).
- Views DRF são `APIView` com `permission_classes` explícito por classe (`AllowAny`/`IsAuthenticated`), nunca deixado no default global.
- Serializer de escrita (`CustomerCreateSerializer`, `LogoutSerializer`, ...) é `serializers.Serializer` puro; serializer de leitura/saída é `ModelSerializer` com `read_only_fields = fields`.
- Views delegam para `services.py` e nunca chamam `Model.objects.create` diretamente para fluxo de negócio multi-campo.

### Gotchas
- `DATABASES['default']['HOST']` em `core/settings/base.py:68` é fixo em `'postgres'` (nome do serviço no compose). Rodar `manage.py` fora do container/rede do Docker não conecta no banco sem override.
- `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `RESEND_API_KEY` não têm default em `env()` — sobem `ImproperlyConfigured` imediatamente se ausentes do `.env`.
- `_docker/entrypoint.dev.sh` roda `migrate --noinput` automaticamente antes do `runserver` — só vale para o container `backend`; `make dev-migrate`/`make migrations` são para reaplicar manualmente depois que o container já está de pé.
- `.env` não é versionado (está no `.gitignore`); `.env.example` não lista `DEFAULT_FROM_EMAIL` nem `BACKEND_BASE_URL` (têm default no código, são opcionais).

### Segurança (postura)
- Segredos vêm só de variáveis de ambiente via `django-environ`, lidas em `core/settings/base.py`; nenhum valor sensível hardcoded.
- Validação de entrada é responsabilidade do serializer na fronteira HTTP (`validate_*` em `CustomerCreateSerializer`), incluindo checagem de unicidade contra o banco.
- AuthZ é declarada por view via `permission_classes`; autenticação é JWT (SimpleJWT) configurada globalmente em `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`.
- Acesso a dados é 100% via Django ORM — nenhum SQL cru (`.raw()`/`cursor.execute`) no repo.

### Robustez
- `account/services.py:open_account` usa `transaction.atomic()` para a única escrita que faz (criação de `Account` com retry de colisão de número).
- RISCO: `notification/adapters.py:ResendEmailAdapter.send` chama a API do Resend sem nenhum timeout — é a única chamada de rede externa do projeto hoje e não tem proteção.

## Parte B — Alvo

Regras de engenharia (código novo e alterado)

Obrigatórias, não sugestões. Regra vs. caminho fácil → siga a regra. Precisa violar uma? Pare e explique por quê antes de escrever.

### Filosofia (decide o que NÃO escrever)
- YAGNI: só o que o problema atual exige. Sem parâmetro/flag/abstração para uso futuro hipotético. Abstração só na 2ª ocorrência real do problema.
- KISS: a solução mais simples que resolve o caso atual.
- DRY: cada regra de negócio vive em UM lugar. Duplicou lógica de decisão → extraia. (Duplicar estrutura trivial não viola; duplicar conhecimento viola.)

### SOLID (mecânico)
- SRP: uma razão para mudar por classe/módulo. I/O + regra + formatação juntos → separe.
- OCP: comportamento novo por classe/implementação nova, não por if/elif crescente numa função existente.
- LSP: qualquer implementação de um contrato substitui outra sem quebrar o chamador. NotImplementedError/contrato estreitado = herança errada.
- ISP: interface enxuta — só os métodos que o consumidor usa.
- DIP: caso de uso depende de interface/abstração; dependência entra por parâmetro (injeção), não instanciada dentro do service.

### POO
- Encapsulamento: estado interno privado; exponha operações, não atributos crus.
- Abstração: contrato ("quê") separado da implementação ("como").
- Herança só para "é um" real com contrato compartilhado; na dúvida, composição.
- Polimorfismo por contrato: sem isinstance/type() para desviar fluxo.

### Modelagem de domínio
- Value Object no lugar de primitivo quando o valor carrega regra (dinheiro, CPF, e-mail, faixa). Não passe primitivo cru com invariante embutida.
- Imutabilidade: Value Object não muda; operação retorna novo objeto.
- Máquina de estados: transição inválida é bloqueada no domínio, não permitida.
- Exceções de domínio falam a língua do negócio, lançadas no domínio; a fronteira traduz para HTTP. O domínio não conhece HTTP.

### Design patterns (quando alcançar — não force)
- Strategy: algoritmos intercambiáveis atrás de interface, em runtime. Só com ≥2 variações reais.
- Adapter: traduz interface externa incompatível para o contrato do domínio; o detalhe do provedor não vaza para dentro.
- Factory: um ponto decide qual implementação concreta criar.
- Facade: uma entrada simples orquestra subsistemas por trás.

### Confiabilidade
- Atomicidade: operação que toca várias tabelas roda em transação — tudo ou nada.
- Idempotência: operação reexecutável (retry, task, webhook) tem o efeito de uma só; proteja com chave/guard.
- Timeout em toda chamada externa. Nenhuma chamada de rede sem timeout.

### Testes
Unitário (domínio isolado) + integração (fluxo com atomicidade) + idempotência onde importa. Código novo com regra de negócio entra com teste; sem teste = não concluído.

### Quando o projeto for Django/DRF
- Monólito modular: separe por domínio; módulo expõe fronteira, não importe internals de outro módulo direto.
- Responsabilidade por arquivo:
  - `models.py`: dados + invariantes que dependem só do próprio objeto.
  - `services.py`: orquestra o caso de uso; regra que cruza objetos; toda escrita passa aqui.
  - `selectors.py`: todas as leituras/consultas ao banco.
  - `views.py`: fronteira HTTP; delega a service/selector; traduz resultado e exceção de domínio. Sem regra de negócio.
  - `serializers.py`: valida formato e converte domínio ↔ JSON. Sem regra.
  - `adapters.py`: traduz integração externa (gateway, API, SDK) para o contrato do domínio.
- N+1: select_related/prefetch_related em listagem; nunca query em loop.
- Celery: task idempotente, retry seguro, efeito colateral protegido.
- Saga (orquestração): fluxo multi-passo com efeito externo tem orquestrador que coordena e dispara compensação no passo que falha; sem estado parcial órfão.
- Postgres é a fonte da verdade; Redis é cache/broker.

## Parte C — Fechamento

### Divergências detectadas
- Não há `selectors.py` em nenhum app: leituras/consultas (incl. checagem de unicidade) acontecem direto em `views.py` (`authentication/views.py:ConfirmEmailView.get`, `ResendConfirmationView.post`) e em `serializers.py` (`customer/serializers.py:CustomerCreateSerializer.validate_username/validate_cpf`), violando a separação leitura/escrita do bloco Django/DRF.
- `customer/services.py:register_customer` escreve em `User`, `Customer`, `Address` e `Account` sem um `transaction.atomic()` envolvendo o fluxo inteiro — usa rollback manual (`delete()` em cascata no `except`) em vez de atomicidade de transação.

### Não faça
- Não instancie `ResendEmailAdapter` (ou qualquer adapter de integração externa) direto dentro de um service — sempre por injeção via parâmetro, seguindo o padrão de `notification/services.py:send_email`.
- Não coloque regra de negócio (checagem de unicidade, transição de estado, cálculo) dentro de `serializers.py` ou `views.py` — pertence a `services.py`/`selectors.py`/domínio.

### Como validar antes de concluir
```bash
uv run ruff check .
docker compose -f _docker/docker-compose.dev.yml --env-file .env exec backend uv run python3 manage.py makemigrations --check --dry-run
docker compose -f _docker/docker-compose.dev.yml --env-file .env exec backend uv run python3 manage.py test
```
Confira: migração gerada para todo `models.py` alterado; app novo registrado em `core/settings/base.py:INSTALLED_APPS` e roteado em `core/urls.py`; `.env.example` atualizado se uma nova env var obrigatória foi introduzida.

---
Examinado: `pyproject.toml`, `Makefile`, `README.md` (vazio), `_docs/*.md`, `.env`/`.env.example`, `.claude/settings.json`, `.vscode/settings.json`, `core/settings/base.py`/`dev.py`, `core/urls.py`, `manage.py`, `_docker/docker-compose.dev.yml`, `_docker/Dockerfile.dev`, `_docker/entrypoint.dev.sh`, `api_tester.rest.example`, todos os `models.py`/`services.py`/`views.py`/`serializers.py`/`urls.py`/`tests.py` de `account`, `authentication`, `customer`, `notification`, `customer/domain.py`, `notification/adapters.py`/`channels.py`, migrations de `account`/`customer`/`authentication`, `git log`, greps por SQL cru/`isinstance`/Celery/timeout. Não havia CLAUDE.md, `.cursorrules` ou `copilot-instructions.md` prévios.
