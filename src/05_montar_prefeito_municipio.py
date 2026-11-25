"""
05_montar_prefeito_municipio.py
===============================

O QUE ESTE SCRIPT FAZ
---------------------
Lê os arquivos brutos de prefeito (script 04) e monta dois bancos limpos,
de 1996 a 2024:

1) data/processed/prefeito_municipio_candidato.(parquet/csv)
   Uma linha por município × ano × turno × candidato a prefeito, com votos e
   % dos votos válidos, só da ELEIÇÃO ORDINÁRIA (a de outubro).

2) data/processed/prefeito_municipio.(parquet/csv)
   Uma linha por município × ano: quem foi eleito prefeito (partido, nome),
   com quantos % no 1º turno, se houve 2º turno e de onde veio a informação
   (eleição ordinária ou suplementar).

Os dois bancos já trazem o código IBGE, a região e a dummy de capital,
vindos da tabela TSE × IBGE (script 03, que precisa ter sido rodado antes).

REGRAS (detalhes e justificativas em docs/decisoes.md, D19 a D22)
------------------------------------------------------------------
a) Qual coluna tem os votos: em 2000 o TSE deixou QT_VOTOS_NOMINAIS zerada e
   pôs os votos em QT_VOTOS_NOMINAIS_VALIDOS (o mesmo problema de 1998 para
   presidente). Nos outros anos usamos QT_VOTOS_NOMINAIS.

b) Votos anulados: votos em candidatos que tiveram o registro negado ou
   cassado não são votos válidos. Como o TSE marca isso:
     - 2016 em diante: coluna NM_TIPO_DESTINACAO_VOTOS ("Válido",
       "Anulado", "Anulado sub judice"). Válido = começa com "Válido".
     - antes de 2016: pela situação da candidatura (INAPTO, INDEFERIDO,
       CASSAÇÃO DO REGISTRO, CANCELAMENTO = não apto).
   A coluna `apto` marca isso; `pct_votos` é calculada só sobre votos aptos.

c) Eleição ordinária x suplementar: o banco de votos usa só a ordinária. As
   suplementares (também chamadas extraordinárias) acontecem meses ou anos
   depois, quando a eleição ordinária é anulada.

d) Prefeito eleito: é quem tem situação "ELEITO" no último turno da eleição
   ordinária. Se a ordinária não teve eleito (eleição anulada), usamos o
   eleito da PRIMEIRA eleição suplementar daquele ciclo, e marcamos
   `fonte_eleito = "suplementar"`.

COMO RODAR
----------
    .venv\\Scripts\\python src\\05_montar_prefeito_municipio.py
"""

import glob
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_BRUTO = RAIZ / "data" / "raw" / "prefeito"
PASTA_SAIDA = RAIZ / "data" / "processed"
TABELA_MUNICIPIOS = PASTA_SAIDA / "municipios_tse_ibge.parquet"

# Situações de candidatura que tornam os votos NÃO válidos (antes de 2016)
SITUACOES_NAO_APTAS = {
    "INAPTO", "INDEFERIDO", "INDEFERIDO POR IMPUGNAÇÃO",
    "CASSAÇÃO DO REGISTRO", "CANCELAMENTO",
}


