## Dockerfile

#### `--from`
No `COPY` copia arquivos de outra imagem (ou outro estágio de build), em vez do seu próprio sistema de arquivos local.

#### .dockerignore
Só afeta o build da imagem (o COPY . /app/ do Dockerfile). Ele não tem nenhum efeito sobre volumes montados em runtime (o volumes: .:/app do docker-compose.yml).


## Docker Compose

#### `target: stage_alias`
Diz pro Compose usar aquele estágio (stage) específico do Dockerfile como build final 

### `${VAR}` vs `env_file`
- O ${VAR} só substitui valor dentro do YAML (automático, lê .env da pasta do compose). Só usar
- no YAML (ex: environment: X: ${VAR}) → interpolação já resolve.
- O env_file injeta variáveis no container, pra app ler via código (precisa declarar por serviço). Regra: app lê env var → precisa de env_file.

