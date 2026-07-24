# Financial Advisor — instruções do projeto

## Fluxo de Git

A partir de agora, todo novo desenvolvimento (nova feature, ajuste,
correção) deve seguir este fluxo — nunca commitar direto na `main`:

1. Criar uma branch separada a partir da `main` (ex: `git checkout -b
   feature/nome-descritivo` ou `fix/nome-descritivo`).
2. Fazer os commits do desenvolvimento nessa branch.
3. Ao concluir e validar (testes passando, verificação end-to-end feita),
   dar merge da branch de volta na `main` (localmente ou via PR no
   GitHub, conforme o que o usuário pedir no momento).
4. Só então fazer push da `main` atualizada.

A `main` deve sempre refletir um estado estável e testado do projeto.