# ---------------------------------------------------------------------------
# 1. LEITURA E PADRONIZAÇÃO DE CADA ANO
# ---------------------------------------------------------------------------
def ler_ano(caminho: str) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=";", encoding="latin1", dtype=str)
    ano = int(df["ANO_ELEICAO"].iloc[0])

    # (a) coluna de votos
    votos = pd.to_numeric(df["QT_VOTOS_NOMINAIS"])
    if votos.sum() == 0 and "QT_VOTOS_NOMINAIS_VALIDOS" in df:
        print(f"  {ano}: QT_VOTOS_NOMINAIS zerada -> usando QT_VOTOS_NOMINAIS_VALIDOS")
        votos = pd.to_numeric(df["QT_VOTOS_NOMINAIS_VALIDOS"])

    # (b) votos aptos (válidos) ou anulados
    destinacao = df.get("NM_TIPO_DESTINACAO_VOTOS", pd.Series("#NE", index=df.index))
    if destinacao.str.startswith("Válido").any():
        apto = destinacao.str.startswith("Válido")
    else:
        apto = ~df["DS_SITUACAO_CANDIDATURA"].str.upper().isin(SITUACOES_NAO_APTAS)

    # (c) tipo de eleição: ordinária ou suplementar/extraordinária.
    # Cuidado: "Extraordinária" contém a palavra "ordinária"; por isso a
    # comparação é com o nome exato.
    ordinaria = df["NM_TIPO_ELEICAO"].str.strip().str.upper() == "ELEIÇÃO ORDINÁRIA"
    assert ordinaria.any(), f"{ano}: nenhuma linha de eleição ordinária"

    return pd.DataFrame({
        "ano": ano,
        "ordinaria": ordinaria,
        "cd_eleicao": df["CD_ELEICAO"],
        "dt_eleicao": pd.to_datetime(df["DT_ELEICAO"], format="%d/%m/%Y"),
        "turno": df["NR_TURNO"].astype(int),
        "cd_municipio_tse": df["CD_MUNICIPIO"].str.zfill(5),
        "sq_candidato": df["SQ_CANDIDATO"],
        "nr_candidato": df["NR_CANDIDATO"],
        "nm_urna_candidato": df["NM_URNA_CANDIDATO"],
        "sg_partido": df["SG_PARTIDO"],
        "situacao_turno": df["DS_SIT_TOT_TURNO"],
        "apto": apto.astype(int),
        "votos": votos,
    })


# ---------------------------------------------------------------------------
# 2. ELEITO DE UMA ELEIÇÃO (ordinária ou suplementar)
# ---------------------------------------------------------------------------
def eleitos(dados: pd.DataFrame, por_codigo: bool) -> pd.DataFrame:
    """
    Para cada eleição, devolve o candidato com situação ELEITO no ÚLTIMO turno
    realizado. (Olhar só o último turno evita um problema do arquivo de 2000,
    em que o líder do 1º turno também aparece como "ELEITO" em cidades com
    2º turno.)

    por_codigo=False (eleição ordinária): a eleição é município × ano. A partir
      de 2016 o TSE dá um código diferente a cada turno da ordinária (e Macapá
      teve códigos próprios em 2020, quando a eleição foi adiada pelo apagão),
      então o código da eleição NÃO pode separar os grupos.
    por_codigo=True (suplementares): cada código é uma eleição diferente; um
      município pode ter tido mais de uma suplementar no mesmo ciclo.
    """
    chave = ["ano", "cd_municipio_tse"] + (["cd_eleicao"] if por_codigo else [])
    ultimo = dados.groupby(chave)["turno"].transform("max")
    el = dados[(dados["turno"] == ultimo) & (dados["situacao_turno"] == "ELEITO")]
    el = (el.groupby(chave + ["turno", "sq_candidato", "nm_urna_candidato",
                              "sg_partido"], as_index=False)
          .agg(votos=("votos", "sum"), dt_eleicao=("dt_eleicao", "max")))
    # Segurança: se ainda houver mais de um eleito, fica o mais votado
    return (el.sort_values("votos", ascending=False)
            .drop_duplicates(chave)
            .rename(columns={"turno": "turnos"}))


