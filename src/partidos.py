"""
partidos.py
===========

Funções para tratar mudanças de nome e fusões de partidos ao longo do tempo.
Este arquivo não é rodado sozinho; os scripts numerados o "importam".

A IDEIA EM DUAS PARTES
----------------------
1) LINHAGEM (renomeações): o mesmo partido com nomes diferentes recebe um
   único nome, o da sigla mais recente. Exemplos:
       PMDB e MDB            -> linhagem "MDB"
       PFL e DEM             -> linhagem "DEM"
       PRN, PTC e AGIR       -> linhagem "AGIR"
   Tabela: data/manual/partidos_siglas.csv

2) FUSÕES E INCORPORAÇÕES (por data): quando dois partidos se juntam, a
   ligação só vale para eleições DEPOIS da fusão. Exemplo:
       DEM e PSL -> UNIÃO, a partir da eleição de 2022.
   Assim, em 2018 o DEM e o PSL continuam sendo partidos diferentes (o que
   é correto: Bolsonaro era do PSL, não do DEM). Mas um prefeito do DEM
   eleito em 2020 é ligado ao União Brasil em 2022.
   Tabela: data/manual/partidos_eventos.csv

FUNÇÕES PRINCIPAIS
------------------
- linhagem(sigla, ano): a linhagem de uma sigla numa eleição.
- sucessor(linhagem, ano_origem, ano_destino): em qual linhagem um partido
  de `ano_origem` estava em `ano_destino`, aplicando as fusões ocorridas
  entre as duas eleições. Usado no pareamento t -> t+2.
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARQ_SIGLAS = RAIZ / "data" / "manual" / "partidos_siglas.csv"
ARQ_EVENTOS = RAIZ / "data" / "manual" / "partidos_eventos.csv"


def carregar_tabelas():
    """Lê as duas tabelas manuais (texto UTF-8, separador ';')."""
    siglas = pd.read_csv(ARQ_SIGLAS, sep=";", dtype=str, encoding="utf-8",
                         keep_default_na=False)
    siglas["ano_min"] = siglas["ano_min"].astype(int)
    siglas["ano_max"] = siglas["ano_max"].astype(int)
    eventos = pd.read_csv(ARQ_EVENTOS, sep=";", dtype=str, encoding="utf-8",
                          keep_default_na=False)
    eventos["ano_efeito"] = eventos["ano_efeito"].astype(int)
    return siglas, eventos


_SIGLAS, _EVENTOS = carregar_tabelas()


def linhagem(sigla: str, ano: int):
    """
    Linhagem de uma sigla numa eleição. A coluna de anos só importa para a
    sigla "PSD", que nomeou dois partidos diferentes (o PSD de 1987-2003 e o
    PSD criado em 2011). Devolve None se a sigla não estiver na tabela.
    """
    if sigla is None or pd.isna(sigla):
        return None
    achou = _SIGLAS[(_SIGLAS["sg_partido"] == sigla)
                    & (_SIGLAS["ano_min"] <= ano) & (_SIGLAS["ano_max"] >= ano)]
    linhagens = achou["linhagem"].unique()
    if len(linhagens) == 0:
        return None
    if len(linhagens) > 1:
        raise ValueError(f"Sigla {sigla} em {ano} tem mais de uma linhagem: {linhagens}")
    return linhagens[0]


def sucessor(lin: str, ano_origem: int, ano_destino: int):
    """
    Segue as fusões/incorporações com efeito entre ano_origem (exclusivo) e
    ano_destino (inclusivo). Segue cadeias: PRP -> PATRIOTA (2020) -> PRD (2024).
    Exemplo: sucessor("PSL", 2020, 2022) == "UNIÃO";
             sucessor("PSL", 2016, 2018) == "PSL".
    """
    if lin is None:
        return None
    atual = lin
    for _ in range(10):  # no máximo 10 passos (evita laço infinito)
        ev = _EVENTOS[(_EVENTOS["linhagem_origem"] == atual)
                      & (_EVENTOS["ano_efeito"] > ano_origem)
                      & (_EVENTOS["ano_efeito"] <= ano_destino)]
        if ev.empty:
            return atual
        atual = ev["linhagem_destino"].iloc[0]
    raise RuntimeError(f"Cadeia de fusões longa demais a partir de {lin}")
