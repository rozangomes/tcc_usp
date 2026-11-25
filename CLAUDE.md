# TCC — Voto para presidente × voto municipal no Brasil

Contexto para o Claude Code. Responda sempre em português.

## Quem sou e o que é o projeto
- Aluno: Rozan Gomes (TCC USP). Orientador: Prof. Lucas Damasceno.
- Formado em administração, atuo em campanhas eleitorais desde 1997. Sei pouco de Python e de estatística, então explique o que cada passo faz em linguagem simples.
- Objetivo: um artigo publicável em ciência política, não um relatório de consultoria.

## Pergunta de pesquisa (definida na 1ª orientação, nov/2026)
**Qual é a relação entre o voto para presidente e o voto para prefeito?** Ela é testada nas duas direções:
1. **Presidente → prefeito:** ter o partido na Presidência favorece ou prejudica esse partido nas eleições municipais?
2. **Prefeito → presidente:** um município governado pelo partido X dá mais votos ao candidato a presidente do partido X na eleição seguinte?

Para cada direção: existe relação (H1) ou não (H0)? O sinal é positivo ou negativo?

Hipóteses secundárias:
- O efeito difere entre capitais e não capitais (usar uma dummy de capital).
- A relação ficou mais forte nos ciclos recentes (2022, 2024 e 2026).

⚠️ **Ponto em aberto:** a proposta original comparava presidente com **deputado federal**, só em Magé (RJ), de 2018 a 2026. Na reunião, o orientador falou de **prefeito**. Ainda falta confirmar com ele qual é o cargo. Enquanto isso, trabalhe primeiro no que serve aos dois cenários, que são os votos para presidente por município.

## Desenho
- Todos os municípios do Brasil, em série histórica desde a redemocratização.
- Dados agregados mostram associação, não causalidade. Fale em "associação" ou "relação", nunca em "efeito causal".
- Controles: capital (dummy), região e UF; opcionalmente renda per capita (IBGE).
- "Polarização": só usar se o conceito for bem definido, com autor e justificativa.

## Fontes de dados
- TSE, Portal de Dados Abertos: https://dadosabertos.tse.jus.br
- CEPESP Data (FGV): bases mais limpas, mas pode ainda não ter 2026.
- Sempre registrar no README a fonte, a URL e a data de download de cada arquivo.

## Regras do orientador sobre uso de IA
- O Claude pode escrever o código, raspar e montar os bancos e fazer os gráficos.
- O código precisa ser **bem comentado em português** e versionado no GitHub.
- **NÃO escreva o texto do artigo.** A redação é minha. Você pode revisar a lógica e apontar problemas, mas não deve redigir parágrafos do artigo.
- O artigo final terá uma nota declarando o uso de IA generativa nos dados, no código e nos gráficos.

## Estrutura do repositório
```
data/raw/        # arquivos originais do TSE/CEPESP — nunca editar
data/processed/  # bancos limpos gerados pelos scripts
src/             # scripts numerados: 01_baixar_presidente.py, 02_..., etc.
notebooks/       # exploração
output/          # figuras e tabelas
docs/            # dicionário de variáveis e registro de decisões
```
- Os dados brutos grandes não vão para o Git (usar `.gitignore`). Os scripts precisam conseguir baixá-los de novo.
- Registrar cada decisão metodológica em `docs/decisoes.md`.

## Armadilhas conhecidas
- O código de município do TSE é diferente do código do IBGE; é preciso uma tabela de correspondência.
- Vários municípios foram criados ao longo da série (por exemplo, em 1993, 1997 e 2001).
- Partidos mudaram de nome ou se fundiram (PFL→DEM→União Brasil, PMDB→MDB, PPB→PP, PR→PL, PSL+DEM→União). Montar uma tabela de equivalência.
- Turnos: usar o 1º turno por padrão e documentar a escolha.
- Coligações e federações: decidir se a unidade é o partido ou o campo político.
- As eleições municipais (2000, 2004…) e as gerais (1998, 2002…) não coincidem. Definir o pareamento, por exemplo prefeito eleito em t × presidente em t+2.

## Prazos
- **Mandar ao orientador, antes de 18/12/2026**, um retorno com os dados baixados, os primeiros gráficos e os testes simples.
- Plano detalhado: semana 1, votos presidenciais por município; semana 2, segundo cargo e montagem do painel; semana 3, gráficos, correlação e regressão simples com dummy de capital.
