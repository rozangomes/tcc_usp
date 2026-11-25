"""
12_montar_proporcional.py
=========================

O QUE ESTE SCRIPT FAZ
---------------------
Monta o banco de votos POR PARTIDO nas eleições proporcionais, por
município:
  - deputado federal (1994-2026)
  - deputado estadual (1994-2026; no DF, deputado distrital)
  - vereador (1996-2024)
Ver D36 e D37 em docs/decisoes.md.

O QUE É "VOTO DO PARTIDO"
-------------------------
Voto do partido = votos nominais válidos dos seus candidatos + votos de
legenda (no número do partido). É a soma que o TSE usa para distribuir as
cadeiras. O formato das colunas muda ao longo dos anos:
  - 1994, 1996, 1998 e 2016 em diante: QT_VOTOS_NOMINAIS_VALIDOS +
    QT_TOTAL_VOTOS_LEG_VALIDOS (legenda + nominais de candidatos anulados que
    a lei manda contar para a legenda);
  - 2000 a 2014: QT_VOTOS_NOMINAIS + QT_VOTOS_LEGENDA.
  - 1994: o arquivo do TSE não traz os votos de legenda (vêm zerados), então
    em 1994 o voto do partido é só o nominal (limitação registrada na D37).

FILTROS
-------
- Só eleição ordinária (as suplementares de vereador são raras).
- As zonas são somadas por município. Não há votos do exterior nem em
  trânsito nesses cargos.

ENTRADAS
--------
data/raw/partido/votacao_partido_munzona_{ANO}.zip           (script 11)
data/processed/municipios_tse_ibge.parquet                    (script 03)

SAÍDA
-----
data/processed/proporcional_municipio_partido.(parquet/csv): uma linha por
ano × cargo × município × partido.

COMO RODAR
----------
    .venv\\Scripts\\python src\\12_montar_proporcional.py
"""

import zipfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "raw" / "partido"
PASTA = RAIZ / "data" / "processed"

ANOS = list(range(1994, 2027, 2))  # gerais e municipais alternados
CARGOS = {  # nome no TSE -> nome no nosso banco
    "DEPUTADO FEDERAL": "deputado_federal",
    "DEPUTADO ESTADUAL": "deputado_estadual",
    "DEPUTADO DISTRITAL": "deputado_estadual",  # DF: equivalente ao estadual
    "VEREADOR": "vereador",
}


def ler_ano(ano: int) -> pd.DataFrame:
    """Lê o arquivo nacional (_BRASIL.csv) de um ano e padroniza os votos."""
    z = zipfile.ZipFile(BRUTO / f"votacao_partido_munzona_{ano}.zip")
    nome = [n for n in z.namelist() if n.endswith("_BRASIL.csv")][0]
    df = pd.read_csv(z.open(nome), sep=";", encoding="latin1", dtype=str)

    df["cargo"] = df["DS_CARGO"].str.strip().str.upper().map(CARGOS)
    df = df[df["cargo"].notna()]
    df = df[df["NM_TIPO_ELEICAO"].str.strip().str.upper() == "ELEIÇÃO ORDINÁRIA"]
    assert (df["SG_UF"] != "ZZ").all() and (df["ST_VOTO_EM_TRANSITO"] == "N").all()

    num = lambda c: pd.to_numeric(df[c]) if c in df.columns else 0
    if "QT_TOTAL_VOTOS_LEG_VALIDOS" in df.columns:   # 1994-1998 e 2016+
        nominais, legenda = num("QT_VOTOS_NOMINAIS_VALIDOS"), num("QT_TOTAL_VOTOS_LEG_VALIDOS")
    else:                                            # 2000-2014
        nominais, legenda = num("QT_VOTOS_NOMINAIS"), num("QT_VOTOS_LEGENDA")
    out = pd.DataFrame({
        "ano": ano, "cargo": df["cargo"], "sg_uf": df["SG_UF"],
        "cd_municipio_tse": df["CD_MUNICIPIO"].str.zfill(5),
        "nr_partido": df["NR_PARTIDO"], "sg_partido": df["SG_PARTIDO"].str.strip(),
        "votos_nominais": nominais, "votos_legenda": legenda,
    })
    # Soma as zonas de cada município
    return (out.groupby(["ano", "cargo", "sg_uf", "cd_municipio_tse", "nr_partido", "sg_partido"],
                        as_index=False)[["votos_nominais", "votos_legenda"]].sum())


def main():
    partes = []
    for ano in ANOS:
        d = ler_ano(ano)
        partes.append(d)
        resumo = d.groupby("cargo")[["votos_nominais", "votos_legenda"]].sum() / 1e6
        print(f"[{ano}] " + "; ".join(f"{c}: {r.votos_nominais:.1f} mi nominais + "
                                       f"{r.votos_legenda:.1f} mi legenda"
                                       for c, r in resumo.iterrows()))
    df = pd.concat(partes, ignore_index=True)
    df["votos"] = df["votos_nominais"] + df["votos_legenda"]

    # % do partido sobre os votos válidos do cargo no município
    chave = ["ano", "cargo", "cd_municipio_tse"]
    df["votos_validos_mun"] = df.groupby(chave)["votos"].transform("sum")
    df["pct_votos"] = (df["votos"] / df["votos_validos_mun"] * 100).where(df["votos_validos_mun"] > 0)

    # Código IBGE, região e capital (ver D10-D12)
    mun = pd.read_parquet(PASTA / "municipios_tse_ibge.parquet")[
        ["cd_municipio_tse", "cd_municipio_ibge", "nm_municipio_ibge", "regiao", "capital"]
    ].rename(columns={"nm_municipio_ibge": "nm_municipio"})
    df = df.merge(mun, on="cd_municipio_tse", how="left")
    sem = df.loc[df["cd_municipio_ibge"].isna(), "cd_municipio_tse"].unique()
    print(f"\nMunicípios sem código IBGE: {len(sem)} {list(sem)[:10]}")

    # Conferências
    s = df.groupby(chave)["pct_votos"].sum()
    s = s[s > 0]
    assert ((s - 100).abs() < 1e-6).all(), "% não somam 100"
    assert not df.duplicated(chave + ["sg_partido", "nr_partido"]).any(), "linhas duplicadas"
    print("ok: % somam 100 em cada município e cargo; sem duplicatas")
    print("\nMunicípios por ano e cargo:")
    print(df.groupby(["ano", "cargo"])["cd_municipio_tse"].nunique().unstack().to_string())

    df = df[["ano", "cargo", "regiao", "sg_uf", "cd_municipio_tse", "cd_municipio_ibge",
             "nm_municipio", "capital", "nr_partido", "sg_partido", "votos_nominais",
             "votos_legenda", "votos", "votos_validos_mun", "pct_votos"]]
    df.to_parquet(PASTA / "proporcional_municipio_partido.parquet", index=False)
    df.to_csv(PASTA / "proporcional_municipio_partido.csv", sep=";", decimal=",",
              index=False, encoding="utf-8-sig")
    print(f"\nSalvo data/processed/proporcional_municipio_partido.parquet e .csv "
          f"({len(df):,} linhas)")


if __name__ == "__main__":
    main()
