# Registro de decisões metodológicas

Cada decisão tem data, o que foi decidido, por quê e onde está no código.
Decisões marcadas como **[provisória]** devem ser confirmadas com o orientador.

---

## 25/11/2026 — Votos para presidente por município

### D1. A série municipal de presidente começa em 1994, não em 1989
- **O quê:** o banco cobre 1994, 1998, 2002, 2006, 2010, 2014, 2018, 2022 e 2026.
- **Por quê:** o TSE só publica a eleição de 1989 por UF (pacote
  `resultados-1989`: "Detalhe de apuração por UF" e "Votação nominal por UF").
  Não há votação de 1989 por município no Portal de Dados Abertos.
- **Pendência:** verificar se o CEPESP Data ou outra fonte tem 1989 por município.

### D2. Fonte: arquivo `votacao_candidato_munzona` do TSE
- **O quê:** usamos o arquivo de votação nominal por município e zona.
- **Como:** de cada ZIP baixamos só o arquivo interno `_BR.csv`, que traz
  apenas o cargo de abrangência nacional (presidente). Isso evita baixar
  ~2,4 GB. O arquivo é salvo sem nenhuma alteração.
- **Código:** `src/01_baixar_presidente.py`

### D3. Tratamento especial de 1998
- **O quê:** em 1998 não há `_BR.csv`, e os arquivos por UF não trazem
  presidente. Lemos o `_BRASIL.csv` (todos os cargos) e guardamos só as
  linhas com `DS_CARGO = Presidente`.
- **Além disso:** em 1998 a coluna `QT_VOTOS_NOMINAIS` vem zerada; os votos
  estão em `QT_VOTOS_NOMINAIS_VALIDOS`. Usamos essa coluna para 1998.
  Conferência: FHC 35.936.382 no arquivo × 35.936.540 no resultado oficial
  (diferença de 0,0004%).
- **Código:** `01_baixar_presidente.py` (filtro) e
  `02_montar_presidente_municipio.py`, função `ler_ano` (coluna de votos).

### D4. Exclusão de votos do exterior e em trânsito
- **O quê:** retiramos do banco municipal os votos com UF `ZZ` (exterior),
  UF `VT` e `ST_VOTO_EM_TRANSITO = S` (voto em trânsito, 2010 e 2014).
- **Por quê:** esses votos não pertencem ao eleitorado de nenhum município.
  São no máximo 0,3% do total de cada turno (ver saída do script 02).
- **Observação:** a partir de 2018 o TSE não marca mais o voto em trânsito
  nesse arquivo, então ele fica somado ao município onde foi dado. O volume
  é pequeno, mas fica registrado como limitação.

### D5. Agregação por município
- **O quê:** somamos as zonas eleitorais para ter uma linha por município ×
  ano × turno × candidato.
- **Unidade:** código de município do **TSE** (`cd_municipio_tse`). A
  correspondência com o código do IBGE fica para um script posterior.

### D6. Porcentagem sobre votos válidos
- **O quê:** `pct_votos` = votos do candidato ÷ soma dos votos de todos os
  candidatos no município × 100.
- **Por quê:** para presidente não existe voto de legenda, então a soma dos
  votos nominais é igual aos votos válidos (excluídos brancos e nulos).

### D7. Os dois turnos ficam no banco [provisória]
- **O quê:** o banco guarda o 1º e o 2º turno (coluna `turno`). Por padrão,
  as análises usarão o **1º turno**, como diz o plano do projeto.
- **Por quê guardar o 2º:** permite testes de robustez. Em 1994 e 1998 só
  houve 1º turno.

### D8. Dummy de capital e região
- **O quê:** `capital = 1` para as 27 capitais (incluindo Brasília),
  identificadas pelo nome do município dentro da UF; `regiao` segue a divisão
  do IBGE pela UF. O script confere que há exatamente 27 capitais por ano.

### D9. Siglas de partido como no original [provisória]
- **O quê:** por enquanto a sigla é a do ano da eleição (ex.: Bolsonaro = PSL
  em 2018 e PL em 2022). A tabela de equivalência de partidos
  (PFL→DEM→União etc.) será feita depois.

---

