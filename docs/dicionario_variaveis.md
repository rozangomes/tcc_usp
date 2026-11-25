# Dicionário de variáveis

## `data/processed/presidente_municipio_candidato` (.parquet / .csv)
Uma linha por **município × ano × turno × candidato a presidente**.

| Coluna | Significado |
|---|---|
| `ano` | Ano da eleição geral (1994–2026) |
| `turno` | 1 = primeiro turno; 2 = segundo turno |
| `regiao` | Região do IBGE (Norte, Nordeste, Centro-Oeste, Sudeste, Sul) |
| `sg_uf` | Sigla da UF |
| `cd_municipio_tse` | Código do município **no TSE** (5 dígitos; não é o código do IBGE) |
| `nm_municipio` | Nome do município (grafia do ano mais recente) |
| `capital` | 1 = capital da UF (inclui Brasília); 0 = não capital |
| `nr_candidato` | Número do candidato na urna |
| `nm_urna_candidato` | Nome de urna do candidato |
| `sg_partido` | Sigla do partido **no ano da eleição** |
| `votos` | Votos do candidato no município (soma das zonas) |
| `votos_validos_mun` | Total de votos válidos para presidente no município, naquele turno |
| `pct_votos` | `votos ÷ votos_validos_mun × 100` |

## `data/processed/presidente_municipio` (.parquet / .csv)
Uma linha por **município × ano × turno** (resumo).

| Coluna | Significado |
|---|---|
| `ano`, `turno`, `regiao`, `sg_uf`, `cd_municipio_tse`, `nm_municipio`, `capital`, `votos_validos_mun` | Iguais à tabela acima |
| `partido_mais_votado_mun` | Partido do candidato mais votado **no município** |
| `candidato_mais_votado_mun` | Nome de urna desse candidato |
| `pct_mais_votado_mun` | % de votos válidos desse candidato no município |
| `partido_mais_votado_brasil` | Partido do candidato mais votado **no Brasil** naquele ano e turno. No 2º turno, é o eleito. No 1º turno, é quem liderou (ex.: 2026, 1º turno = PL) |
| `candidato_mais_votado_brasil` | Nome de urna desse candidato |
| `pct_mais_votado_brasil` | % de votos válidos que esse candidato teve **no município** |

## `data/processed/municipios_tse_ibge` (.parquet / .csv)
Uma linha por **código de município do TSE** (5.572 linhas: os 5.571 municípios
atuais mais 1 código antigo — ver D11 em `docs/decisoes.md`).

| Coluna | Significado |
|---|---|
| `cd_municipio_tse` | Código do município no TSE (5 dígitos, texto) |
| `cd_municipio_ibge` | Código do município no IBGE (7 dígitos, texto) |
| `sg_uf` | Sigla da UF |
| `cd_uf_ibge` | Código da UF no IBGE (2 dígitos) |
| `nm_municipio_tse` | Nome do município segundo o TSE |
| `nm_municipio_ibge` | Nome atual do município segundo o IBGE |
| `regiao` | Região do IBGE |
| `capital` | 1 = capital da UF (inclui Brasília); 0 = não capital |
| `cd_mesorregiao`, `nm_mesorregiao` | Mesorregião geográfica do IBGE |
| `cd_microrregiao`, `nm_microrregiao` | Microrregião geográfica do IBGE |
| `correspondencia_manual` | 1 = ligação feita à mão (não consta da tabela oficial do TSE) |
| `obs` | Explicação, quando houver correspondência manual |
| `data_tabela_tse` | Data em que o TSE gerou a tabela oficial usada |

**Regra:** junte bases sempre pelo código (`cd_municipio_tse` ou
`cd_municipio_ibge`), nunca pelo nome do município.

## `data/processed/prefeito_municipio_candidato` (.parquet / .csv)
Uma linha por **município × ano × turno × candidato a prefeito**, só da
eleição **ordinária** (1996–2024).

