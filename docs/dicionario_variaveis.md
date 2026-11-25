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

Os arquivos .csv usam `;` como separador e `,` como decimal (padrão do Excel em português).