## 25/11/2026 — Correspondência de códigos TSE × IBGE

### D10. Fonte: tabela oficial do TSE, conferida com o IBGE
- **O quê:** a correspondência vem da tabela "Códigos oficiais de UF e
  municípios segundo o TSE e o IBGE", publicada pelo próprio TSE (5.571
  municípios). Nome atual, região, mesorregião e microrregião vêm da API de
  Localidades do IBGE.
- **Conferências feitas (todas passaram):** todo código IBGE existe na lista
  do IBGE; a UF é igual nas duas fontes; a relação é um-para-um; as 27
  capitais batem pelo nome; todos os 5.572 códigos TSE do banco de presidente
  (1994–2026) têm par.
- **Por que não usar tabelas feitas por terceiros:** comparamos com uma tabela
  pública muito usada (github.com/betafcc/Municipios-Brasileiros-TSE). Ela
  difere da oficial em 7 municípios (5 na BA, 2 em SC), em que os códigos IBGE
  de vizinhos em ordem alfabética estão trocados (ex.: Lagoa Real ↔ Lajedo do
  Tabocal). Na tabela oficial, o nome do TSE e o nome do IBGE coincidem nesses
  7 casos; o erro é da tabela de terceiros.
- **Nomes diferentes:** 13 municípios têm grafia ou nome diferente no TSE e no
  IBGE (ex.: "São Thomé das Letras" × "São Tomé das Letras"; "Governador
  Edison Lobão" × "Ribeirãozinho do Maranhão"). O código é o mesmo; por isso
  sempre juntamos bases **pelo código, nunca pelo nome**.
- **Código:** `src/03_tabela_tse_ibge.py`

### D11. Boa Esperança do Norte (MT): correspondência manual
- **O quê:** o código TSE 91065 (usado só em 2002) não está na tabela oficial.
  Foi ligado à mão ao IBGE 5101837, o mesmo do município recriado que votou
  em 2026 com o código TSE 73709. Marcado com `correspondencia_manual = 1`.
- **Por quê:** é o mesmo município, criado em 2000, extinto depois de 2002
  (território voltou a Sorriso e Nova Ubiratã) e recriado. Tem 906 votos
  válidos em 2002; o impacto é desprezível, mas o caso fica rastreável.
- **Atenção no painel:** nesse caso, um código IBGE tem dois códigos TSE.
  Ao juntar por código IBGE, os dois anos não se misturam (2002 e 2026).

### D12. Dummy de capital pelo código IBGE
- **O quê:** na tabela TSE × IBGE, `capital` é definida pelo código IBGE das
  27 capitais. Conferido: dá exatamente o mesmo resultado que a definição
  pelo nome usada no script 02.

---

## 25/11/2026 — Definições do desenho (decididas pelo aluno)

### D13. O segundo cargo é prefeito
- **O quê:** a comparação é presidente × **prefeito**, em todos os municípios
  e em todas as eleições municipais com dados no TSE (1996–2024). São usados
  os votos de todos os candidatos a prefeito, não só dos eleitos.
- **Substitui:** a proposta original (presidente × deputado federal, só em
  Magé, 2018–2026).

### D14. A série começa em 1994 (confirma D1)
- **O quê:** aceito que a série municipal de presidente começa em 1994, porque
  o TSE não publica 1989 por município.

### D15. Unidade de análise: o partido
- **O quê:** a análise é feita por **partido**, com todos os partidos, e não
  por campo político (esquerda/direita).
- **Consequência:** coligações e federações não são somadas; conta o partido
  do candidato. Mudanças de nome e fusões de partido serão tratadas por uma
  tabela de equivalência.

### D16. Pareamento das eleições
- **Prefeito → presidente:** partido do prefeito eleito em *t* × voto do
  candidato a presidente desse partido no município em *t + 2*
  (1996→1998, 2000→2002, …, 2024→2026).
- **Presidente → prefeito:** partido do presidente eleito em *t* × desempenho
  desse partido nas eleições municipais de *t + 2*
  (1994→1996, 1998→2000, …, 2022→2024).
- **Limitação aceita:** desde 1994 só três partidos (ou quatro, contando a
  troca PSL→PL) chegaram à Presidência: PSDB, PT e PSL/PL.

### D17. Evitar o conceito de "polarização"
- **O quê:** o trabalho evita o termo. Se ele for usado, o aluno define qual
  conceito de polarização, com autor e justificativa.

---

## 25/11/2026 — Votos para prefeito por município

### D18. Fonte e filtro dos dados de prefeito
- **O quê:** de cada ZIP `votacao_candidato_munzona_{ANO}` (1996–2024) lemos o
  arquivo nacional `_BRASIL.csv` e guardamos só as linhas com
  `DS_CARGO = Prefeito`, copiadas sem alteração. As linhas de vereador são
  descartadas.
- **Código:** `src/04_baixar_prefeito.py` (usa `src/utils_tse.py`).

### D19. Coluna de votos e votos anulados
- **2000:** `QT_VOTOS_NOMINAIS` vem zerada; usamos `QT_VOTOS_NOMINAIS_VALIDOS`
  (mesmo problema de 1998 para presidente).
- **Votos anulados** (candidato com registro negado/cassado) não contam como
  válidos. Até 2012, isso é identificado pela situação da candidatura
  (INAPTO, INDEFERIDO, INDEFERIDO POR IMPUGNAÇÃO, CASSAÇÃO DO REGISTRO,
  CANCELAMENTO). De 2016 em diante, segue-se a marcação do próprio TSE em
  `NM_TIPO_DESTINACAO_VOTOS` (Válido × Anulado × Anulado sub judice).
- **Peso:** os votos anulados no 1º turno vão de 0 a 1,0% do total
  (o máximo foi em 2024, com 1,14 milhão).
- **Limitação:** em 2000, candidatos *sub judice* (5 milhões de votos) foram
  mantidos como válidos, porque a situação final deles não está no arquivo.

### D20. Só a eleição ordinária entra no banco de votos
- **O quê:** o banco de votos (`prefeito_municipio_candidato`) usa só a
  eleição ordinária de outubro (1º e 2º turnos). As eleições suplementares
  (chamadas "extraordinárias" no TSE a partir de 2016) ficam de fora.
- **Por quê:** elas acontecem meses ou anos depois, em outro contexto, e não
  são comparáveis à ordinária.
- **Detalhe técnico:** a partir de 2016 o TSE dá um código de eleição diferente
  a cada turno da ordinária, e Macapá (2020) teve códigos próprios, porque a
  eleição foi adiada pelo apagão. A ordinária é agrupada por município e ano,
  não pelo código.

### D21. Quem é o prefeito eleito
- **Regra:** é o candidato com situação "ELEITO" no último turno da eleição
  ordinária. Se a ordinária não teve eleito, porque a eleição foi anulada,
  usamos o eleito da **primeira** suplementar do ciclo
  (`fonte_eleito = "suplementar"`): 1 caso em 2008, 1 em 2012, 43 em 2016,
  70 em 2020 e 27 em 2024.
- **Robustez:** o banco informa se houve suplementar no ciclo
  (`teve_suplementar`) e o partido do vencedor da última suplementar.
  O partido mudou depois da suplementar em 40 (2004), 112 (2008), 85 (2012),
  101 (2016), 24 (2020) e 10 (2024) municípios. Esses casos podem ser
  excluídos num teste de robustez.
- **Sem eleito identificado:** 20 casos em ~44 mil (0,05%), listados na saída
  do script 05. Ficam sem partido.

### D22. Lacunas nos dados do TSE para prefeito
- **1996:** faltam ~104 municípios na base do TSE (74 no Maranhão, 19 no Pará
  e outros 11). Os dados existentes cobrem 5.408 municípios. Limitação a
  declarar; não há outra fonte oficial no Portal do TSE.
- **Fernando de Noronha (PE)** não tem prefeito (é distrito estadual) e não
  aparece em nenhum ano. **DF** também não tem prefeito.
- **Municípios criados depois** (ex.: Mojuí dos Campos, Paraíso das Águas,
  Pescaria Brava, Balneário Rincão, Pinto Bandeira, instalados em 2013)
  só aparecem a partir de quando passam a votar.
- **Sem votos registrados:** Bom Jesus de Goiás (GO, 2012) e Brejo Alegre
  (SP, 2024) têm zero votos válidos na ordinária no arquivo do TSE; ficam com
  `pct_votos` vazio.
- **2024:** 8 municípios não têm a eleição ordinária no arquivo (Anajatuba,
  Guimarães e Santana do Maranhão/MA; Barra dos Coqueiros, Cedro de São João e
  Nossa Senhora do Socorro/SE; Iporá e Americano do Brasil/GO).

### Conferência com fatos conhecidos (25/11/2026)
- Partido do prefeito eleito em São Paulo, Rio de Janeiro e Belo Horizonte,
  1996–2024: todos corretos (ex.: São Paulo = PPB, PT, PSDB, DEM, PT, PSDB,
  PSDB, MDB).
- Prefeitos por partido em 2024: PSD 890, MDB 862, PP 750, União 591, PL 517,
  em linha com o noticiado após a eleição.

---

## 25/11/2026 — Equivalência de partidos

### D23. Duas camadas: linhagem (renomeações) e fusões por data
- **Linhagem:** siglas que são o mesmo partido com outro nome recebem um
  único nome, o da sigla mais recente (ex.: PMDB/MDB → MDB; PFL/DEM → DEM;
  PRN/PTC/AGIR → AGIR; PMB/DEMOCRATA → DEMOCRATA).
  Tabela manual: `data/manual/partidos_siglas.csv`.
- **Fusões e incorporações:** só valem para eleições **posteriores** ao
  evento. Ex.: DEM e PSL → União Brasil a partir de 2022. Em 2018, DEM e PSL
  continuam sendo partidos diferentes.
  Tabela manual: `data/manual/partidos_eventos.csv` (15 eventos).
- **Por quê:** se toda sigla fosse trocada pelo nome atual em todos os anos,
  um prefeito do DEM eleito em 2016 seria contado como "do mesmo partido"
  que Bolsonaro (PSL) em 2018, o que é falso.
- **No pareamento t → t+2:** o partido em *t* é levado à linhagem que ele
  tinha em *t + 2* (coluna `linhagem_ano_mais_2`). Ex.: prefeito do PSL
  eleito em 2020 → União Brasil em 2022.
- **Código:** `src/partidos.py` (funções) e `src/06_tabela_partidos.py`.

### D24. Fontes e conferência das equivalências
- As renomeações e fusões foram listadas a partir do histórico dos partidos e
  **conferidas com os próprios dados do TSE**: (i) número do partido;
  (ii) a sigla absorvida não aparece em nenhuma eleição ordinária depois da
  fusão (o script 06 testa isso para os 15 eventos).
- Os casos recentes foram conferidos pelas datas de criação e registro dos
  partidos: Democrata (nº 35) tem as mesmas datas do PMB, Mobiliza (nº 33) as
  mesmas do PMN, e o Partido Missão (nº 14) é um partido novo (registro em
  nov/2025), sem relação com o antigo PTB.
- **Limitação:** as páginas oficiais de partidos do TSE bloquearam o acesso
  automático (erro 403). As datas exatas dos eventos devem ser conferidas
  manualmente em https://www.tse.jus.br/partidos antes da versão final. Para
  o painel, só importa **entre quais eleições** cada evento ocorreu, e isso
  está confirmado pelos dados.
- **Data incerta:** a incorporação do PAN ao PTB (2006 ou 2007). Não afeta os
  pares com presidente, porque nenhum dos dois teve candidato em 2006.

### D25. Particularidades encontradas nos dados do TSE
- **Siglas "atualizadas":** nas eleições **suplementares**, o TSE às vezes
  registra a sigla atual (ex.: "UNIÃO" numa suplementar do ciclo 2020,
  realizada depois de 2022). Nas eleições ordinárias, as siglas são sempre as
  da época. A tabela de linhagem trata os dois casos.
- **Mesma sigla, partidos diferentes:** "PSD" nomeou o PSD de 1987–2003
  (nº 41, incorporado ao PTB) e o PSD criado em 2011 (nº 55). Distinguidos
  pelo ano.
- **Números reaproveitados:** União (44, antigo PRP), PRD (25, antigo DEM),
  Missão (14, antigo PTB) e Podemos (20, antigo PSC) usam números de partidos
  extintos. Por isso a ligação é feita pela sigla e pela data, nunca só pelo
  número.
- **Federações (2022 em diante)** não são tratadas como fusão: pela D15, a
  unidade é o partido.

### Observação para a análise (não é decisão)
- Na direção prefeito → presidente, o número de municípios em que o partido
  do prefeito teve candidato a presidente dois anos depois varia de 1.174
  (1996→1998) a 2.547 (2016→2018). Casos que chamam atenção:
  - 2016→2018: só 31 prefeitos do PSL (partido de Bolsonaro em 2018).
  - 2020→2022: os prefeitos do PSL e do DEM eleitos em 2020 viram União
    Brasil em 2022 (candidata Soraya Thronicke), e não PL (Bolsonaro).
    Isso decorre da D15, que toma o partido como unidade de análise.

---

## 25/11/2026 — Montagem do painel

### D26. Dois painéis, um para cada direção da pergunta
- **Painel A (prefeito → presidente):** uma linha por município × par de
  eleições × candidato a presidente no 1º turno de *t + 2*. A variável-chave
  `mesmo_partido` vale 1 quando o candidato é do partido do prefeito eleito
  em *t*. O partido do prefeito é levado a *t + 2* com as fusões (D23).
- **Painel B (presidente → prefeito):** uma linha por município × eleição
  municipal × partido. A variável-chave `partido_do_presidente` vale 1 para
  o partido do presidente eleito em *t*. Os resultados são o % no 1º turno
  para prefeito e se o partido elegeu o prefeito.
- **Por quê:** com uma linha por partido, cada partido é comparado com ele
  mesmo (onde tem prefeito × onde não tem; quando está na Presidência ×
  quando não está), como pede a D15.
- **Código:** `src/07_montar_painel.py`.

### D27. Ponto de partida: a eleição anterior do mesmo cargo
- Cada painel traz o % do mesmo partido na eleição **anterior do mesmo
  cargo** (presidente em *t − 2* no painel A; prefeito em *t − 2* no painel
  B), com o partido levado ao ano de comparação pelas fusões.
- **Por quê:** permite comparar a variação, e não só o nível. Um partido
  forte num município tende a ser forte nos dois cargos, e o ponto de
  partida ajuda a separar isso da relação entre os cargos.
- **Regra dos vazios:** fica 0% se o partido disputou a eleição anterior mas
  não teve votos no município (ou não teve candidato a prefeito ali). Fica
  vazio se o partido não disputou a Presidência em *t − 2*, se não há dados
  (prefeito em 1992) ou se o município ainda não existia.

### D28. Partidos sem candidato no painel B
- No painel B entram os partidos que tiveram candidato a prefeito no
  município em *t + 2* **ou** na eleição municipal anterior. Quem não teve
  candidato fica com 0% e `teve_candidato` = 0.
- **Por quê:** não lançar candidato também é um resultado (o partido pode
  ter recuado ou apoiado outro). A análise pode usar todas as linhas ou só
  as com candidato. Essa escolha fica para a análise.
- **Limitação:** em 1996 não há eleição anterior nos dados (1992), então só
  entram os partidos com candidato em 1996.

### Observações para a análise (não são decisões)
- **Presidente "eleito em t" × presidente no cargo em t + 2:** em dois
  casos eles não coincidem. Em 2016, Dilma (PT) já tinha sido afastada, e
  Temer (MDB) governava durante a eleição municipal. Em 2020, Bolsonaro já
  tinha saído do PSL (nov/2019) e estava sem partido. O painel segue a D16
  (partido do presidente eleito em *t*). Vale discutir com o orientador se
  esses dois ciclos devem ser tratados de outra forma.
- **Comparação descritiva inicial:** a saída do script 07 mostra, para cada
  candidato a presidente, o % médio onde o prefeito é do seu partido × nos
  demais municípios. É só uma média, sem controles, e não indica causa.

---

## 25/11/2026 — Primeiros gráficos e testes simples

### D29. Candidatos incluídos na direção A
- Entram os candidatos a presidente cujo partido elegeu **pelo menos 30
  prefeitos** em *t* e que tiveram **média de pelo menos 5%** dos votos nos
  municípios em *t + 2* (23 candidatos, 1998–2026).
- **Por quê:** com poucos prefeitos, a média oscila muito; candidatos com
  menos de 5% quase não variam entre municípios.
- **Atenção:** Bolsonaro 2018 entra com só 31 prefeitos do PSL.

### D30. Especificação das regressões simples
- **Método:** mínimos quadrados ordinários (MQO), com erros-padrão agrupados
  por município (o mesmo município aparece em vários anos e várias linhas).
- **Modelo A:** % do candidato a presidente no município ~ `mesmo_partido`
  + `mesmo_partido × capital` + `mesmo_partido × recente` + capital, com
  efeito fixo de candidato × UF (cada candidato é comparado com ele mesmo
  dentro da mesma UF). **A2** acrescenta o % do partido na eleição
  presidencial anterior (D27); por isso perde os candidatos cujo partido não
  disputou a Presidência quatro anos antes.
- **Modelo B:** % do partido para prefeito no 1º turno (e, à parte,
  "elegeu o prefeito", 0/1) ~ `partido_do_presidente` + interações com
  capital e com ciclo recente + capital, com efeito fixo de partido × UF e de
  ano. **B2** acrescenta o % do partido na eleição municipal anterior e, por
  isso, perde 1996.
- **Ciclos recentes:** 2022 e 2026 para presidente (modelo A) e 2024 para
  prefeito (modelo B), seguindo a hipótese secundária do CLAUDE.md.
- **Limites:** são testes iniciais, sem renda per capita e sem controles do
  contexto de cada eleição. No modelo B, a variação vem de poucos partidos
  (PSDB, PT e PSL). Os resultados mostram associação, não causalidade.
- **Código:** `src/08_analise_inicial.py`.

### D31. Gráficos
- Cores da paleta de referência (validada para daltonismo): azul `#2a78d6`
  e laranja `#eb6834`. Os gráficos não usam o termo "polarização" (D17).
- Gráficos e tabelas ficam em `output/` e **vão para o Git** (são pequenos e
  o orientador pode vê-los direto no GitHub).

### D32. Dashboard interativo
- Um dashboard no Claude (artefato privado do aluno) mostra os dois
  gráficos com filtro de recorte (Brasil, capitais, não capitais e cada
  região), as correlações e as regressões.
- Ele lê só as tabelas resumidas de `output/dashboard/` (script 09), não os
  bancos completos. Quando os scripts 07 a 09 forem rodados de novo, os
  arquivos do dashboard precisam ser enviados de novo.
- Nos recortes por região e capital, a seleção de candidatos é a mesma do
  Brasil (D29); por isso alguns candidatos têm poucos ou nenhum prefeito do
  partido no recorte.

### D33. Painel público na Vercel
- **Decisão do aluno (25/11/2026):** publicar uma versão pública do painel,
  marcada como **resultados preliminares**, em
  https://prefeito-presidente-tcc.vercel.app (projeto
  `prefeito-presidente-tcc` na conta Vercel do aluno).
- É uma página independente (`site/index.html`, com a biblioteca d3), que
  lê as mesmas tabelas resumidas do dashboard (cópia em `site/data/`, feita
  pelo script 09). Não contém os bancos completos.
- O aviso de resultados preliminares deve sair só depois da revisão do
  orientador e das conferências pendentes (totais de 2026, datas de fusão).

---

## Observações sobre a qualidade dos dados (25/11/2026)
- Totais por candidato conferidos com os resultados oficiais conhecidos de
  2002 a 2022: idênticos ao voto.
- 1994: diferença pequena em relação ao resultado oficial divulgado (FHC
  34.350.217 no arquivo × 34.314.961 divulgado; ≈0,1%). O arquivo de 1994 também
  não traz votos do exterior. Manter como limitação.
- 2026: os totais vêm do arquivo do TSE gerado em 25/11/2026; ainda não
  foram conferidos com a totalização oficial publicada.
- Número de municípios cresce ao longo da série (5.019 em 1994; 5.571 em
  2026), por causa da criação de municípios. No painel, cada par usa os
  municípios presentes nas duas eleições (perdem-se de 0 a 6 por par).
