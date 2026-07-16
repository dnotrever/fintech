#### Aspas Simples x Sem Aspas
Compose v2 (atual): remove as aspas simples corretamente, funciona sem problema.
Compose v1 (legado): bug conhecido — não remove as aspas, e elas viram parte literal do valor ('minha-chave' em vez de minha-chave), quebrando senhas/tokens silenciosamente.
Recomendação: não usar aspas no .env, a menos que o valor tenha espaço ou caractere especial — assim evita depender da versão do Compose de quem for rodar o projeto.