def main():
    if not TABELA_MUNICIPIOS.exists():
        raise SystemExit("Rode antes o script 03 (tabela TSE x IBGE).")

    arquivos = sorted(glob.glob(str(PASTA_BRUTO / "votacao_candidato_munzona_*_prefeito.csv")))
    print(f"Lendo {len(arquivos)} arquivos brutos de prefeito...")
    tudo = pd.concat([ler_ano(a) for a in arquivos], ignore_index=True)

    municipios = pd.read_parquet(TABELA_MUNICIPIOS)[
        ["cd_municipio_tse", "cd_municipio_ibge", "sg_uf", "nm_municipio_ibge",
         "regiao", "capital"]].rename(columns={"nm_municipio_ibge": "nm_municipio"})

    # -----------------------------------------------------------------------
    # 3. BANCO DE VOTOS: SÓ ELEIÇÃO ORDINÁRIA, SOMANDO AS ZONAS
    # -----------------------------------------------------------------------
    ordi = tudo[tudo["ordinaria"]]
    chaves = ["ano", "turno", "cd_municipio_tse", "sq_candidato", "nr_candidato",
              "nm_urna_candidato", "sg_partido", "apto"]
    cand = ordi.groupby(chaves, as_index=False)["votos"].sum()
    # situação final do candidato no turno (ELEITO, NÃO ELEITO, 2º TURNO)
    sit = (ordi.drop_duplicates(["ano", "turno", "cd_municipio_tse", "sq_candidato"])
           [["ano", "turno", "cd_municipio_tse", "sq_candidato", "situacao_turno"]])
    cand = cand.merge(sit, on=["ano", "turno", "cd_municipio_tse", "sq_candidato"])

    # % sobre votos válidos (só de candidatos aptos)
    grupo = ["ano", "turno", "cd_municipio_tse"]
    cand["votos_validos_mun"] = (cand["votos"] * cand["apto"]).groupby(
        [cand[c] for c in grupo]).transform("sum")
    # Onde não há nenhum voto válido registrado (caso raro de dado ausente no
    # TSE), a porcentagem fica vazia em vez de dar divisão por zero.
    cand["pct_votos"] = (100 * cand["votos"] * cand["apto"]
                         / cand["votos_validos_mun"].where(cand["votos_validos_mun"] > 0))

    cand = cand.merge(municipios, on="cd_municipio_tse", how="left")
    assert cand["cd_municipio_ibge"].notna().all(), "município sem código IBGE"

    colunas_cand = ["ano", "turno", "regiao", "sg_uf", "cd_municipio_tse",
                    "cd_municipio_ibge", "nm_municipio", "capital", "nr_candidato",
                    "nm_urna_candidato", "sg_partido", "situacao_turno", "apto",
                    "votos", "votos_validos_mun", "pct_votos"]
    cand = cand[colunas_cand].sort_values(
        ["ano", "sg_uf", "nm_municipio", "turno", "votos"],
        ascending=[1, 1, 1, 1, 0])

    # -----------------------------------------------------------------------
    # 4. QUEM FOI ELEITO EM CADA MUNICÍPIO E ANO
    # -----------------------------------------------------------------------
    el_ordi = eleitos(ordi, por_codigo=False).assign(fonte_eleito="ordinária")
    # todas as eleições suplementares, em ordem de data
    supl_todas = (eleitos(tudo[~tudo["ordinaria"]], por_codigo=True)
                  .sort_values("dt_eleicao"))
    # Informação de robustez: houve suplementar no ciclo? Quem venceu a última?
    # (A suplementar costuma ocorrer quando o eleito tem o registro ou o
    # mandato cassado; nesses casos o município passa a ser governado por
    # outro prefeito, às vezes de outro partido.)
    ultima_supl = (supl_todas.drop_duplicates(["ano", "cd_municipio_tse"], keep="last")
                   [["ano", "cd_municipio_tse", "sg_partido", "dt_eleicao"]]
                   .rename(columns={"sg_partido": "partido_eleito_ultima_suplementar",
                                    "dt_eleicao": "data_ultima_suplementar"}))
    # Para o prefeito eleito, a suplementar só entra onde a ordinária não
    # teve eleito; nesse caso usamos a PRIMEIRA suplementar do ciclo.
    el_supl = (supl_todas.drop_duplicates(["ano", "cd_municipio_tse"])
               .assign(fonte_eleito="suplementar"))
    el_supl = el_supl[~el_supl.set_index(["ano", "cd_municipio_tse"]).index.isin(
        el_ordi.set_index(["ano", "cd_municipio_tse"]).index)]
    eleito = pd.concat([el_ordi, el_supl], ignore_index=True).rename(columns={
        "nm_urna_candidato": "candidato_eleito", "sg_partido": "partido_eleito",
        "dt_eleicao": "data_eleicao_eleito"})

    # desempenho no 1º turno da ordinária (do eleito, se ele disputou)
    t1 = cand[cand["turno"] == 1]
    resumo_t1 = (t1.groupby(["ano", "cd_municipio_tse"])
                 .agg(votos_validos_1t=("votos_validos_mun", "first"),
                      n_candidatos_1t=("nr_candidato", "nunique"),
                      teve_2turno=("situacao_turno", lambda s: int((s == "2º TURNO").any())))
                 .reset_index())
    # % do partido do eleito no 1º turno da ordinária
    pct_partido = t1[["ano", "cd_municipio_tse", "sg_partido", "pct_votos"]] \
        .groupby(["ano", "cd_municipio_tse", "sg_partido"], as_index=False)["pct_votos"].sum()

    resumo = (resumo_t1
              .merge(eleito[["ano", "cd_municipio_tse", "partido_eleito",
                             "candidato_eleito", "fonte_eleito",
                             "data_eleicao_eleito"]],
                     on=["ano", "cd_municipio_tse"], how="outer")
              .merge(pct_partido.rename(columns={"sg_partido": "partido_eleito",
                                                 "pct_votos": "pct_eleito_1t"}),
                     on=["ano", "cd_municipio_tse", "partido_eleito"], how="left")
              .merge(ultima_supl, on=["ano", "cd_municipio_tse"], how="left")
              .merge(municipios, on="cd_municipio_tse", how="left"))
    # Se o eleito veio de suplementar, o % do 1º turno da ordinária não se aplica
    resumo.loc[resumo["fonte_eleito"] == "suplementar", "pct_eleito_1t"] = pd.NA
    resumo["teve_suplementar"] = resumo["data_ultima_suplementar"].notna().astype(int)

    colunas_res = ["ano", "regiao", "sg_uf", "cd_municipio_tse", "cd_municipio_ibge",
                   "nm_municipio", "capital", "partido_eleito", "candidato_eleito",
                   "fonte_eleito", "data_eleicao_eleito", "pct_eleito_1t",
                   "teve_2turno", "n_candidatos_1t", "votos_validos_1t",
                   "teve_suplementar", "partido_eleito_ultima_suplementar",
                   "data_ultima_suplementar"]
    resumo = resumo[colunas_res].sort_values(["ano", "sg_uf", "nm_municipio"])

    # -----------------------------------------------------------------------
    # 5. CONFERÊNCIAS
    # -----------------------------------------------------------------------
    print("\nPor ano:")
    conf = resumo.groupby("ano").agg(
        municipios=("cd_municipio_tse", "nunique"),
        eleito_ordinaria=("fonte_eleito", lambda s: (s == "ordinária").sum()),
        eleito_suplementar=("fonte_eleito", lambda s: (s == "suplementar").sum()),
        sem_eleito=("partido_eleito", lambda s: s.isna().sum()),
        com_2turno=("teve_2turno", "sum"),
        capitais=("capital", "sum"),
        teve_suplementar=("teve_suplementar", "sum"),
        partido_mudou_na_supl=("partido_eleito_ultima_suplementar",
                               lambda s: int((s.notna() & (s != resumo.loc[s.index, "partido_eleito"])).sum())),
    )
    votos_ano = cand[cand["turno"] == 1].groupby("ano").agg(
        votos_aptos_1t=("votos", lambda v: int((v * cand.loc[v.index, "apto"]).sum())),
        votos_anulados_1t=("votos", lambda v: int((v * (1 - cand.loc[v.index, "apto"])).sum())))
    print(conf.join(votos_ano).to_string())
    assert resumo.duplicated(["ano", "cd_municipio_tse"]).sum() == 0
    com_votos = cand[(cand["apto"] == 1) & (cand["votos_validos_mun"] > 0)]
    soma = com_votos.groupby(grupo)["pct_votos"].sum()
    assert ((soma - 100).abs() < 1e-6).all(), "% não soma 100 em algum município"
    print("ok: % dos candidatos aptos soma 100 em todos os municípios e turnos com votos")
    sem_votos = cand[cand["votos_validos_mun"] == 0].drop_duplicates(grupo)
    if len(sem_votos):
        print("aviso: municípios sem nenhum voto válido registrado pelo TSE:")
        print(sem_votos[["ano", "turno", "sg_uf", "nm_municipio"]].to_string(index=False))

    sem = resumo[resumo["partido_eleito"].isna()]
    if len(sem):
        print(f"\nMunicípios sem prefeito eleito identificado ({len(sem)}):")
        print(sem[["ano", "sg_uf", "nm_municipio"]].to_string(index=False))

    # -----------------------------------------------------------------------
    # 6. SALVA
    # -----------------------------------------------------------------------
    for nome, tabela in [("prefeito_municipio_candidato", cand),
                         ("prefeito_municipio", resumo)]:
        tabela.to_parquet(PASTA_SAIDA / f"{nome}.parquet", index=False)
        tabela.to_csv(PASTA_SAIDA / f"{nome}.csv", sep=";", decimal=",",
                      index=False, encoding="utf-8-sig")
        print(f"\nSalvo data/processed/{nome}.parquet e .csv ({len(tabela):,} linhas)")


if __name__ == "__main__":
    main()
