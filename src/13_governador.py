"""
13_governador.py
================

O QUE ESTE SCRIPT FAZ
---------------------
1. Baixa do TSE os votos para GOVERNADOR por município e zona, nas eleições
   gerais de 1994 a 2022 (mesmos ZIPs "votacao_candidato_munzona" usados
   para presidente), guardando só as linhas de governador.
2. Monta a tabela do governador eleito em cada UF e eleição.
Ver D39 em docs/decisoes.md.

POR QUE
-------
O governador é o elo entre o prefeito e o presidente. Sem ele, parte da
relação medida pode ser, na verdade, alinhamento com o governo estadual.

REGRA DO ELEITO
---------------
Eleição ordinária; o candidato marcado ELEITO no último turno da UF
(2º turno, se houve). Cassações e eleições suplementares para governador
(raras) não são tratadas: vale o eleito nas urnas, como para presidente.
O Distrito Federal tem governador e entra como as outras UFs.

COMO RODAR
----------
    .venv\\Scripts\\python src\\13_governador.py
O download leva alguns minutos; anos já baixados são pulados.

SAÍDAS
------
data/raw/governador/votacao_candidato_munzona_{ANO}_governador.csv
data/raw/governador/registro_downloads.csv
data/processed/governador_uf.(parquet/csv): uma linha por ano × UF
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from utils_tse import (CODIFICACAO, SEPARADOR, URL_VOTACAO_MUNZONA, abrir_zip_remoto,
                       filtrar_cargo, impressao_digital, registrar_download)

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "data" / "raw" / "governador"
PASTA = RAIZ / "data" / "processed"
ANOS = list(range(1994, 2023, 4))  # 1994, 1998, ..., 2022


def baixar(ano: int) -> Path:
    destino = BRUTO / f"votacao_candidato_munzona_{ano}_governador.csv"
    if destino.exists():
        print(f"[{ano}] já existe, pulando.")
        return destino
    url = URL_VOTACAO_MUNZONA.format(ano=ano)
    nome = f"votacao_candidato_munzona_{ano}_BRASIL.csv"
    print(f"[{ano}] lendo {nome} no servidor do TSE e filtrando governador...")
    z, remoto = abrir_zip_remoto(url)
    temporario = destino.with_suffix(".parcial")
    n = filtrar_cargo(z, nome, temporario, "Governador")
    if n == 0:
        temporario.unlink()
        raise RuntimeError(f"[{ano}] nenhuma linha de governador!")
    temporario.replace(destino)
    print(f"[{ano}] salvo {destino.name}: {n:,} linhas")
    registrar_download(BRUTO, {
        "ano": ano, "arquivo_salvo": destino.name, "url_zip": url,
        "arquivo_dentro_do_zip": nome,
        "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tamanho_bytes": destino.stat().st_size, "sha256": impressao_digital(destino),
        "observacao": f"filtrado: só linhas com DS_CARGO = Governador ({n} linhas)",
    })
    return destino


def eleitos(caminho: Path, ano: int) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=SEPARADOR, encoding=CODIFICACAO, dtype=str)
    df = df[df["NM_TIPO_ELEICAO"].str.strip().str.upper() == "ELEIÇÃO ORDINÁRIA"]
    df["turno"] = df["NR_TURNO"].astype(int)
    # Último turno de cada UF; nele, quem está marcado como eleito
    ult = df.groupby("SG_UF")["turno"].transform("max")
    df = df[(df["turno"] == ult) & df["DS_SIT_TOT_TURNO"].str.upper().str.startswith("ELEITO")]
    g = (df.groupby(["SG_UF", "SG_PARTIDO", "NM_URNA_CANDIDATO", "turno"]).size()
         .reset_index().drop(columns=0))
    g.insert(0, "ano", ano)
    return g.rename(columns={"SG_UF": "sg_uf", "SG_PARTIDO": "partido_governador",
                             "NM_URNA_CANDIDATO": "governador_eleito",
                             "turno": "turno_decisao"})


def main():
    BRUTO.mkdir(parents=True, exist_ok=True)
    partes = [eleitos(baixar(ano), ano) for ano in ANOS]
    gov = pd.concat(partes, ignore_index=True)

    # Conferências: 27 UFs por ano, um eleito por UF
    por_ano = gov.groupby("ano")["sg_uf"].nunique()
    print("\nUFs com governador eleito por ano:", por_ano.to_dict())
    assert not gov.duplicated(["ano", "sg_uf"]).any(), "UF com mais de um eleito"
    assert (por_ano == 27).all(), "falta governador em alguma UF"
    print("ok: 27 UFs por ano, um governador eleito em cada")

    gov.to_parquet(PASTA / "governador_uf.parquet", index=False)
    gov.to_csv(PASTA / "governador_uf.csv", sep=";", index=False, encoding="utf-8-sig")
    print(f"Salvo data/processed/governador_uf.parquet e .csv ({len(gov)} linhas)")
    print("\nGovernadores eleitos por partido:")
    print(gov.pivot_table(index="partido_governador", columns="ano", values="sg_uf",
                          aggfunc="count", fill_value=0).to_string())


if __name__ == "__main__":
    main()
