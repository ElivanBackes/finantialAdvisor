# Financial Advisor

Sistema de orientação financeira que coleta dados de mercado, roda 3
análises independentes e sintetiza tudo em uma recomendação final — uma de
5 categorias (`Compra Forte` / `Comprar` / `Aguardar` / `Manter` / `Revisão
Necessária`) — sobre se vale a pena realizar um novo aporte, já considerando
valuation e a composição da carteira do usuário.

**MVP**: ações da bolsa brasileira (B3). A arquitetura já é genérica o
suficiente (`AssetType`) para suportar no futuro ações/ETFs internacionais,
criptomoedas e renda fixa/passivos (dívidas, financiamentos), sem precisar
reescrever o núcleo.

> ⚠️ As recomendações são geradas automaticamente a partir de heurísticas
> simples sobre dados públicos. **Não constituem aconselhamento financeiro
> profissional.**

## Como funciona (pipeline de 4 etapas)

```
Buscar/Cadastrar → Coletar e Analisar → Gerar Conclusão → Gerar Recomendação
     (ativo)         (3 análises)         (síntese)         (veredito)
```

1. **Coleta de dados** (`collectors/`): busca dados brutos de fontes
   públicas — [yfinance](https://pypi.org/project/yfinance/) e
   [brapi.dev](https://brapi.dev/) para cotação/fundamentos, e
   [NewsAPI](https://newsapi.org/) para notícias — salvos em `raw_data`.
2. **3 análises independentes** (`analyzers/`), cada uma com seu próprio
   schema e fontes, mas podendo compartilhar dados brutos entre si:
   - **Fundamentalista**: P/L, P/VP, Dividend Yield (com payout como
     modificador de sustentabilidade), ROE, endividamento, EV/EBITDA, FCF
     yield, crescimento (lucro/receita), ROIC (via demonstrativos
     financeiros) e histórico dos múltiplos (compara P/L, P/VP e EV/EBITDA
     atuais com a própria média histórica do ativo).
   - **Técnica**: médias móveis (SMA 20/50/200), RSI(14), MACD, tendência.
   - **Notícias/Sentimento**: score de sentimento (léxico PT-BR) sobre
     notícias recentes do ativo.
3. **Conclusão** (`conclusions/`): cada análise vira um sub-score
   normalizado (-100 a +100); a média das disponíveis (redistribuindo peso
   se alguma faltar) gera um `overall_score` + rótulo `favoravel` /
   `neutro` / `desfavoravel`. O sub-score fundamentalista é uma **composição
   ponderada** (não média simples), seguindo os pesos da especificação:
   valuation 30%, Dividend Yield 15%, ROE 10%, crescimento 10%, FCF yield
   10%, endividamento 10%, ROIC 5%, histórico dos múltiplos 5%, EV/EBITDA
   2%, P/L 1,5%, P/VP 1,5% — pesos redistribuídos entre os critérios
   disponíveis quando algum falta (ex: ROIC ausente, histórico insuficiente).
   **Valuation** compara o preço atual a um preço-teto conservador (o menor
   entre a fórmula de Graham, `sqrt(22.5 x LPA x VPA)`, e a de Bazin,
   `DPA / 6%`). **Payout** não tem peso próprio — funciona como modificador:
   payout acima de 60% reduz a nota do dividend yield proporcionalmente (a
   spec explicitamente proíbe recomendar compra só pelo DY). **ROIC** vem de
   EBIT/alíquota efetiva/capital investido (`.financials`/`.balance_sheet`
   do yfinance). **Histórico dos múltiplos** compara P/L, P/VP e EV/EBITDA
   atuais com a média das análises fundamentalistas passadas do próprio
   ativo (mín. 3 pontos) — fica ausente para ativos recém-cadastrados.
4. **Recomendação** (`recommendations/`): classifica o ativo em uma de 5
   categorias — `Compra Forte` / `Comprar` / `Aguardar` / `Manter` /
   `Revisão Necessária` — a partir do sub-score fundamentalista (que já
   embute o valuation), convertido para uma nota 0-10. Técnica e
   notícias/sentimento não decidem a categoria, mas alimentam um sinal
   auxiliar de **concordância** e **confiança** (`alta`/`media`/`baixa`)
   junto com a justificativa textual. Dois ajustes são aplicados em
   sequência sobre o sub-score/categoria fundamentalista:
   1. **Cenário macro setorial** (`macro/`): a partir do setor/indústria do
      ativo (yfinance), soma um pequeno ajuste (±10 pontos, nunca um
      critério pesado) ao sub-score — Petróleo/Gás usa a tendência do preço
      do Brent e do câmbio (BCB); Bancos/Seguros usa o nível da Selic
      (BCB). Demais setores não recebem ajuste (cobertura parcial por
      design — ver Limitações). Isso pode inclusive mudar a categoria (ex:
      de `Aguardar` para `Comprar`) antes da alocação ser considerada.
   2. **Estratégia de alocação de carteira** (`portfolio/`): se o usuário
      registrou uma posição para o ativo (`Carteira`) e ele já está
      **acima** da alocação-alvo, uma categoria `Compra Forte`/`Comprar` é
      rebaixada para `Aguardar` — evita concentrar novos aportes em ativos
      já sobreponderados. Nunca *promove* uma categoria (fundamentos e
      macro sempre têm prioridade); registrar posição é opcional.

Cada etapa de análise persiste seu resultado no MongoDB de forma
*append-only* (histórico completo, nunca sobrescreve), então o dashboard
sempre mostra o resultado mais recente de cada estágio. Posições de carteira
(`positions`) são a exceção: como representam estado atual do usuário (não
um evento histórico), são upsert por ativo — igual à coleção `assets`.

Sempre que uma Recomendação é gerada com sucesso, `RecommendationService`
também grava um snapshot em `analysis_history` (`analysis_history/`) —
upsert por ativo, igual a `assets`/`positions`, não confundir com
`recommendations`, que continua sendo o histórico completo/imutável de cada
veredito. Essa coleção existe só para alimentar a tela **Histórico de
Análises** (ticker, empresa, score final, DY esperado, preço atual/teto,
potencial de valorização e recomendação) sem precisar agregar as outras
coleções toda vez que a tela carrega. Ativos apenas cadastrados em "Buscar
Ativo" (sem Recomendação gerada) não aparecem nela.

## Setup

Pré-requisitos: Python 3.12+, Docker (para o MongoDB local).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # preencha NEWSAPI_KEY para a análise de notícias funcionar

docker compose up -d          # sobe o MongoDB local
python scripts/check_setup.py # confirma conexão + cria índices
```

Variáveis em `.env`:

| Variável | Obrigatória? | Descrição |
|---|---|---|
| `MONGO_URI` / `MONGO_DB_NAME` | Não (tem default) | Conexão com o Mongo local |
| `NEWSAPI_KEY` | Só para a análise de notícias | Chave gratuita em [newsapi.org/register](https://newsapi.org/register) |
| `BRAPI_API_TOKEN` | Só para a fonte brapi.dev | A brapi.dev passou a exigir token em toda requisição — sem ele, essa fonte é pulada (isolado, não quebra as outras análises, que seguem funcionando via yfinance/NewsAPI). Token gratuito em [brapi.dev](https://brapi.dev) — o app só usa a cotação simples, compatível com o plano gratuito |

## Como usar

### Via dashboard (Streamlit)

```bash
streamlit run app.py
```

Abre em `http://localhost:8501` com 8 páginas na barra lateral:

1. **Buscar Ativo**: informe um ticker B3 com sufixo `.SA` (ex: `PETR4.SA`),
   clique em "Buscar / Cadastrar" e depois em "Coletar e Analisar".
2. **Análise Fundamentalista** / **Análise Técnica** / **Notícias/Sentimento**:
   mostram o resultado mais recente de cada análise para o ativo selecionado.
3. **Conclusão e Recomendação**: botões "Gerar Conclusão" e "Gerar
   Recomendação" (nessa ordem — a recomendação consome a última conclusão
   salva, não recalcula nada sozinha).
4. **Carteira** (opcional): registre quantidade possuída, preço médio e
   alocação-alvo (%) do ativo selecionado. Mostra a alocação atual calculada
   (valor da posição / valor total da carteira, usando o preço mais recente
   coletado) e uma tabela com todas as posições cadastradas.
5. **Histórico de Análises**: tabela com todos os ativos já efetivamente
   analisados (ranking por Score Final, DY esperado, preço atual/teto,
   potencial de valorização, recomendação com badge colorida). Tem busca
   dinâmica por ticker/empresa, filtros (recomendação, faixa de score, faixa
   de DY), paginação e um atalho para "carregar" um ativo já analisado nas
   demais páginas sem precisar coletar de novo.
6. **Logs**: histórico de execução persistido no MongoDB (ver seção
   [Logs](#logs) abaixo) — filtro por nível e por ticker.

### Via linha de comando (sem Streamlit)

Útil para depurar ou automatizar. Cada script assume que o anterior já rodou
para o mesmo ticker:

```bash
python scripts/collect_and_analyze.py PETR4.SA --name "Petrobras"  # coleta + 3 análises
python scripts/build_conclusion.py PETR4.SA                        # síntese
python scripts/build_recommendation.py PETR4.SA                    # veredito final
```

Todos imprimem o resultado em JSON e retornam exit code `1` com mensagem
amigável em caso de erro (ex: ticker não encontrado, análises insuficientes).

## Testes

```bash
python -m pytest tests/ -v
```

Testes unitários com mocks/fixtures (sem rede real, sem Mongo real) para
collectors, analyzers, scoring de conclusão/recomendação e orquestração dos
services. `scripts/*.py` servem como testes de integração manuais contra as
APIs e o Mongo reais.

Para testar o dashboard de ponta a ponta num navegador headless (Playwright),
use a skill `.claude/skills/run-finantialadvisor/` — documenta setup, um
driver que dirige o app inteiro (cadastrar → coletar → concluir → recomendar,
com screenshot em cada etapa) e os principais gotchas já encontrados.

## Logs

Todo log a partir de `INFO` (início/sucesso/falha de cada operação) é
persistido na coleção `logs` do MongoDB — não só no `stdout`/`stderr` do
processo, que costuma ficar preso ao terminal de quem rodou o app.
Configurado uma única vez por processo via `config/logging_setup.py`
(`configure_logging()`, chamado em `app.py` e em todos os `scripts/*.py`).

- **Ver na página "Logs" do dashboard** (filtro por nível/ticker), ou
  consultar direto: `LogRepository().find_recent(limit=200, level=..., ticker=...)`.
- Cada registro guarda `timestamp`, `level`, `logger`, `ticker` (quando
  disponível) e `message`/`exception`.
- Retenção: índice TTL de 30 dias — expira sozinho, sem limpeza manual.

## Estrutura de pastas

```
core/            abstrações centrais: Asset, AssetType, Collector, Analyzer
collectors/      coleta de dados brutos (yfinance, brapi.dev, NewsAPI)
analyzers/       as 3 análises (fundamentalista, técnica, sentimento)
conclusions/     síntese das 3 análises em um score + rótulo
recommendations/ veredito final (categoria + confiança + justificativa)
portfolio/       posições da carteira do usuário e cálculo de alocação
macro/           ajuste de cenário macroeconômico setorial (BCB, Brent)
analysis_history/ snapshot consultável de todo ativo já analisado (tela
                 "Histórico de Análises")
persistence/     repositórios MongoDB e definição de índices
services/        orquestração (AssetService: coleta -> análises)
config/          configuração (.env, conexão Mongo, logging_setup.py)
dashboard/       app Streamlit (páginas e componentes)
scripts/         scripts manuais (um por etapa do pipeline)
tests/           testes automatizados (espelha a estrutura acima)
```

Regra de camadas: `dashboard/` nunca acessa `pymongo`/`collectors`/
`analyzers` diretamente — sempre passa pelos `services/`/`conclusions/`/
`recommendations/`. `conclusions/` e `recommendations/` não recalculam a
etapa anterior — sempre leem o resultado mais recente já persistido.

## Limitações conhecidas / próximos passos

- yfinance não é consistente no formato de `dividend_yield`/`roe` (ora
  fração, ora percentual já multiplicado) — `conclusions/scoring.py`
  aplica uma heurística best-effort para normalizar (ver comentário em
  `_normalize_percent`).
- As regras de scoring (bandas de P/L, P/VP, RSI etc.) são heurísticas
  simples para o MVP, não calibradas com dados históricos reais.
- NewsAPI (free tier) cobre só notícias do último mês e não deve ser usada
  em produção — ok para uso pessoal/MVP.
- brapi.dev passou a exigir `BRAPI_API_TOKEN` em toda requisição (mudança de
  política da API, não do nosso código) — sem token, essa fonte é pulada e
  as análises seguem funcionando só com yfinance/NewsAPI. O collector só usa
  a cotação simples (compatível com o plano gratuito do token).
- yfinance exige o sufixo `.SA` para tickers da B3 (ex: `PETR4.SA`, não
  `PETR4`) — sem ele, a coleta falha para essa fonte; o app não valida/
  normaliza isso automaticamente ainda.
- Expansão natural: novos `AssetType` (cripto, ações internacionais, renda
  fixa/passivos) exigem apenas novos `collectors/` + adaptar os
  `analyzers/` existentes ou criar novos — o `core/` não precisa mudar.
- O preço-teto (Graham/Bazin) usa o DY/LPA de um único ponto no tempo (não
  há histórico de dividendos/lucros coletado ainda) e o yield mínimo do
  Bazin é fixo em 6% (não calibrado por setor) — aproximações aceitáveis
  para o MVP2, não substituem análise fundamentalista completa.
- Documentos de `recommendations` gerados antes desta mudança usam o schema
  antigo (`action`: comprar/manter/evitar) — o dashboard detecta e pede para
  gerar uma nova recomendação em vez de quebrar, mas não há migração
  automática dos documentos antigos.
- Crescimento e FCF yield usam o dado de um único período do yfinance
  (`earningsGrowth`/`revenueGrowth`/`freeCashflow`), não o CAGR de 3/5/10
  anos da especificação (exigiria coletar demonstrativos financeiros
  multi-ano) — aproximação aceitável para o MVP2.
- EV/EBITDA e FCF costumam vir ausentes para bancos/seguradoras no yfinance
  (ex: ITUB4.SA) — o scoring já trata como ausente e redistribui o peso, sem
  quebrar a análise.
- **ROIC** usa o EBIT/alíquota efetiva/"Invested Capital" mais recentes de
  `.financials`/`.balance_sheet` (yfinance) — chamadas extras e mais frágeis
  que os campos de `.info`; isoladas (uma falha aqui não derruba a coleta),
  mas o dado pode vir ausente para tickers com cobertura pior.
- **Histórico dos múltiplos** só fica disponível a partir da 4ª análise
  fundamentalista do mesmo ativo (mín. 3 pontos passados) — em ativos
  recém-cadastrados, o peso é redistribuído entre os demais critérios.
- **Qualidade da gestão** (5% na especificação) não tem fonte de dado
  gratuita confiável e não foi implementada — peso redistribuído
  automaticamente entre os critérios disponíveis.
- **Cenário macro setorial** cobre só Petróleo/Gás (Brent + câmbio) e
  Bancos/Seguros (Selic) — os únicos com fonte gratuita confiável
  encontrada. Energia Elétrica, Holding Financeira e demais setores da
  especificação não recebem ajuste (ficam neutros) em vez de uma heurística
  sem lastro real.
- A série de câmbio do BCB/SGS (série 1) limita o endpoint `/dados/ultimos`
  a ~20 pontos (erro 400 acima disso, validado empiricamente) — por isso a
  janela de tendência do câmbio é de 20 dias úteis (~1 mês), mais curta que
  a do petróleo (3 meses via yfinance).
- A alocação-alvo é um número fixo por ativo (sem tolerância/banda de
  rebalanceamento) — qualquer alocação acima da meta, por menor que seja,
  já rebaixa uma categoria atrativa para "Aguardar".
- O "valor atual" de cada posição usa o preço mais recente da análise
  fundamentalista já coletada (não busca cotação em tempo real) — cai para
  o preço médio de compra se o ativo ainda não foi coletado/analisado.
- Registrar posição é opt-in e por ativo, um de cada vez, na página
  "Carteira" — não há import em lote (ex: CSV da corretora).
- As 4 fases do modelo de valuation mapeadas na análise comparativa com a
  especificação técnica estão implementadas. Gaps conhecidos e
  intencionalmente fora de escopo: CAGR real multi-ano (só há dado de um
  período), qualidade da gestão (sem fonte gratuita) e cobertura macro
  completa por setor (só Petróleo/Gás e Bancos/Seguros).
- O **Histórico de Análises** só passa a existir a partir desta versão —
  recomendações geradas antes dela não têm snapshot em `analysis_history`
  até serem regeneradas (não há migração/backfill automático).
- A paginação e os filtros da tela de Histórico operam sobre o snapshot
  mais recente de cada ativo (um registro por ativo) — não é uma busca no
  histórico completo de `recommendations`; ver comparação/gráfico de
  evolução ao longo do tempo é um próximo passo natural, não implementado
  ainda.
