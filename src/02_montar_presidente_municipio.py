"""
02_montar_presidente_municipio.py
=================================

O QUE ESTE SCRIPT FAZ
---------------------
Lê os arquivos brutos baixados pelo script 01 (data/raw/presidente/) e monta
dois bancos limpos de votos para PRESIDENTE por MUNICÍPIO, de 1994 a 2026:

1) data/processed/presidente_municipio_candidato.parquet (e .csv)
   Uma linha para cada município × ano × turno × candidato.
   Ex.: "Magé, 2022, 1º turno, Lula, PT, 61.000 votos, 52,3%".

2) data/processed/presidente_municipio.parquet (e .csv)
   Uma linha para cada município × ano × turno, com um resumo:
   total de votos válidos, partido mais votado no município e o desempenho
   no município do partido que venceu a eleição nacional.

Os arquivos .csv usam ";" como separador e acentos em UTF-8, para abrirem
direto no Excel. Os .parquet são a versão compacta para o Python.

PASSO A PASSO
-------------
1. Lê cada ano e escolhe a coluna certa de votos (ver "1998" abaixo).
2. Tira votos que não pertencem a nenhum município brasileiro:
   - UF "ZZ" = votos no exterior;
   - UF "VT" e ST_VOTO_EM_TRANSITO = "S" = voto em trânsito (eleitor votando
     fora da sua cidade; não representa o eleitorado do município).
3. Soma as zonas eleitorais: o TSE informa votos por município E zona; uma
   cidade grande tem várias zonas. Somamos tudo para ficar 1 linha por cidade.
4. Calcula a porcentagem de cada candidato sobre os votos válidos do município.
   (Para presidente, votos válidos = soma dos votos nos candidatos, pois não
   existe voto de legenda.)
5. Acrescenta região e a dummy de capital (1 = capital, 0 = não capital).

ATENÇÃO
-------
- O código de município aqui é o do TSE (CD_MUNICIPIO), não o do IBGE. A
  correspondência com o IBGE será feita num script posterior.
- Partidos estão com a sigla original do ano (PSL em 2018, PL em 2022...). A
  tabela de equivalência de partidos também virá num script posterior.

COMO RODAR
----------
    .venv\\Scripts\\python src\\02_montar_presidente_municipio.py
"""

import glob
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_BRUTO = RAIZ / "data" / "raw" / "presidente"
PASTA_SAIDA = RAIZ / "data" / "processed"

# ---------------------------------------------------------------------------
# TABELAS DE APOIO
# ---------------------------------------------------------------------------

# Região de cada UF (divisão oficial do IBGE)
REGIAO = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Capitais (nome sem acento, em maiúsculas). Todas já eram capitais em 1994
# (Palmas/TO é capital desde 1990).
CAPITAIS = {
    "AC": "RIO BRANCO", "AL": "MACEIO", "AP": "MACAPA", "AM": "MANAUS",
    "BA": "SALVADOR", "CE": "FORTALEZA", "DF": "BRASILIA", "ES": "VITORIA",
    "GO": "GOIANIA", "MA": "SAO LUIS", "MT": "CUIABA", "MS": "CAMPO GRANDE",
    "MG": "BELO HORIZONTE", "PA": "BELEM", "PB": "JOAO PESSOA",
    "PR": "CURITIBA", "PE": "RECIFE", "PI": "TERESINA",
    "RJ": "RIO DE JANEIRO", "RN": "NATAL", "RS": "PORTO ALEGRE",
    "RO": "PORTO VELHO", "RR": "BOA VISTA", "SC": "FLORIANOPOLIS",
    "SP": "SAO PAULO", "SE": "ARACAJU", "TO": "PALMAS",
}


def sem_acento(texto: str) -> str:
    """'SÃO LUÍS' -> 'SAO LUIS'. Usado só para comparar nomes."""
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip()


