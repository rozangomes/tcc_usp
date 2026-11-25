# TCC — Voto para presidente × voto municipal no Brasil

Repositório de dados e código do TCC de Rozan Gomes (Pós-graduação em Marketing
Político e Campanhas Eleitorais, USP). Orientador: Prof. Lucas Damasceno.

## Como reproduzir

Pré-requisito: Python 3.12 instalado.

```powershell
# 1. Criar o ambiente e instalar as bibliotecas (só na primeira vez)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. Baixar os votos para presidente do TSE (≈ 2 min)
.venv\Scripts\python src\01_baixar_presidente.py

# 3. Montar o banco por município
.venv\Scripts\python src\02_montar_presidente_municipio.py

# 4. Montar a tabela de correspondência TSE × IBGE
.venv\Scripts\python src\03_tabela_tse_ibge.py

# 5. Baixar os votos para prefeito (≈ 1 min) e montar o banco
.venv\Scripts\python src\04_baixar_prefeito.py
.venv\Scripts\python src\05_montar_prefeito_municipio.py
```

Os dados brutos e processados **não** ficam no Git (são grandes); os scripts
acima os recriam.

## Scripts

| Script | O que faz | Saída |
|---|---|---|
| `src/01_baixar_presidente.py` | Baixa do TSE os votos para presidente por município e zona, 1994–2026 | `data/raw/presidente/` |
| `src/02_montar_presidente_municipio.py` | Soma as zonas, tira exterior e trânsito, calcula % por município, adiciona região e dummy de capital | `data/processed/presidente_municipio*.{parquet,csv}` |
| `src/03_tabela_tse_ibge.py` | Monta a correspondência entre código de município do TSE e do IBGE, com regiões geográficas e dummy de capital | `data/processed/municipios_tse_ibge.{parquet,csv}` |
| `src/04_baixar_prefeito.py` | Baixa do TSE os votos para prefeito por município e zona, 1996–2024 | `data/raw/prefeito/` |
| `src/05_montar_prefeito_municipio.py` | Banco de votos de prefeito (eleição ordinária) e prefeito eleito por município e ano | `data/processed/prefeito_municipio*.{parquet,csv}` |
| `src/utils_tse.py` | Funções compartilhadas (leitura parcial dos ZIPs do TSE, filtro por cargo, registro de downloads) | — |

O significado de cada coluna está em [docs/dicionario_variaveis.md](docs/dicionario_variaveis.md).
As decisões metodológicas estão em [docs/decisoes.md](docs/decisoes.md).

## Fontes de dados

| Dado | Fonte | URL | Data de download |
|---|---|---|---|
| Votação nominal por município e zona — Presidente, 1994, 2002–2026 (arquivo `_BR.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | 25/11/2026 |
| Votação nominal por município e zona — Presidente, 1998 (linhas de presidente do arquivo `_BRASIL.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip` | 25/11/2026 |
| Votação nominal por município e zona — Prefeito, 1996–2024 (linhas de prefeito do arquivo `_BRASIL.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | 25/11/2026 |
| Códigos oficiais de UF e municípios segundo o TSE e o IBGE (tabela gerada pelo TSE em 22/11/2026) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip` | 25/11/2026 |
| Lista de municípios com região, mesorregião e microrregião | IBGE, API de Localidades | `https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado` | 25/11/2026 |

O registro completo de cada arquivo (URL, data e hora, tamanho e código SHA-256)
é gerado automaticamente em `registro_downloads.csv` dentro de cada pasta de
`data/raw/` (`presidente/`, `prefeito/` e `municipios/`).

## Uso de IA generativa

O código, a montagem dos bancos e os gráficos foram feitos com auxílio do
Claude Code (Anthropic), sob supervisão do autor. A redação do artigo é do autor.