| Coluna | Significado |
|---|---|
| `ano` | Ano da eleição municipal |
| `turno` | 1 ou 2 |
| `regiao`, `sg_uf`, `capital` | Como nas outras tabelas (capital vem do código IBGE) |
| `cd_municipio_tse`, `cd_municipio_ibge` | Códigos do município no TSE e no IBGE |
| `nm_municipio` | Nome atual do município segundo o IBGE |
| `nr_candidato`, `nm_urna_candidato` | Número e nome de urna |
| `sg_partido` | Sigla do partido **no ano da eleição** |
| `situacao_turno` | Resultado do candidato no turno: ELEITO, NÃO ELEITO, 2º TURNO |
| `apto` | 1 = votos válidos; 0 = votos anulados (registro negado/cassado) |
| `votos` | Votos do candidato (soma das zonas) |
| `votos_validos_mun` | Soma dos votos dos candidatos aptos no município e turno |
| `pct_votos` | `votos ÷ votos_validos_mun × 100` (0 para não aptos; vazio se o município não tem votos registrados) |

## `data/processed/prefeito_municipio` (.parquet / .csv)
Uma linha por **município × ano** de eleição municipal.

| Coluna | Significado |
|---|---|
| `ano`, `regiao`, `sg_uf`, `cd_municipio_tse`, `cd_municipio_ibge`, `nm_municipio`, `capital` | Como acima |
| `partido_eleito` | Partido do prefeito eleito (regra em D21) |
| `candidato_eleito` | Nome de urna do prefeito eleito |
| `fonte_eleito` | `ordinária` ou `suplementar` (quando a ordinária não teve eleito) |
| `data_eleicao_eleito` | Data da eleição (do turno) em que ele foi eleito |
| `pct_eleito_1t` | % de votos válidos do partido do eleito no 1º turno da ordinária (vazio se o eleito veio de suplementar) |
| `teve_2turno` | 1 = houve 2º turno na ordinária |
| `n_candidatos_1t` | Número de candidatos no 1º turno |
| `votos_validos_1t` | Votos válidos no 1º turno |
| `teve_suplementar` | 1 = houve eleição suplementar para prefeito no ciclo |
| `partido_eleito_ultima_suplementar` | Partido do vencedor da última suplementar do ciclo |
| `data_ultima_suplementar` | Data dessa suplementar |

## Tabelas manuais de partidos (`data/manual/`, versionadas no Git)

`partidos_siglas.csv`: uma linha por sigla (e número) de partido.

| Coluna | Significado |
|---|---|
| `sg_partido`, `nr_partido` | Sigla e número como aparecem no TSE |
| `ano_min`, `ano_max` | Anos em que a regra vale (só importa para "PSD", que nomeou dois partidos) |
| `linhagem` | O partido, juntando renomeações (nome da sigla mais recente) |
| `nome`, `obs` | Nome do partido e observações |

`partidos_eventos.csv`: uma linha por fusão ou incorporação.

| Coluna | Significado |
|---|---|
| `linhagem_origem` | Partido que deixou de existir |
| `linhagem_destino` | Partido que o absorveu ou que resultou da fusão |
| `ano_efeito` | Primeira eleição em que a mudança vale |
| `tipo` | fusão ou incorporação |
| `quando` | Ano do evento (aproximado quando indicado) |

## `data/processed/partidos_equivalencia` (.parquet / .csv)
Uma linha por **ano × sigla** que aparece nos bancos de presidente e prefeito.

| Coluna | Significado |
|---|---|
| `ano`, `sg_partido` | Eleição e sigla como aparecem nos dados |
| `linhagem` | O partido naquele ano (renomeações juntadas) |
| `linhagem_ano_mais_2` | O partido dois anos depois, aplicando fusões (use no pareamento t → t+2) |
| `linhagem_2026` | O partido equivalente hoje |
| `origem` | Em quais bancos a sigla aparece naquele ano |

## `data/processed/painel_prefeito_presidente` (.parquet / .csv)
**Painel A, prefeito → presidente.** Uma linha por **município × par de
eleições × candidato a presidente** (1º turno). Pares: 1996→1998, …,
2024→2026 (D16, D26).

