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

# 6. Montar e conferir a equivalência de partidos
.venv\Scripts\python src\06_tabela_partidos.py

# 7. Montar os dois painéis (prefeito -> presidente e presidente -> prefeito)
.venv\Scripts\python src\07_montar_painel.py

# 8. Primeiros gráficos, correlações e regressões simples
.venv\Scripts\python src\08_analise_inicial.py

# 9. Tabelas resumidas que alimentam o dashboard interativo
.venv\Scripts\python src\09_dados_dashboard.py

# 10. (Opcional) Conferir o banco de prefeito com a Base dos Dados
#     Precisa de um projeto no Google Cloud; abre o navegador para login
.venv\Scripts\python src\10_conferir_base_dos_dados.py ID-DO-PROJETO

# 11. Baixar os votos por partido (deputados e vereador) e montar o banco
.venv\Scripts\python src\11_baixar_partido.py
.venv\Scripts\python src\12_montar_proporcional.py

# 12. Baixar os votos para governador e montar a tabela de eleitos
.venv\Scripts\python src\13_governador.py

# 13. Perfil do eleitorado (TSE; demorado, ~1 GB lido) e PIB municipal (IBGE)
.venv\Scripts\python src\14_perfil_eleitorado.py
.venv\Scripts\python src\15_pib_municipal.py
```

Depois dos passos 11 e 12, rode de novo os scripts 06 a 09 para atualizar a
tabela de partidos, os painéis, as regressões e os dados do painel.

Os dados brutos e processados **não** ficam no Git (são grandes); os scripts
acima os recriam. As tabelas feitas à mão (`data/manual/`, como a
equivalência de partidos) ficam no Git, assim como os gráficos e as tabelas
de `output/`.

## Scripts

| Script | O que faz | Saída |
|---|---|---|
| `src/01_baixar_presidente.py` | Baixa do TSE os votos para presidente por município e zona, 1994–2026 | `data/raw/presidente/` |
| `src/02_montar_presidente_municipio.py` | Soma as zonas, tira exterior e trânsito, calcula % por município, adiciona região e dummy de capital | `data/processed/presidente_municipio*.{parquet,csv}` |
| `src/03_tabela_tse_ibge.py` | Monta a correspondência entre código de município do TSE e do IBGE, com regiões geográficas e dummy de capital | `data/processed/municipios_tse_ibge.{parquet,csv}` |
| `src/04_baixar_prefeito.py` | Baixa do TSE os votos para prefeito por município e zona, 1996–2024 | `data/raw/prefeito/` |
| `src/05_montar_prefeito_municipio.py` | Banco de votos de prefeito (eleição ordinária) e prefeito eleito por município e ano | `data/processed/prefeito_municipio*.{parquet,csv}` |
| `src/06_tabela_partidos.py` | Confere as tabelas manuais de partidos contra os dados e gera a equivalência por ano (renomeações e fusões) | `data/processed/partidos_equivalencia.{parquet,csv}` |
| `src/07_montar_painel.py` | Junta presidente e prefeito nos dois painéis do pareamento t → t+2, por partido | `data/processed/painel_*.{parquet,csv}` |
| `src/08_analise_inicial.py` | Gráficos, correlações e regressões simples (com dummy de capital) dos dois painéis | `output/figuras/`, `output/tabelas/` |
| `src/09_dados_dashboard.py` | Resume os painéis e os resultados do 08 em tabelas pequenas para o dashboard (por recorte: Brasil, capitais, não capitais e regiões) | `output/dashboard/` |
| `src/10_conferir_base_dos_dados.py` | Confere o banco de prefeito com a Base dos Dados (municípios, votos e partido do eleito) | `output/tabelas/conferencia_base_dos_dados_*.csv` |
| `src/11_baixar_partido.py` | Baixa do TSE os votos por partido, município e zona (deputados 1994–2026, vereador 1996–2024) | `data/raw/partido/` |
| `src/12_montar_proporcional.py` | Banco de votos por partido (nominais + legenda) nas eleições proporcionais, por município | `data/processed/proporcional_municipio_partido.{parquet,csv}` |
| `src/13_governador.py` | Baixa do TSE os votos para governador (1994–2022) e monta o governador eleito por UF e ano | `data/raw/governador/`, `data/processed/governador_uf.{parquet,csv}` |
| `src/14_perfil_eleitorado.py` | Perfil do eleitorado por município e ano (sexo, idade, escolaridade), lido direto do TSE | `data/raw/perfil_eleitorado/`, `data/processed/perfil_eleitorado_municipio.{parquet,csv}` |
| `src/15_pib_municipal.py` | PIB per capita municipal (2002–2023) pela API do IBGE | `data/raw/ibge_pib/`, `data/processed/pib_municipal.{parquet,csv}` |
| `src/partidos.py` | Funções de linhagem e sucessão de partidos (usadas pelo 06 e pelo painel) | — |
| `src/utils_tse.py` | Funções compartilhadas (leitura parcial dos ZIPs do TSE, filtro por cargo, registro de downloads) | — |

O significado de cada coluna está em [docs/dicionario_variaveis.md](docs/dicionario_variaveis.md).
As decisões metodológicas estão em [docs/decisoes.md](docs/decisoes.md).

## Painel público

Versão pública (resultados preliminares) dos gráficos e testes:
**https://prefeito-presidente-tcc.vercel.app**

O site é a pasta `site/` (uma página HTML que lê `site/data/`, gerada pelo
script 09). Para publicar de novo depois de rodar os scripts:

```powershell
cd site
vercel deploy --prod
```

## Fontes de dados

| Dado | Fonte | URL | Data de download |
|---|---|---|---|
| Votação nominal por município e zona — Presidente, 1994, 2002–2026 (arquivo `_BR.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | 25/11/2026 |
| Votação nominal por município e zona — Presidente, 1998 (linhas de presidente do arquivo `_BRASIL.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_1998.zip` | 25/11/2026 |
| Votação nominal por município e zona — Prefeito, 1996–2024 (linhas de prefeito do arquivo `_BRASIL.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | 25/11/2026 |
| Códigos oficiais de UF e municípios segundo o TSE e o IBGE (tabela gerada pelo TSE em 22/11/2026) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip` | 25/11/2026 |
| Votação nominal por município e zona — Governador, 1994–2022 (linhas de governador do arquivo `_BRASIL.csv` de dentro do ZIP) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{ANO}.zip` | 25/11/2026 |
| Perfil do eleitorado por município e zona (sexo, faixa etária, escolaridade), 1994–2026 | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitorado/perfil_eleitorado_{ANO}.zip` | 25/11/2026 |
| PIB dos Municípios (tabela 5938), população estimada (6579) e Censos 2010 (202) e 2022 (4709) | IBGE, API SIDRA | `https://apisidra.ibge.gov.br/values/t/{TABELA}/...` (consultas exatas em `data/raw/ibge_pib/registro_downloads.csv`) | 25/11/2026 |
| Votação por partido, município e zona — deputado federal, estadual e distrital (1994–2026) e vereador (1996–2024) | TSE, Portal de Dados Abertos | `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_{ANO}.zip` | 25/11/2026 |
| Resultados por candidato e município, prefeito 1996–2024 (só para conferência) | Base dos Dados, tabela `basedosdados.br_tse_eleicoes.resultados_candidato_municipio` (Google BigQuery) | https://basedosdados.org/dataset/br-tse-eleicoes | 25/11/2026 |
| Lista de municípios com região, mesorregião e microrregião | IBGE, API de Localidades | `https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado` | 25/11/2026 |

O registro completo de cada arquivo (URL, data e hora, tamanho e código SHA-256)
é gerado automaticamente em `registro_downloads.csv` dentro de cada pasta de
`data/raw/` (`presidente/`, `prefeito/`, `municipios/`, `partido/` e `governador/`).

## Uso de IA generativa

O código, a montagem dos bancos e os gráficos foram feitos com auxílio do
Claude Code (Anthropic), sob supervisão do autor. A redação do artigo é do autor.
