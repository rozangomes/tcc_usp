"""
14_perfil_eleitorado.py
=======================

O QUE ESTE SCRIPT FAZ
---------------------
Monta o PERFIL DO ELEITORADO de cada município em cada eleição (1994-2026),
a partir dos arquivos "perfil_eleitorado" do TSE: quantos eleitores aptos o
município tem e como eles se dividem por sexo, faixa etária e escolaridade.
Ver D40 em docs/decisoes.md.

ATENÇÃO: o voto é secreto. Estes dados descrevem o MUNICÍPIO (ex.: "% de
eleitores com 60 anos ou mais"), não o voto de cada grupo. Concluir algo
sobre o eleitor individual a partir deles é a "falácia ecológica".

O QUE O TSE PUBLICA EM CADA ANO
-------------------------------
- Sexo: todos os anos.
- Escolaridade: de 2000 em diante (antes vem "não informado").
- Faixa etária: de 2008 em diante (antes vem "#NE").
Onde a informação não existe, a coluna fica vazia.

COMO FUNCIONA
-------------
Os arquivos de 2008 em diante são grandes (700 MB a 1,8 GB descompactados).
O script lê cada um direto do servidor do TSE, em pedaços, e já soma os
eleitores por município, sem guardar o arquivo inteiro no computador. O
registro de downloads guarda a URL, a data, o tamanho e o "ETag" (código de
versão do arquivo no servidor) de cada ZIP lido.

COMO RODAR
----------
    .venv\\Scripts\\python src\\14_perfil_eleitorado.py
Leva bastante tempo (cerca de 1 GB lido do TSE). Anos já processados são
pulados (ficam guardados em data/raw/perfil_eleitorado/).

SAÍDAS
------
data/raw/perfil_eleitorado/perfil_{ANO}_agregado.parquet  (soma por município)
data/raw/perfil_eleitorado/registro_downloads.csv
data/processed/perfil_eleitorado_municipio.(parquet/csv)
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from utils_tse import CODIFICACAO, SEPARADOR, abrir_zip_remoto, registrar_download

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "raw" / "perfil_eleitorado"
PASTA = RAIZ / "data" / "processed"
URL = ("https://cdn.tse.jus.br/estatistica/sead/odsele/"
       "perfil_eleitorado/perfil_eleitorado_{ano}.zip")
ANOS = list(range(1994, 2027, 2))


def idade_minima(faixa: str):
    """Primeiro número da faixa etária ('25 a 29 anos' -> 25). Sem número -> None."""
    m = re.search(r"\d+", str(faixa))
    return int(m.group()) if m else None


def agregar_ano(ano: int) -> pd.DataFrame:
    """Lê o(s) CSV(s) do ano no servidor do TSE e soma os eleitores por
    município × sexo × faixa etária × escolaridade."""
    destino = BRUTO / f"perfil_{ano}_agregado.parquet"  # parquet: ~10x menor que CSV
    if destino.exists():
        return pd.read_parquet(destino)
    url = URL.format(ano=ano)
    z, remoto = abrir_zip_remoto(url)
    nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
    # Arquivos por UF (2022+) ou um nacional. Nunca os dois juntos (evita
    # contar duas vezes) e nunca o exterior (ZZ).
    por_uf = [n for n in nomes if re.search(r"_[A-Z]{2}\.csv$", n) and not n.endswith("_ZZ.csv")]
    arquivos = por_uf if por_uf else [n for n in nomes if not n.endswith("_ZZ.csv")]
    print(f"[{ano}] lendo {len(arquivos)} arquivo(s) do TSE...")
    partes = []
    for nome in arquivos:
        cab = pd.read_csv(z.open(nome), sep=SEPARADOR, encoding=CODIFICACAO, nrows=0).columns
        qt = "QT_ELEITORES" if "QT_ELEITORES" in cab else "QT_ELEITORES_PERFIL"
        cols = ["SG_UF", "CD_MUNICIPIO", "DS_GENERO", "DS_FAIXA_ETARIA", "DS_GRAU_ESCOLARIDADE", qt]
        for bloco in pd.read_csv(z.open(nome), sep=SEPARADOR, encoding=CODIFICACAO, dtype=str,
                                 usecols=cols, chunksize=2_000_000):
            bloco = bloco[bloco["SG_UF"] != "ZZ"]
            bloco[qt] = pd.to_numeric(bloco[qt])
            partes.append(bloco.groupby(cols[:-1], as_index=False)[qt].sum()
                          .rename(columns={qt: "eleitores"}))
    df = pd.concat(partes).groupby(["SG_UF", "CD_MUNICIPIO", "DS_GENERO", "DS_FAIXA_ETARIA",
                                    "DS_GRAU_ESCOLARIDADE"], as_index=False)["eleitores"].sum()
    df.columns = ["sg_uf", "cd_municipio_tse", "genero", "faixa_etaria", "escolaridade", "eleitores"]
    df["cd_municipio_tse"] = df["cd_municipio_tse"].str.zfill(5)
    df.insert(0, "ano", ano)
    BRUTO.mkdir(parents=True, exist_ok=True)
    df.to_parquet(destino, index=False)
    cab = requests.head(url, timeout=60).headers
    registrar_download(BRUTO, {
        "ano": ano, "arquivo_salvo": destino.name, "url_zip": url,
        "arquivos_lidos": "|".join(arquivos),
        "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tamanho_zip_bytes": remoto.tamanho, "etag": cab.get("ETag", ""),
        "observacao": "lido direto do servidor; salvo só a soma por município, sexo, idade e escolaridade",
    })
    print(f"[{ano}] {df['eleitores'].sum():,} eleitores em {df['cd_municipio_tse'].nunique():,} municípios")
    return df


def indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula as porcentagens por município."""
    df = df.copy()
    df["idade"] = df["faixa_etaria"].map(idade_minima)
    esc = df["escolaridade"].str.upper()
    tem_idade = df["idade"].notna().any()
    tem_esc = (esc != "NÃO INFORMADO").any()

    g = df.groupby(["ano", "sg_uf", "cd_municipio_tse"])
    out = g["eleitores"].sum().rename("eleitores").to_frame()
    soma = lambda mask: df[mask].groupby(["ano", "sg_uf", "cd_municipio_tse"])["eleitores"].sum()
    out["pct_mulheres"] = soma(df["genero"].str.upper() == "FEMININO") / out["eleitores"] * 100
    if tem_idade:
        out["pct_16_24_anos"] = soma(df["idade"] < 25) / out["eleitores"] * 100
        out["pct_60_mais"] = soma(df["idade"] >= 60) / out["eleitores"] * 100
    if tem_esc:
        out["pct_ate_le_escreve"] = soma(esc.isin(["ANALFABETO", "LÊ E ESCREVE"])) / out["eleitores"] * 100
        out["pct_superior_completo"] = soma(esc == "SUPERIOR COMPLETO") / out["eleitores"] * 100
    return out.fillna({c: 0.0 for c in out.columns if c.startswith("pct_")}).reset_index()


def main():
    partes = [indicadores(agregar_ano(ano)) for ano in ANOS]
    perfil = pd.concat(partes, ignore_index=True)
    perfil.to_parquet(PASTA / "perfil_eleitorado_municipio.parquet", index=False)
    perfil.to_csv(PASTA / "perfil_eleitorado_municipio.csv", sep=";", decimal=",",
                  index=False, encoding="utf-8-sig")
    print(f"\nSalvo data/processed/perfil_eleitorado_municipio.parquet e .csv ({len(perfil):,} linhas)")
    resumo = perfil.groupby("ano").agg(
        municipios=("cd_municipio_tse", "nunique"), eleitores=("eleitores", "sum"),
        pct_16_24=("pct_16_24_anos", "mean"), pct_60_mais=("pct_60_mais", "mean"),
        pct_superior=("pct_superior_completo", "mean"))
    print(resumo.round(1).to_string())


if __name__ == "__main__":
    main()
