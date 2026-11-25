"""
09_dados_dashboard.py
=====================

O QUE ESTE SCRIPT FAZ
---------------------
Gera as tabelas resumidas (pequenas) que alimentam o dashboard interativo
do projeto. O dashboard não lê os painéis inteiros (centenas de milhares de
linhas): lê só estes resumos, já calculados aqui.

SAÍDAS (output/dashboard/, CSV separado por vírgula, ponto decimal)
------
- prefeito_presidente.csv  : direção A. Para cada candidato a presidente
  (mesma seleção da D29) e cada recorte (Brasil, capitais, não capitais,
  cada região): % médio de votos onde o prefeito é do partido dele × nos
  demais municípios.
- prefeituras_partido.csv  : direção B. % das prefeituras conquistadas por
  partido, em cada eleição municipal e recorte, marcando quando o partido
  era o do presidente eleito dois anos antes.
- correlacoes.csv e regressoes.csv: cópias das tabelas do script 08, em
  vírgula e ponto decimal.

COMO RODAR (depois do 08)
----------
    .venv\\Scripts\\python src\\09_dados_dashboard.py
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "processed"
TAB = RAIZ / "output" / "tabelas"
SAIDA = RAIZ / "output" / "dashboard"

MIN_PREFEITOS, MIN_PCT_MEDIO = 30, 5.0  # igual ao script 08 (D29)
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
PARTIDOS_B = ["PT", "PSDB", "PSL", "MDB", "PP", "DEM", "PSD", "PL", "UNIÃO", "PSB"]


def recortes(df):
    """Devolve (nome do recorte, parte da tabela) para cada recorte."""
    yield "Brasil", df
    yield "Capitais", df[df["capital"] == 1]
    yield "Não capitais", df[df["capital"] == 0]
    for r in REGIOES:
        yield r, df[df["regiao"] == r]


def direcao_a():
    a = pd.read_parquet(PASTA / "painel_prefeito_presidente.parquet")
    g = a.groupby(["ano_presidente", "candidato_presidente", "partido_presidente"])
    sel = g.agg(n=("mesmo_partido", "sum"), m=("pct_votos_presidente", "mean")).reset_index()
    sel = sel[(sel["n"] >= MIN_PREFEITOS) & (sel["m"] >= MIN_PCT_MEDIO)]
    chave = ["ano_presidente", "candidato_presidente", "partido_presidente"]
    a = a.merge(sel[chave], on=chave)
    linhas = []
    for nome, d in recortes(a):
        t = (d.groupby(chave + ["mesmo_partido"])["pct_votos_presidente"]
             .agg(["mean", "size"]).unstack())
        for idx, r in t.iterrows():
            linhas.append({
                "recorte": nome, "ano_presidente": idx[0],
                "candidato": idx[1].title(), "partido": idx[2],
                "n_prefeitos": int(r[("size", 1)]) if pd.notna(r[("size", 1)]) else 0,
                "pct_mesmo_partido": r[("mean", 1)], "pct_outros": r[("mean", 0)],
            })
    out = pd.DataFrame(linhas)
    out["diferenca"] = out["pct_mesmo_partido"] - out["pct_outros"]
    out["rotulo"] = out["ano_presidente"].astype(str) + " " + out["candidato"] + " (" + out["partido"] + ")"
    return out.round(2)


def direcao_b():
    b = pd.read_parquet(PASTA / "painel_presidente_prefeito.parquet")
    linhas = []
    for nome, d in recortes(b):
        total = d.groupby("ano_municipal")["cd_municipio_tse"].nunique()
        pres = d.groupby("ano_municipal")["partido_presidente_eleito"].first()
        ganhos = d.groupby(["ano_municipal", "partido"])["elegeu_prefeito"].sum()
        for (ano, part), v in ganhos.items():
            if part in PARTIDOS_B:
                linhas.append({"recorte": nome, "ano_municipal": ano, "partido": part,
                               "prefeituras": int(v), "municipios": int(total[ano]),
                               "pct_prefeituras": 100 * v / total[ano],
                               "partido_do_presidente": int(pres[ano] == part),
                               "partido_presidente_eleito": pres[ano]})
    return pd.DataFrame(linhas).round(2)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    direcao_a().to_csv(SAIDA / "prefeito_presidente.csv", index=False, encoding="utf-8")
    direcao_b().to_csv(SAIDA / "prefeituras_partido.csv", index=False, encoding="utf-8")
    cor = pd.read_csv(TAB / "correlacoes.csv", sep=";", decimal=",")
    cor.round(3).to_csv(SAIDA / "correlacoes.csv", index=False, encoding="utf-8")
    reg = pd.read_csv(TAB / "regressoes.csv", sep=";", decimal=",")
    reg = reg[reg["termo"] != "capital"]
    reg.round(4).to_csv(SAIDA / "regressoes.csv", index=False, encoding="utf-8")
    for f in sorted(SAIDA.glob("*.csv")):
        print(f"  {f.name}: {sum(1 for _ in open(f, encoding='utf-8')) - 1} linhas, "
              f"{f.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
