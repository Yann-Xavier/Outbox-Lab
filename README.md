# Outbox Lab

O banco confirmou a gravação do evento, mas o processo caiu antes de avisar o próximo sistema. Quando voltar, como ele vai saber o que ainda precisa enviar?

Este laboratório demonstra o padrão **Transactional Outbox** com Python e SQLite. O evento e a intenção de entrega são gravados na mesma transação. Depois, um worker consulta a outbox e marca cada entrega como concluída quando o envio retorna com sucesso.

## Como funciona

1. `record()` insere o evento em `events` e a entrega pendente em `outbox`. Se a segunda gravação falhar, a transação desfaz a primeira.
2. `dispatch()` busca entregas pendentes em ordem de gravação e chama o receptor com o ID do evento.
3. Se o receptor retornar com sucesso, o worker marca a entrega como concluída. Se a chamada falhar, a entrega continua pendente para uma nova execução e o worker segue para a próxima. `dispatch()` retorna os IDs que falharam.

## Como executar

Na pasta que contém `lab.py` e `test_lab.py`, rode o comando abaixo com Python 3. O projeto usa apenas a biblioteca padrão.

```bash
python -m unittest -v
```

| Cenário | O que o teste verifica |
| --- | --- |
| Processo cai antes do envio | Um processo filho grava o evento e termina com `os._exit`. Outro processo encontra a entrega pendente e envia uma vez. |
| Processo cai depois do envio | O processo filho envia e termina antes de marcar a entrega. A entrega continua pendente e o próximo despacho envia o mesmo ID de novo. |
| Confirmação perdida após o recebimento | O receptor recebe o evento e lança timeout. O mesmo ID é enviado duas vezes. O teste não deduplica: ele mostra que o reenvio acontece. |
| Falha em um evento | O primeiro evento falha e os dois seguintes são entregues na mesma execução. |
| Falha ao gravar a outbox | O banco desfaz a gravação do evento. |

## Escopo

O laboratório usa um único worker e simula o receptor com uma função local. Não há limite de tentativas, backoff nem fila de mensagens mortas: um evento que sempre falha fica pendente para sempre. A reentrega depende de uma nova chamada a `dispatch()`. Se o receptor aplicar o efeito e a confirmação se perder, a outbox pode reenviar o evento. Em produção, o receptor precisa registrar a deduplicação de forma durável e consistente com o efeito aplicado.

O [Webhook Lab](https://github.com/Yann-Xavier/webhook-lab) explora o outro lado desse fluxo: como o receptor lida com a chegada repetida de um evento.
