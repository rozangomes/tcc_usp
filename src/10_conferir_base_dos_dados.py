"""
10_conferir_base_dos_dados.py
=============================

O QUE ESTE SCRIPT FAZ
---------------------
Confere o nosso banco de prefeito (feito direto dos arquivos do TSE, script
05) com uma base independente: a Base dos Dados (basedosdados.org), tabela
`basedosdados.br_tse_eleicoes.resultados_candidato_municipio`.
Ver D34 e D35 em docs/decisoes.md.

A Base dos Dados também parte do TSE, mas faz a sua própria limpeza. Se os
dois bancos baterem, ganhamos confiança de que a nossa montagem não
introduziu erros; onde não baterem, investigamos.

O QUE É COMPARADO (só eleição ordinária, cargo prefeito, 1996-2024)
1. Número de municípios com votação em cada ano.
2. Total de votos por município, ano e turno.
3. Partido do prefeito eleito em cada município e ano.
4. Os casos que já sabíamos problemáticos: municípios que faltam no TSE
   (1996, 2024) e municípios sem prefeito eleito identificado.

COMO ACESSAR (uma vez só)
-------------------------
A Base dos Dados fica no Google BigQuery. É preciso:
  1. Uma conta Google e um projeto no Google Cloud (o "sandbox" gratuito
     do BigQuery basta; a consulta usa bem menos que a cota gratuita).
  2. Rodar o script com o ID do projeto:
         .venv\\Scripts\\python src\\10_conferir_base_dos_dados.py ID-DO-PROJETO
     Na primeira vez abre o navegador para você entrar na sua conta Google
     e autorizar a leitura do BigQuery.
O resultado da consulta fica guardado em data/raw/base_dos_dados/, então
as próximas rodadas não consultam o BigQuery de novo.

SAÍDAS
------
output/tabelas/conferencia_base_dos_dados_*.csv e um resumo no terminal.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from partidos import linhagem

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "processed"
BRUTO = RAIZ / "data" / "raw" / "base_dos_dados"
TAB = RAIZ / "output" / "tabelas"
ARQ = BRUTO / "prefeito_base_dos_dados.parquet"

TABELA_BD = "basedosdados.br_tse_eleicoes.resultados_candidato_municipio"

# Só as colunas necessárias (não lemos dados pessoais, como título eleitoral)
CONSULTA = f"""
SELECT ano, tipo_eleicao, turno, id_municipio_tse, id_municipio,
       sigla_partido, numero_candidato, resultado, SUM(votos) AS votos
