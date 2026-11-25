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

---

Os arquivos .csv usam `;` como separador e `,` como decimal (padrão do Excel em português).
