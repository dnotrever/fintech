
#### Fluxo de Envio de E-mail de Confirmação (Criação de Conta e Reenvio):

`fintech-backend`
- Django deleta tokens de confirmação não confirmados do usuário no Postgres
- Django cria um novo token de confirmação pro usuário no Postgres
- Django commita o novo token de confirmação no Postgres
- Celery monta a mensagem da task e entrega para o Kombu
- Kombu publica a mensagem da task no Redis
- Django retorna resposta (não trava o fluxo)

`fintech-redis`
- A mensagem da task fica guardada na lista 'celery' até algum worker consumir

`fintech-celery-worker`
- Celery recebe e desserializa a mensagem da task
- Celery executa a task registrada
- Django executa o envio da notificação
  - Sucesso:
    - Task concluída
  - Falha:
    - Celery monta mensagem de retry e entrega pro Kombu
    - Kombu republica no Redis (com backoff, até 3 vezes)


