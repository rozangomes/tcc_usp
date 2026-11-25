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

## Observações sobre a qualidade dos dados (25/11/2026)
- Totais por candidato conferidos com os resultados oficiais conhecidos de
  2002 a 2022: idênticos ao voto.
- 1994: diferença pequena em relação ao resultado oficial divulgado (FHC
  34.350.217 no arquivo × 34.314.961 divulgado; ≈0,1%). O arquivo de 1994 também
  não traz votos do exterior. Manter como limitação.
- 2026: os totais vêm do arquivo do TSE gerado em 25/11/2026; ainda não
  foram conferidos com a totalização oficial publicada.
- Número de municípios cresce ao longo da série (5.019 em 1994; 5.571 em
  2026), por causa da criação de municípios. Tratar no painel.
