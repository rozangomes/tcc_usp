"""
15_pib_municipal.py
===================

O QUE ESTE SCRIPT FAZ
---------------------
Monta o PIB PER CAPITA de cada município, ano a ano (2002-2023), a partir
da API do IBGE (SIDRA). É a medida de riqueza municipal disponível todo ano.
Ver D41 em docs/decisoes.md.

FONTES (API SIDRA do IBGE)
--------------------------
- PIB dos Municípios, tabela 5938, variável 37 (PIB a preços correntes, em
  mil reais), 2002-2023.
- População: estimativas anuais (tabela 6579, variável 9324) e, nos anos de
  Censo, a população recenseada: 2010 (tabela 202) e 2022 (tabela 4709).
  Nos anos sem estimativa nem Censo (2007 e 2023), a população é
  interpolada em linha reta entre o ano anterior e o seguinte.

LIMITAÇÕES
----------
- PIB per capita não é renda das famílias: mede a produção no município
  (uma cidade com uma grande indústria pode ter PIB alto e renda baixa).
- Valores em reais correntes (sem correção pela inflação). Nas regressões,
  usar o logaritmo e comparar dentro do mesmo ano (efeito fixo de ano).

COMO RODAR
----------
    .venv\\Scripts\\python src\\15_pib_municipal.py
As respostas da API ficam guardadas em data/raw/ibge_pib/ e não são
baixadas de novo.

SAÍDA
-----
data/processed/pib_municipal.(parquet/csv): uma linha por município × ano
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from utils_tse import impressao_digital, registrar_download

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "raw" / "ibge_pib"
PASTA = RAIZ / "data" / "processed"
API = "https://apisidra.ibge.gov.br/values"
ANOS_PIB = list(range(2002, 2024))
# 2024 entra só para interpolar 2023 (precisa de um ano depois)
ANOS_ESTIMATIVA = [a for a in range(2002, 2025) if a not in (2007, 2010, 2022, 2023)]

CONSULTAS = (
    [(f"pib_{a}", f"/t/5938/n6/all/v/37/p/{a}") for a in ANOS_PIB]
    + [(f"pop_estimativa_{a}", f"/t/6579/n6/all/v/9324/p/{a}") for a in ANOS_ESTIMATIVA]
    + [("pop_censo_2010", "/t/202/n6/all/v/93/p/2010/c1/0/c2/0"),
       ("pop_censo_2022", "/t/4709/n6/all/v/93/p/2022")]
)


def baixar(nome: str, caminho: str) -> pd.DataFrame:
    """Baixa (uma vez) a consulta da API e devolve código IBGE, ano e valor."""
    arq = BRUTO / f"{nome}.json"
    if not arq.exists():
        url = API + caminho
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        arq.write_bytes(r.content)
        registrar_download(BRUTO, {
            "arquivo_salvo": arq.name, "url": url,
            "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tamanho_bytes": arq.stat().st_size, "sha256": impressao_digital(arq),
        })
        print(f"  baixado {nome}")
    linhas = json.loads(arq.read_text(encoding="utf-8"))[1:]  # a 1ª linha é o cabeçalho
    df = pd.DataFrame(linhas)[["D1C", "D3C", "V"]]
    df.columns = ["cd_municipio_ibge", "ano", "valor"]
    df["ano"] = df["ano"].astype(int)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")  # "-" ou "..." viram vazio
    return df


def main():
    BRUTO.mkdir(parents=True, exist_ok=True)
    dados = {nome: baixar(nome, caminho) for nome, caminho in CONSULTAS}
    pib = pd.concat([d for n, d in dados.items() if n.startswith("pib_")])
    pib = pib.rename(columns={"valor": "pib_mil_reais"})
    pop = pd.concat([d for n, d in dados.items() if n.startswith("pop_")])
    pop = pop.rename(columns={"valor": "populacao"}).dropna()

    # Interpola a população nos anos que faltam (2007, 2023), por município
    grade = pd.MultiIndex.from_product([pop["cd_municipio_ibge"].unique(), ANOS_PIB + [2024]],
                                       names=["cd_municipio_ibge", "ano"])
    pop = (pop.set_index(["cd_municipio_ibge", "ano"])["populacao"].reindex(grade)
           .groupby(level=0).transform(lambda s: s.interpolate(limit_area="inside"))
           .reset_index())
    pop["populacao_interpolada"] = pop["ano"].isin([2007, 2023]).astype(int)

    df = pib.merge(pop, on=["cd_municipio_ibge", "ano"], how="left")
    df["pib_per_capita"] = df["pib_mil_reais"] * 1000 / df["populacao"]

    # Conferências
    sem = df["pib_per_capita"].isna().sum()
    print(f"\nLinhas: {len(df):,}; municípios por ano: "
          f"{df.groupby('ano')['cd_municipio_ibge'].nunique().min():,} a "
          f"{df.groupby('ano')['cd_municipio_ibge'].nunique().max():,}; "
          f"sem PIB per capita: {sem}")
    mage = df[df["cd_municipio_ibge"] == "3302502"].set_index("ano")["pib_per_capita"]
    print("Exemplo, Magé (RJ), PIB per capita em R$:",
          {a: round(mage[a]) for a in [2002, 2010, 2022, 2023]})
    nac = df.groupby("ano").apply(lambda g: g["pib_mil_reais"].sum() * 1000 / g["populacao"].sum())
    print("PIB per capita do Brasil (soma dos municípios), R$:",
          {a: round(nac[a]) for a in [2002, 2010, 2022, 2023]})

    df.to_parquet(PASTA / "pib_municipal.parquet", index=False)
    df.to_csv(PASTA / "pib_municipal.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"Salvo data/processed/pib_municipal.parquet e .csv ({len(df):,} linhas)")


if __name__ == "__main__":
    main()
