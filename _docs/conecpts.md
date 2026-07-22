## DDD

#### Value Object (VO)
Um tipo que representa um valor (não uma entidade com identidade própria), definido pelos seus atributos, imutável e que carrega dentro de si a regra de validação daquele valor.
Sempre que um primitivo (string, int) carrega uma invariante de negócio — se o valor pode ser "inválido" segundo alguma regra, ele merece um VO em vez de trafegar como str/int cru pelo sistema.
Se um formato/regra é validado em mais de um lugar (serializer, service, teste), é sinal de que devia ser VO, não str. Dinheiro, e-mail, faixa de valores seguiriam o mesmo padrão.

