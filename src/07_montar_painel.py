"""
07_montar_painel.py
===================

O QUE ESTE SCRIPT FAZ
---------------------
Junta os bancos de presidente e de prefeito em DOIS painéis, um para cada
direção da pergunta de pesquisa (pareamento da D16 em docs/decisoes.md).
O partido é a unidade de análise (D15), e as mudanças de nome e as fusões
são tratadas pela tabela de equivalência (D23, src/partidos.py).

PAINEL A — prefeito -> presidente  (painel_prefeito_presidente)
    "Um município governado pelo partido X dá mais votos ao candidato a
     presidente do partido X na eleição seguinte?"
    Pares: prefeito eleito em t  ×  1º turno para presidente em t+2
           (1996->1998, 2000->2002, ..., 2024->2026)
    Uma linha = município × par de eleições × candidato a presidente.
    Variável-chave: mesmo_partido = 1 se o candidato a presidente é do
    partido do prefeito (com o partido do prefeito levado a t+2, aplicando
    fusões: prefeito do PSL eleito em 2020 conta como União Brasil em 2022).
    Resultado: pct_votos_presidente (% de votos válidos do candidato).
    Também traz o % do mesmo partido na eleição presidencial ANTERIOR (t-2),
    para comparar com o "ponto de partida" do partido no município.

PAINEL B — presidente -> prefeito  (painel_presidente_prefeito)
    "Ter o partido na Presidência favorece ou prejudica o partido nas
     eleições municipais?"
    Pares: presidente eleito em t  ×  eleição municipal em t+2
           (1994->1996, 1998->2000, ..., 2022->2024)
    Uma linha = município × eleição municipal × partido. Entram os partidos
    que tiveram candidato a prefeito no município em t+2 OU na eleição
    municipal anterior (t-2); quem não teve candidato fica com 0%.
    Variável-chave: partido_do_presidente = 1 se o partido é o do presidente
    eleito em t (levado a t+2, aplicando fusões).
    Resultados: pct_prefeito_1t (% de votos válidos no 1º turno) e
    elegeu_prefeito (1 = o partido elegeu o prefeito).
    Também traz o % do partido na eleição municipal anterior (t-2).

O QUE NÃO FAZ
-------------
Não calcula correlações nem regressões (isso fica para o script de análise).
Os painéis mostram ASSOCIAÇÃO, não causalidade.

ENTRADAS
--------
data/processed/presidente_municipio_candidato.parquet   (script 02)
data/processed/prefeito_municipio_candidato.parquet     (script 05)
data/processed/prefeito_municipio.parquet               (script 05)
data/manual/partidos_*.csv                              (via partidos.py)

SAÍDAS
------
data/processed/painel_prefeito_presidente.(parquet/csv)
data/processed/painel_presidente_prefeito.(parquet/csv)

COMO RODAR
----------
    .venv\\Scripts\\python src\\07_montar_painel.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

from partidos import linhagem, sucessor

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "processed"

# Pares de eleições (D16)
PARES_A = [(t, t + 2) for t in range(1996, 2025, 4)]   # prefeito t -> presidente t+2
PARES_B = [(t, t + 2) for t in range(1994, 2023, 4)]   # presidente t -> prefeito t+2

# Informações do município (vêm do banco de prefeito, que usa o código IBGE
# para região e capital; ver D12)
COLS_MUN = ["cd_municipio_tse", "cd_municipio_ibge", "nm_municipio",
            "sg_uf", "regiao", "capital"]


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def adicionar_linhagem(df: pd.DataFrame, col_sigla: str, col_ano: str,
                       nova: str) -> pd.DataFrame:
    """Cria a coluna `nova` com a linhagem de cada sigla no seu ano.
    Calcula uma vez por combinação (sigla, ano), o que é bem mais rápido."""
    pares = df[[col_sigla, col_ano]].drop_duplicates().dropna()
    mapa = {(s, a): linhagem(s, int(a)) for s, a in zip(pares[col_sigla], pares[col_ano])}
    df[nova] = [mapa.get((s, a)) for s, a in zip(df[col_sigla], df[col_ano])]
    faltam = df.loc[df[col_sigla].notna() & df[nova].isna(), col_sigla].unique()
    assert len(faltam) == 0, f"Siglas sem linhagem: {faltam} (rode o script 06)"
    return df


def levar_para(df: pd.DataFrame, col_lin: str, ano_origem: int,
               ano_destino: int, nova: str) -> pd.DataFrame:
    """Leva a linhagem de `ano_origem` até `ano_destino`, aplicando as fusões
    ocorridas no meio (ex.: PSL em 2020 -> UNIÃO em 2022)."""
    mapa = {l: sucessor(l, ano_origem, ano_destino) for l in df[col_lin].dropna().unique()}
    df[nova] = df[col_lin].map(mapa)
    return df


def presidente_por_linhagem(pres: pd.DataFrame, ano: int,
                            ano_destino: int) -> pd.DataFrame:
    """% de votos no 1º turno para presidente, por município e partido, num
    ano. A linhagem é levada até `ano_destino` (para comparar anos)."""
    d = pres[(pres["ano"] == ano) & (pres["turno"] == 1)].copy()
    d = levar_para(d, "linhagem", ano, ano_destino, "lin_dest")
    return (d.groupby(["cd_municipio_tse", "lin_dest"], as_index=False)["pct_votos"].sum())


def prefeito_por_linhagem(pref: pd.DataFrame, ano: int,
                          ano_destino: int) -> pd.DataFrame:
    """% de votos no 1º turno para prefeito (eleição ordinária), por
    município e partido, num ano. Se um partido tiver mais de um candidato
    (caso raro, por registro anulado), os % são somados."""
    d = pref[(pref["ano"] == ano) & (pref["turno"] == 1)].copy()
    d = levar_para(d, "linhagem", ano, ano_destino, "lin_dest")
    return (d.groupby(["cd_municipio_tse", "lin_dest"], as_index=False)
            .agg(pct=("pct_votos", "sum"), n_candidatos=("nr_candidato", "size")))


def partido_presidente_eleito(pres: pd.DataFrame, ano: int) -> tuple[str, str]:
    """Partido e nome do presidente eleito: mais votado no Brasil no último
    turno daquele ano (2º turno, se houve)."""
    d = pres[pres["ano"] == ano]
    d = d[d["turno"] == d["turno"].max()]
    tot = d.groupby(["sg_partido", "nm_urna_candidato"])["votos"].sum()
    sigla, nome = tot.idxmax()
    return sigla, nome


def salvar(df: pd.DataFrame, nome: str):
    df.to_parquet(PASTA / f"{nome}.parquet", index=False)
    df.to_csv(PASTA / f"{nome}.csv", sep=";", decimal=",", index=False,
              encoding="utf-8-sig")
    print(f"  salvo data/processed/{nome}.parquet e .csv ({len(df):,} linhas)")


# ---------------------------------------------------------------------------
# Painel A — prefeito t -> presidente t+2
# ---------------------------------------------------------------------------
def painel_a(pres, res) -> pd.DataFrame:
    partes = []
    for t, t2 in PARES_A:
        # Prefeito eleito em t, com o partido levado a t+2
        mun = res[(res["ano"] == t) & res["partido_eleito"].notna()][
            COLS_MUN + ["partido_eleito", "fonte_eleito"]].copy()
        mun["ano_eleito"] = t
        mun = adicionar_linhagem(mun, "partido_eleito", "ano_eleito", "lin_prefeito_t")
        mun = levar_para(mun, "lin_prefeito_t", t, t2, "partido_prefeito")

        # Candidatos a presidente em t+2, 1º turno
        cand = pres[(pres["ano"] == t2) & (pres["turno"] == 1)][
            ["cd_municipio_tse", "nr_candidato", "nm_urna_candidato",
             "sg_partido", "linhagem", "pct_votos"]].rename(columns={
                "nm_urna_candidato": "candidato_presidente",
                "sg_partido": "sg_partido_presidente",
                "linhagem": "partido_presidente",
                "pct_votos": "pct_votos_presidente"})

        # Ponto de partida: % do mesmo partido na eleição presidencial t-2
        ant = presidente_por_linhagem(pres, t - 2, t2).rename(columns={
            "lin_dest": "partido_presidente",
            "pct_votos": "pct_presidente_eleicao_anterior"})

        d = mun.merge(cand, on="cd_municipio_tse", how="inner")
        d = d.merge(ant, on=["cd_municipio_tse", "partido_presidente"], how="left")
        # Se o partido teve candidato em t-2 mas não neste município, é 0%;
        # se o partido não teve candidato a presidente em t-2, fica vazio.
        teve_ant = set(ant["partido_presidente"])
        sem = d["pct_presidente_eleicao_anterior"].isna() & d["partido_presidente"].isin(teve_ant)
        d.loc[sem, "pct_presidente_eleicao_anterior"] = 0.0

        d["mesmo_partido"] = (d["partido_presidente"] == d["partido_prefeito"]).astype(int)
        # O partido do prefeito teve candidato a presidente em t+2?
        com_cand = d.groupby("cd_municipio_tse")["mesmo_partido"].transform("max")
        d["partido_prefeito_tem_candidato"] = com_cand

        d.insert(0, "ano_presidente", t2)
        d.insert(0, "ano_prefeito", t)
        perdidos = (res["ano"] == t).sum() - mun["cd_municipio_tse"].isin(cand["cd_municipio_tse"]).sum()
        print(f"  {t} -> {t2}: {d['cd_municipio_tse'].nunique():,} municípios, "
              f"{d['candidato_presidente'].nunique()} candidatos; "
              f"{(d.groupby('cd_municipio_tse')['partido_prefeito_tem_candidato'].first()).sum():,} "
              f"municípios em que o partido do prefeito teve candidato "
              f"({perdidos} municípios de {t} sem par)")
        partes.append(d)

    a = pd.concat(partes, ignore_index=True)
    a = a.rename(columns={"partido_eleito": "sg_partido_prefeito"})
    return a[["ano_prefeito", "ano_presidente"] + COLS_MUN + [
        "sg_partido_prefeito", "fonte_eleito", "partido_prefeito",
        "nr_candidato", "candidato_presidente", "sg_partido_presidente",
        "partido_presidente", "mesmo_partido", "partido_prefeito_tem_candidato",
        "pct_votos_presidente", "pct_presidente_eleicao_anterior"]]


# ---------------------------------------------------------------------------
# Painel B — presidente t -> prefeito t+2
# ---------------------------------------------------------------------------
def painel_b(pres, pref, res) -> pd.DataFrame:
    partes = []
    for t, t2 in PARES_B:
        sigla_pres, nome_pres = partido_presidente_eleito(pres, t)
        lin_pres = sucessor(linhagem(sigla_pres, t), t, t2)

        atual = prefeito_por_linhagem(pref, t2, t2).rename(columns={
            "pct": "pct_prefeito_1t", "n_candidatos": "n_candidatos_partido"})
        if t2 - 4 >= 1996:
            ant = prefeito_por_linhagem(pref, t2 - 4, t2).rename(columns={
                "pct": "pct_prefeito_eleicao_anterior"}).drop(columns="n_candidatos")
        else:  # não há dados de 1992
            ant = pd.DataFrame(columns=["cd_municipio_tse", "lin_dest",
                                        "pct_prefeito_eleicao_anterior"])

        # Todos os partidos com candidato em t+2 ou em t-2, por município
        d = atual.merge(ant, on=["cd_municipio_tse", "lin_dest"], how="outer")
        d["teve_candidato"] = d["pct_prefeito_1t"].notna().astype(int)
        d["n_candidatos_partido"] = d["n_candidatos_partido"].fillna(0).astype(int)
        d["pct_prefeito_1t"] = d["pct_prefeito_1t"].fillna(0.0)
        # Só municípios que existem na eleição de t+2 (na anterior, o 0%
        # só vale se o município já existia e teve eleição)
        mun_t2 = res[res["ano"] == t2][COLS_MUN + ["partido_eleito"]].copy()
        d = d.merge(mun_t2, on="cd_municipio_tse", how="inner")
        if t2 - 4 >= 1996:
            mun_ant = set(pref.loc[pref["ano"] == t2 - 4, "cd_municipio_tse"])
            existia = d["cd_municipio_tse"].isin(mun_ant)
            d.loc[existia, "pct_prefeito_eleicao_anterior"] = \
                d.loc[existia, "pct_prefeito_eleicao_anterior"].fillna(0.0)

        # Quem elegeu o prefeito em t+2 (regra da D21)
        d["ano_mun"] = t2
        d = adicionar_linhagem(d, "partido_eleito", "ano_mun", "lin_eleito")
        d["elegeu_prefeito"] = (d["lin_dest"] == d["lin_eleito"]).astype(int)
        d.loc[d["partido_eleito"].isna(), "elegeu_prefeito"] = np.nan

        d["partido_do_presidente"] = (d["lin_dest"] == lin_pres).astype(int)
        d.insert(0, "presidente_eleito", nome_pres)
        d.insert(0, "partido_presidente_eleito", lin_pres)
        d.insert(0, "ano_municipal", t2)
        d.insert(0, "ano_presidente", t)
        n_pres = d.loc[d["partido_do_presidente"] == 1]
        print(f"  {t} -> {t2}: presidente {nome_pres} ({sigla_pres} -> {lin_pres} em {t2}); "
              f"{d['cd_municipio_tse'].nunique():,} municípios; partido do presidente "
              f"teve candidato em {int(n_pres['teve_candidato'].sum()):,} e elegeu "
              f"{int(n_pres['elegeu_prefeito'].sum()):,} prefeitos")
        partes.append(d)

    b = pd.concat(partes, ignore_index=True).rename(columns={"lin_dest": "partido"})
    return b[["ano_presidente", "ano_municipal", "partido_presidente_eleito",
              "presidente_eleito"] + COLS_MUN + [
        "partido", "partido_do_presidente", "teve_candidato",
        "n_candidatos_partido", "pct_prefeito_1t", "elegeu_prefeito",
        "pct_prefeito_eleicao_anterior"]]


# ---------------------------------------------------------------------------
def conferir(a: pd.DataFrame, b: pd.DataFrame):
    """Testes simples de coerência. Se algum falhar, o script para."""
    # A: em cada município e par, os % dos candidatos somam ~100
    soma = a.groupby(["ano_prefeito", "cd_municipio_tse"])["pct_votos_presidente"].sum()
    soma = soma[soma > 0]
    assert ((soma - 100).abs() < 0.01).all(), "Painel A: % não somam 100"
    # A: no máximo um candidato do partido do prefeito por município e par
    assert a.groupby(["ano_prefeito", "cd_municipio_tse"])["mesmo_partido"].sum().max() <= 1
    # B: no máximo um partido eleito por município e ano
    assert b.groupby(["ano_municipal", "cd_municipio_tse"])["elegeu_prefeito"].sum().max() <= 1
    # B: % de prefeito somam ~100 por município (onde houve votos)
    s = b.groupby(["ano_municipal", "cd_municipio_tse"])["pct_prefeito_1t"].sum()
    s = s[s > 0]
    assert ((s - 100).abs() < 0.01).all(), "Painel B: % não somam 100"
    # B: sem linhas duplicadas
    assert not b.duplicated(["ano_municipal", "cd_municipio_tse", "partido"]).any()
    print("ok: % somam 100, um prefeito por município, sem duplicatas")


def main():
    print("Lendo os bancos...")
    pres = pd.read_parquet(PASTA / "presidente_municipio_candidato.parquet")
    pref = pd.read_parquet(PASTA / "prefeito_municipio_candidato.parquet")
    res = pd.read_parquet(PASTA / "prefeito_municipio.parquet")
    pres = adicionar_linhagem(pres, "sg_partido", "ano", "linhagem")
    pref = adicionar_linhagem(pref, "sg_partido", "ano", "linhagem")

    print("\nPainel A — prefeito t -> presidente t+2")
    a = painel_a(pres, res)
    print("\nPainel B — presidente t -> prefeito t+2")
    b = painel_b(pres, pref, res)

    print()
    conferir(a, b)
    print()
    salvar(a, "painel_prefeito_presidente")
    salvar(b, "painel_presidente_prefeito")

    # Um primeiro olhar (descritivo, sem testes estatísticos)
    # Compara cada candidato com ele mesmo: % médio nos municípios em que o
    # prefeito é do seu partido × nos demais. Só candidatos de partidos com
    # pelo menos 30 prefeitos (abaixo disso a média é instável).
    print("\nPainel A — % médio de cada candidato a presidente (1º turno), "
          "conforme o partido do prefeito:")
    tab = (a.groupby(["ano_presidente", "candidato_presidente", "partido_presidente",
                      "mesmo_partido"])["pct_votos_presidente"]
           .agg(["mean", "size"]).unstack())
    tab = tab[tab[("size", 1)] >= 30]
    tab = pd.DataFrame({
        "n_prefeitos_do_partido": tab[("size", 1)].astype(int),
        "pct_onde_prefeito_e_do_partido": tab[("mean", 1)],
        "pct_nos_demais": tab[("mean", 0)]})
    tab["diferenca_pontos"] = tab["pct_onde_prefeito_e_do_partido"] - tab["pct_nos_demais"]
    print(tab.round(1).to_string())

    print("\nPainel B — partido do presidente: % de prefeituras conquistadas")
    tb = (b[b["partido_do_presidente"] == 1].groupby(["ano_municipal", "partido"])
          .agg(municipios=("cd_municipio_tse", "size"),
               pct_com_candidato=("teve_candidato", "mean"),
               pct_elegeu=("elegeu_prefeito", "mean")))
    tb[["pct_com_candidato", "pct_elegeu"]] *= 100
    print(tb.round(1).to_string())


if __name__ == "__main__":
    main()