# ---------------------------------------------------------------------------
# 1. LEITURA DE CADA ANO
# ---------------------------------------------------------------------------
def ler_ano(caminho: str) -> pd.DataFrame:
    # dtype=str: lê tudo como texto, para não perder zeros à esquerda dos
    # códigos (ex.: município "01120").
    df = pd.read_csv(caminho, sep=";", encoding="latin1", dtype=str)
    ano = int(df["ANO_ELEICAO"].iloc[0])

    # Escolha da coluna de votos.
    # Em todos os anos, os votos do candidato estão em QT_VOTOS_NOMINAIS,
    # EXCETO em 1998: nesse ano o TSE deixou QT_VOTOS_NOMINAIS zerada e
    # colocou os votos em QT_VOTOS_NOMINAIS_VALIDOS (conferido com o resultado
    # oficial: FHC 35.936.382 aqui x 35.936.540 no TSE). Nos anos que têm as
    # duas colunas preenchidas (1994, 2018, 2022, 2026) elas são idênticas.
    votos = pd.to_numeric(df["QT_VOTOS_NOMINAIS"])
    if votos.sum() == 0 and "QT_VOTOS_NOMINAIS_VALIDOS" in df:
        print(f"  {ano}: QT_VOTOS_NOMINAIS zerada -> usando QT_VOTOS_NOMINAIS_VALIDOS")
        votos = pd.to_numeric(df["QT_VOTOS_NOMINAIS_VALIDOS"])

    # Ficamos só com as colunas que interessam, com nomes mais simples
    return pd.DataFrame({
        "ano": ano,
        "turno": df["NR_TURNO"].astype(int),
        "sg_uf": df["SG_UF"],
        "cd_municipio_tse": df["CD_MUNICIPIO"].str.zfill(5),
        "nm_municipio": df["NM_MUNICIPIO"],
        "nr_zona": df["NR_ZONA"],
        "transito": df["ST_VOTO_EM_TRANSITO"],
        "nr_candidato": df["NR_CANDIDATO"],
        "nm_urna_candidato": df["NM_URNA_CANDIDATO"],
        "sg_partido": df["SG_PARTIDO"],
        "votos": votos,
    })


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(glob.glob(str(PASTA_BRUTO / "votacao_candidato_munzona_*.csv")))
    print(f"Lendo {len(arquivos)} arquivos brutos...")
    bruto = pd.concat([ler_ano(a) for a in arquivos], ignore_index=True)
    total_bruto = bruto.groupby(["ano", "turno"])["votos"].sum()

    # -----------------------------------------------------------------------
    # 2. TIRA EXTERIOR E VOTO EM TRÂNSITO
    # -----------------------------------------------------------------------
    fora = bruto["sg_uf"].isin(["ZZ", "VT"]) | (bruto["transito"] == "S")
    removidos = bruto[fora].groupby(["ano", "turno"])["votos"].sum()
    dados = bruto[~fora].copy()

    # -----------------------------------------------------------------------
    # 3. SOMA AS ZONAS -> UMA LINHA POR MUNICÍPIO × ANO × TURNO × CANDIDATO
    # -----------------------------------------------------------------------
    chaves = ["ano", "turno", "sg_uf", "cd_municipio_tse",
              "nr_candidato", "nm_urna_candidato", "sg_partido"]
    cand = dados.groupby(chaves, as_index=False)["votos"].sum()

    # O nome do município pode variar de grafia entre anos (com/sem acento).
    # Usamos o nome do ano mais recente em que o município aparece.
    nomes = (dados.sort_values("ano")
             .drop_duplicates("cd_municipio_tse", keep="last")
             .set_index("cd_municipio_tse")["nm_municipio"])
    cand["nm_municipio"] = cand["cd_municipio_tse"].map(nomes)

    # -----------------------------------------------------------------------
    # 4. PORCENTAGEM SOBRE OS VOTOS VÁLIDOS DO MUNICÍPIO
    # -----------------------------------------------------------------------
    grupo_mun = ["ano", "turno", "cd_municipio_tse"]
    cand["votos_validos_mun"] = cand.groupby(grupo_mun)["votos"].transform("sum")
    cand["pct_votos"] = 100 * cand["votos"] / cand["votos_validos_mun"]

    # -----------------------------------------------------------------------
    # 5. REGIÃO E DUMMY DE CAPITAL
    # -----------------------------------------------------------------------
    cand["regiao"] = cand["sg_uf"].map(REGIAO)
    nome_limpo = cand["nm_municipio"].map(sem_acento)
    cand["capital"] = (nome_limpo == cand["sg_uf"].map(CAPITAIS)).astype(int)

    # Conferência: deve haver exatamente 27 capitais em cada ano
    n_capitais = cand[cand["capital"] == 1].groupby("ano")["cd_municipio_tse"].nunique()
    assert (n_capitais == 27).all(), f"Número de capitais errado:\n{n_capitais}"

    colunas = ["ano", "turno", "regiao", "sg_uf", "cd_municipio_tse",
               "nm_municipio", "capital", "nr_candidato", "nm_urna_candidato",
               "sg_partido", "votos", "votos_validos_mun", "pct_votos"]
    cand = cand[colunas].sort_values(["ano", "turno", "sg_uf", "nm_municipio",
                                      "votos"], ascending=[1, 1, 1, 1, 0])

    # -----------------------------------------------------------------------
    # 6. RESUMO: UMA LINHA POR MUNICÍPIO × ANO × TURNO
    # -----------------------------------------------------------------------
    # 6a. Quem foi o mais votado no município
    mais_votado = (cand.sort_values("votos", ascending=False)
                   .drop_duplicates(grupo_mun)
                   [grupo_mun + ["sg_partido", "nm_urna_candidato", "pct_votos"]]
                   .rename(columns={"sg_partido": "partido_mais_votado_mun",
                                    "nm_urna_candidato": "candidato_mais_votado_mun",
                                    "pct_votos": "pct_mais_votado_mun"}))

    # 6b. Quem venceu a eleição NACIONAL naquele ano/turno, e quanto ele teve
    #     em cada município. Em 1994 e 1998 só houve 1º turno.
    nacional = cand.groupby(["ano", "turno", "sg_partido", "nm_urna_candidato"],
                            as_index=False)["votos"].sum()
    vencedor_nac = (nacional.sort_values("votos", ascending=False)
                    .drop_duplicates(["ano", "turno"])
                    [["ano", "turno", "sg_partido", "nm_urna_candidato"]]
                    .rename(columns={"sg_partido": "partido_mais_votado_brasil",
                                     "nm_urna_candidato": "candidato_mais_votado_brasil"}))
    pct_vencedor = (cand.merge(vencedor_nac, on=["ano", "turno"])
                    .query("sg_partido == partido_mais_votado_brasil")
                    [grupo_mun + ["pct_votos"]]
                    .rename(columns={"pct_votos": "pct_mais_votado_brasil"}))

    resumo = (cand.drop_duplicates(grupo_mun)
              [["ano", "turno", "regiao", "sg_uf", "cd_municipio_tse",
                "nm_municipio", "capital", "votos_validos_mun"]]
              .merge(mais_votado, on=grupo_mun)
              .merge(vencedor_nac, on=["ano", "turno"])
              .merge(pct_vencedor, on=grupo_mun, how="left"))
    # Se o vencedor nacional teve 0 votos numa cidade, ela não aparece no
    # merge acima; nesse caso a porcentagem é 0.
    resumo["pct_mais_votado_brasil"] = resumo["pct_mais_votado_brasil"].fillna(0)

    # -----------------------------------------------------------------------
    # 7. CONFERÊNCIAS
    # -----------------------------------------------------------------------
    print("\nVotos válidos por ano/turno (brutos, removidos e no banco final):")
    conf = pd.DataFrame({
        "total_bruto": total_bruto,
        "exterior_e_transito": removidos,
        "no_banco": cand.groupby(["ano", "turno"])["votos"].sum(),
        "municipios": resumo.groupby(["ano", "turno"]).size(),
    }).fillna(0).astype(int)
    assert (conf["total_bruto"] == conf["exterior_e_transito"] + conf["no_banco"]).all()
    print(conf.to_string())

    print("\nMais votado no Brasil em cada ano/turno:")
    print(vencedor_nac.to_string(index=False))

    # -----------------------------------------------------------------------
    # 8. SALVA
    # -----------------------------------------------------------------------
    for nome, tabela in [("presidente_municipio_candidato", cand),
                         ("presidente_municipio", resumo)]:
        tabela.to_parquet(PASTA_SAIDA / f"{nome}.parquet", index=False)
        # utf-8-sig + ";" + vírgula decimal = abre certo no Excel em português
        tabela.to_csv(PASTA_SAIDA / f"{nome}.csv", sep=";", decimal=",",
                      index=False, encoding="utf-8-sig")
        print(f"\nSalvo data/processed/{nome}.parquet e .csv ({len(tabela):,} linhas)")


if __name__ == "__main__":
    main()
