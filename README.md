# Outbox Lab

O banco confirmou a gravação do evento, mas o processo caiu antes de avisar o próximo sistema. Quando voltar, como ele vai saber o que ainda precisa enviar?

Este laboratório demonstra o padrão **Transactional Outbox** com Python e SQLite. O evento e a intenção de entrega são gravados na mesma transação. Depois, um worker consulta a outbox e marca cada entrega como concluída quando o envio retorna com sucesso.

## Como funciona

1. `record()` insere o evento em `events` e a entrega pendente em `outbox`. Se a segunda gravação falhar, a transação desfaz a primeira.
2. `dispatch()` busca entregas pendentes e chama o receptor com o ID do evento.
3. Se o receptor retornar com sucesso, o worker marca a entrega como concluída. Se a chamada falhar, a entrega continua pendente para uma nova execução.

## Como executar

Na pasta que contém `lab.py` e `test_lab.py`, rode o comando abaixo com Python 3. O projeto usa apenas a biblioteca padrão.

```bash
python -m unittest -v
```

| Cenário | O que o teste verifica |
| --- | --- |
| Interrupção antes do envio | Uma nova conexão encontra o registro pendente no SQLite. Depois da confirmação, outro despacho não reenvia o evento. |
| Confirmação perdida após o recebimento | O mesmo ID é enviado duas vezes. O receptor simulado registra um único efeito em memória. |
| Falha ao gravar a outbox | O banco desfaz a gravação do evento. |

## Escopo

O laboratório usa um único worker e simula o receptor com uma função local. A reentrega depende de uma nova chamada a `dispatch()`. Se o receptor aplicar o efeito e a confirmação se perder, a outbox pode reenviar o evento. Em produção, o receptor precisa registrar a deduplicação de forma durável e consistente com o efeito aplicado.

O [Webhook Lab](https://github.com/Yann-Xavier/webhook-lab) explora o outro lado desse fluxo: como o receptor lida com a chegada repetida de um evento.
