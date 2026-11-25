"""
06_tabela_partidos.py
=====================

O QUE ESTE SCRIPT FAZ
---------------------
Monta a tabela de equivalência de partidos usada no painel e confere se ela
está completa e coerente com os dados do TSE.

ENTRADAS (feitas à mão, versionadas no Git)
-------------------------------------------
- data/manual/partidos_siglas.csv : cada sigla -> linhagem (renomeações)
- data/manual/partidos_eventos.csv: fusões e incorporações, com o ano da
  primeira eleição em que valem
A lógica está explicada em src/partidos.py e em docs/decisoes.md (D23-D25).

CONFERÊNCIAS
------------
1. Toda sigla que aparece nos bancos de presidente e de prefeito está na
   tabela (se faltar alguma, o script para e mostra qual).
2. Nenhum partido "absorvido" aparece numa eleição ordinária depois da data
   em que deixou de existir (ex.: o PSL não pode aparecer em 2022).
3. Toda linhagem de destino de um evento existe na tabela de siglas.

SAÍDA
-----
data/processed/partidos_equivalencia.(parquet/csv): uma linha por sigla e
ano em que ela aparece nos dados, com:
  - linhagem           : o partido, juntando renomeações
  - linhagem_ano_mais_2: o partido 2 anos depois (aplicando fusões);
                         é o que se usa no pareamento t -> t+2
  - linhagem_2026      : o partido equivalente hoje (2026)

COMO RODAR
----------
    .venv\\Scripts\\python src\\06_tabela_partidos.py
"""

from pathlib import Path

import pandas as pd

from partidos import carregar_tabelas, linhagem, sucessor

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "processed"


def siglas_observadas() -> pd.DataFrame:
    """Junta todas as combinações (ano, sigla) dos bancos já montados."""
    partes = []
    pres = pd.read_parquet(PASTA / "presidente_municipio_candidato.parquet",
                           columns=["ano", "sg_partido"])
    partes.append(pres.assign(origem="presidente"))
    pref = pd.read_parquet(PASTA / "prefeito_municipio_candidato.parquet",
                           columns=["ano", "sg_partido"])
    partes.append(pref.assign(origem="prefeito (ordinária)"))
    prop_arq = PASTA / "proporcional_municipio_partido.parquet"  # script 12
    if prop_arq.exists():
        prop = pd.read_parquet(prop_arq, columns=["ano", "sg_partido"])
        partes.append(prop.assign(origem="proporcional"))
    res = pd.read_parquet(PASTA / "prefeito_municipio.parquet")
    for col in ["partido_eleito", "partido_eleito_ultima_suplementar"]:
        partes.append(res[["ano", col]].rename(columns={col: "sg_partido"})
                      .dropna().assign(origem=f"prefeito ({col})"))
    tudo = pd.concat(partes, ignore_index=True)
    return (tudo.groupby(["ano", "sg_partido"])["origem"]
            .agg(lambda s: ", ".join(sorted(set(s)))).reset_index())


def main():
    siglas, eventos = carregar_tabelas()
    obs = siglas_observadas()
    print(f"{obs['sg_partido'].nunique()} siglas diferentes em "
          f"{len(obs)} combinações ano × sigla nos dados.")

    # 1. Cobertura
    obs["linhagem"] = [linhagem(s, a) for s, a in zip(obs["sg_partido"], obs["ano"])]
    faltam = obs[obs["linhagem"].isna()]
    assert faltam.empty, f"Siglas sem linhagem na tabela:\n{faltam}"
    print("ok: todas as siglas dos dados estão na tabela de equivalência")

    # 2. Partido absorvido não aparece em eleição ordinária depois do fim
    ordinaria = obs[obs["origem"].str.contains("presidente|ordinária|proporcional")]
    problemas = []
    for _, ev in eventos.iterrows():
        depois = ordinaria[(ordinaria["linhagem"] == ev["linhagem_origem"])
                           & (ordinaria["ano"] >= ev["ano_efeito"])]
        if not depois.empty:
            problemas.append((ev["linhagem_origem"], sorted(depois["ano"].unique())))
    assert not problemas, f"Partidos que aparecem depois de extintos: {problemas}"
    print("ok: nenhum partido absorvido aparece em eleição ordinária após a fusão")

    # 3. Destinos existem
    destinos = set(eventos["linhagem_destino"]) - set(siglas["linhagem"])
    assert not destinos, f"Destinos de fusão sem linhagem: {destinos}"
    print("ok: todos os destinos de fusão existem na tabela")

    # Exemplos para conferência humana
    print("\nExemplos (sucessor do partido 2 anos depois):")
    for lin, a in [("PSL", 2016), ("PSL", 2020), ("DEM", 2020), ("PTB", 2022),
                   ("PRP", 2016), ("MDB", 2016), ("PRONA", 2004)]:
        print(f"  {lin} em {a} -> {sucessor(lin, a, a + 2)} em {a + 2}")

    # Saída
    obs["linhagem_ano_mais_2"] = [sucessor(l, a, a + 2)
                                  for l, a in zip(obs["linhagem"], obs["ano"])]
    obs["linhagem_2026"] = [sucessor(l, a, 2026)
                            for l, a in zip(obs["linhagem"], obs["ano"])]
    obs = obs[["ano", "sg_partido", "linhagem", "linhagem_ano_mais_2",
               "linhagem_2026", "origem"]].sort_values(["ano", "sg_partido"])
    obs.to_parquet(PASTA / "partidos_equivalencia.parquet", index=False)
    obs.to_csv(PASTA / "partidos_equivalencia.csv", sep=";", index=False,
               encoding="utf-8-sig")
    print(f"\nSalvo data/processed/partidos_equivalencia.parquet e .csv "
          f"({len(obs)} linhas)")

    # Resumo: siglas que mudaram de linhagem ao longo do tempo
    mudou = obs[obs["sg_partido"] != obs["linhagem_2026"]][
        ["sg_partido", "linhagem_2026"]].drop_duplicates()
    print(f"\n{len(mudou)} siglas antigas e o partido equivalente hoje:")
    print(mudou.to_string(index=False))


if __name__ == "__main__":
    main()