| Coluna | Significado |
|---|---|
| `ano_prefeito`, `ano_presidente` | Ano do prefeito eleito (*t*) e da eleição para presidente (*t + 2*) |
| `cd_municipio_tse`, `cd_municipio_ibge`, `nm_municipio`, `sg_uf`, `regiao`, `capital` | Município (como nas outras tabelas) |
| `sg_partido_prefeito` | Sigla do partido do prefeito eleito em *t*, como no TSE |
| `fonte_eleito` | `ordinária` ou `suplementar` (D21) |
| `partido_prefeito` | Partido do prefeito levado a *t + 2* (linhagem com fusões; D23) |
| `nr_candidato`, `candidato_presidente` | Número e nome de urna do candidato a presidente |
| `sg_partido_presidente` | Sigla do candidato a presidente, como no TSE |
| `partido_presidente` | Linhagem do candidato a presidente em *t + 2* |
| `mesmo_partido` | 1 = o candidato é do partido do prefeito |
| `partido_prefeito_tem_candidato` | 1 = o partido do prefeito teve candidato a presidente em *t + 2* |
| `pct_votos_presidente` | % de votos válidos do candidato no município (1º turno) |
| `pct_presidente_eleicao_anterior` | % do mesmo partido no 1º turno para presidente em *t − 2* (D27; vazio se o partido não disputou) |
| `pct_dep_federal_anterior` | % do mesmo partido para deputado federal em *t − 2* (D38) |
| `pct_vereador_mesmo_ano` | % do partido do candidato para vereador em *t*, a mesma eleição do prefeito (D38; não usado nos modelos) |

## `data/processed/painel_presidente_prefeito` (.parquet / .csv)
**Painel B, presidente → prefeito.** Uma linha por **município × eleição
municipal × partido**. Pares: 1994→1996, …, 2022→2024 (D16, D26). Entram
os partidos com candidato a prefeito em *t + 2* ou na eleição municipal
anterior (D28).

| Coluna | Significado |
|---|---|
| `ano_presidente`, `ano_municipal` | Ano da eleição do presidente (*t*) e da eleição municipal (*t + 2*) |
| `partido_presidente_eleito`, `presidente_eleito` | Partido (levado a *t + 2*) e nome do presidente eleito em *t* |
| `cd_municipio_tse`, `cd_municipio_ibge`, `nm_municipio`, `sg_uf`, `regiao`, `capital` | Município |
| `partido` | Linhagem do partido em *t + 2* |
| `partido_do_presidente` | 1 = é o partido do presidente eleito em *t* |
| `teve_candidato` | 1 = o partido teve candidato a prefeito no município em *t + 2* |
| `n_candidatos_partido` | Número de candidatos do partido (normalmente 0 ou 1) |
| `pct_prefeito_1t` | % de votos válidos do partido no 1º turno para prefeito (0 se não teve candidato) |
| `elegeu_prefeito` | 1 = o partido elegeu o prefeito (regra da D21); vazio se não há eleito identificado |
| `pct_prefeito_eleicao_anterior` | % do partido no 1º turno para prefeito em *t − 2*, com fusões aplicadas (D27; vazio em 1996) |
| `pct_dep_federal_mesmo_ano` | % do partido para deputado federal em *t*, a mesma eleição do presidente (D38) |
| `pct_vereador_anterior` | % do partido para vereador na eleição municipal anterior (D38; vazio em 1996) |

## `data/processed/proporcional_municipio_partido` (.parquet / .csv)
Uma linha por **ano × cargo × município × partido** nas eleições
proporcionais (D36, D37).

| Coluna | Significado |
|---|---|
| `ano` | Ano da eleição |
| `cargo` | `deputado_federal`, `deputado_estadual` (inclui distrital no DF) ou `vereador` |
| `regiao`, `sg_uf`, `cd_municipio_tse`, `cd_municipio_ibge`, `nm_municipio`, `capital` | Município (como nas outras tabelas) |
| `nr_partido`, `sg_partido` | Número e sigla do partido **no ano da eleição** |
| `votos_nominais` | Votos válidos dados aos candidatos do partido |
| `votos_legenda` | Votos de legenda (só no número do partido); 0 em 1994 (D37) |
| `votos` | `votos_nominais + votos_legenda` |
| `votos_validos_mun` | Soma dos votos de todos os partidos para o cargo no município |
| `pct_votos` | `votos ÷ votos_validos_mun × 100` |

---

Os arquivos .csv usam `;` como separador e `,` como decimal (padrão do Excel em português).