FROM `{TABELA_BD}`
WHERE cargo = 'prefeito' AND ano BETWEEN 1996 AND 2024
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
"""


def baixar(projeto: str) -> pd.DataFrame:
    """Consulta o BigQuery (só na primeira vez) e guarda o resultado."""
    if ARQ.exists():
        print(f"Usando a cópia já baixada: {ARQ.relative_to(RAIZ)}")
        return pd.read_parquet(ARQ)
    import pandas_gbq  # só é necessário na primeira vez
    print("Consultando a Base dos Dados no BigQuery (pode abrir o navegador)...")
    df = pandas_gbq.read_gbq(CONSULTA, project_id=projeto, dialect="standard",
                             progress_bar_type=None)
    BRUTO.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ARQ, index=False)
    (BRUTO / "registro_downloads.txt").write_text(
        f"Fonte: Base dos Dados, tabela {TABELA_BD}\n"
        f"Consulta feita em {datetime.now():%d/%m/%Y %H:%M}\n"
        f"Linhas: {len(df)}\n\nConsulta:\n{CONSULTA}", encoding="utf-8")
    print(f"  {len(df):,} linhas salvas em {ARQ.relative_to(RAIZ)}")
    return df


def so_ordinaria(bd: pd.DataFrame) -> pd.DataFrame:
    tipos = sorted(bd["tipo_eleicao"].dropna().unique())
    print(f"Tipos de eleição na Base dos Dados: {tipos}")
    t = bd["tipo_eleicao"].str.lower().fillna("")
    ordin = t.str.contains("ordin") & ~t.str.contains("extra") & ~t.str.contains("suplem")
    return bd[ordin].copy()


def main():
    if len(sys.argv) < 2 and not ARQ.exists():
        sys.exit("Informe o ID do projeto do Google Cloud. Ex.: "
                 ".venv\\Scripts\\python src\\10_conferir_base_dos_dados.py meu-projeto")
    bd = so_ordinaria(baixar(sys.argv[1] if len(sys.argv) > 1 else ""))
    bd["cd_municipio_tse"] = bd["id_municipio_tse"].astype(str).str.zfill(5)
    nosso = pd.read_parquet(PASTA / "prefeito_municipio_candidato.parquet")
    res = pd.read_parquet(PASTA / "prefeito_municipio.parquet")
    TAB.mkdir(parents=True, exist_ok=True)

    # 1. Municípios por ano
    m_bd = bd[bd["turno"] == 1].groupby("ano")["cd_municipio_tse"].nunique()
    m_nos = nosso[nosso["turno"] == 1].groupby("ano")["cd_municipio_tse"].nunique()
    t1 = pd.DataFrame({"municipios_tse_nosso": m_nos, "municipios_base_dos_dados": m_bd})
    t1["diferenca"] = t1["municipios_base_dos_dados"] - t1["municipios_tse_nosso"]
    print("\n1. Municípios com votação para prefeito (1º turno, eleição ordinária):")
    print(t1.to_string())

    # Municípios que só aparecem em um dos bancos
    chave = ["ano", "cd_municipio_tse"]
    a = set(map(tuple, nosso.loc[nosso["turno"] == 1, chave].drop_duplicates().values))
    b = set(map(tuple, bd.loc[bd["turno"] == 1, chave].drop_duplicates().values))
    so_bd = pd.DataFrame(sorted(b - a), columns=chave).assign(onde="só na Base dos Dados")
    so_nos = pd.DataFrame(sorted(a - b), columns=chave).assign(onde="só no nosso banco")
    dif_mun = pd.concat([so_bd, so_nos], ignore_index=True)
    dif_mun.to_csv(TAB / "conferencia_base_dos_dados_municipios.csv", sep=";", index=False,
                   encoding="utf-8-sig")

    # 2. Total de votos por município, ano e turno
    v_bd = bd.groupby(["ano", "turno", "cd_municipio_tse"])["votos"].sum()
    v_nos = nosso.groupby(["ano", "turno", "cd_municipio_tse"])["votos"].sum()
    v = pd.concat({"votos_nosso": v_nos, "votos_bd": v_bd}, axis=1).dropna()
    v["diferenca"] = v["votos_bd"] - v["votos_nosso"]
    iguais = (v["diferenca"] == 0).mean() * 100
    print(f"\n2. Total de votos por município, ano e turno: {len(v):,} comparados, "
          f"{iguais:.2f}% idênticos")
    print(v.groupby("ano")["diferenca"].apply(lambda s: (s != 0).sum())
          .rename("municipios_com_diferenca").to_string())
    v[v["diferenca"] != 0].reset_index().to_csv(
        TAB / "conferencia_base_dos_dados_votos.csv", sep=";", index=False, encoding="utf-8-sig")

    # 3. Partido do prefeito eleito
    eleito = bd[bd["resultado"].str.lower().fillna("").str.startswith("eleito")]
    ult = eleito.sort_values("turno").groupby(chave).tail(1)
    p_bd = ult.set_index(chave)["sigla_partido"].rename("partido_bd")
    ord_ = res[res["fonte_eleito"] == "ordinária"].set_index(chave)["partido_eleito"].rename("partido_nosso")
    p = pd.concat([ord_, p_bd], axis=1)
    # A Base dos Dados usa a sigla ATUAL do partido em alguns anos (ex.: "MDB"
    # em 2016, quando o TSE registra "PMDB"). Por isso a comparação é feita
    # pela linhagem do partido (src/partidos.py), que junta renomeações.
    p = p.reset_index()
    lin = lambda col: [linhagem(s, a) if isinstance(s, str) else None for s, a in zip(p[col], p["ano"])]
    p["linhagem_nosso"], p["linhagem_bd"] = lin("partido_nosso"), lin("partido_bd")
    p["igual_sigla"] = p["partido_nosso"] == p["partido_bd"]
    p["igual"] = p["linhagem_nosso"] == p["linhagem_bd"]
    ambos = p.dropna(subset=["partido_nosso", "partido_bd"])
    print(f"\n3. Partido do prefeito eleito (eleição ordinária): {len(ambos):,} comparados")
    print(f"   mesma sigla: {ambos['igual_sigla'].mean() * 100:.2f}%  |  "
          f"mesmo partido (renomeações juntadas): {ambos['igual'].mean() * 100:.2f}%")
    print(ambos.groupby("ano").agg(comparados=("igual", "size"),
                                   partidos_diferentes=("igual", lambda s: int((~s).sum()))).to_string())
    print(f"   eleitos só no nosso banco: {p['partido_bd'].isna().sum()}, "
          f"só na Base dos Dados: {p['partido_nosso'].isna().sum()}")
    p[~p["igual"]].to_csv(TAB / "conferencia_base_dos_dados_eleitos.csv", sep=";",
                                        index=False, encoding="utf-8-sig")

    # 4. Casos conhecidos: municípios sem eleito no nosso banco
    sem = res[res["partido_eleito"].isna()][chave]
    achou = sem.merge(ult[chave + ["sigla_partido"]], on=chave, how="left")
    print(f"\n4. Dos {len(sem)} municípios sem prefeito eleito no nosso banco, "
          f"{achou['sigla_partido'].notna().sum()} têm eleito na Base dos Dados.")
    print("\nDetalhes salvos em output/tabelas/conferencia_base_dos_dados_*.csv")


if __name__ == "__main__":
    main()
