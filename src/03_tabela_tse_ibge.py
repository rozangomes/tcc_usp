"""
03_tabela_tse_ibge.py
=====================

O QUE ESTE SCRIPT FAZ
---------------------
Monta a tabela de correspondência entre o código de município do TSE e o
código do IBGE, e salva em data/processed/municipios_tse_ibge.(parquet/csv).

POR QUE PRECISAMOS DISSO
------------------------
O TSE e o IBGE usam códigos diferentes para o mesmo município. Exemplo:
Magé (RJ) é 58491 no TSE e 3302502 no IBGE. Os dados eleitorais vêm com o
código do TSE; renda, população e outros controles vêm com o do IBGE. Para
juntar as duas coisas, precisamos desta "tradução".

DE ONDE VÊM OS DADOS
--------------------
1. Tabela oficial do próprio TSE: "Códigos oficiais de UF e municípios segundo
   o TSE e o IBGE" (Portal de Dados Abertos do TSE). É a fonte principal.
2. Lista oficial de municípios do IBGE (API de Localidades). Serve para
   CONFERIR a tabela do TSE e para trazer o nome atual do município e as
   regiões geográficas (região, mesorregião, microrregião).

O ÚNICO CASO ESPECIAL
---------------------
Boa Esperança do Norte (MT) foi criado em 2000, votou em 2002 com o código
TSE 91065 e depois foi extinto, voltando ao território de Sorriso e Nova
Ubiratã. Foi recriado e votou de novo em 2026, já com outro código TSE
(73709, IBGE 5101837). O código antigo 91065 não está na tabela oficial,
então o incluímos à mão, ligado ao mesmo código IBGE, com a marcação
"correspondencia_manual = 1". Ver docs/decisoes.md (D11).

COMO RODAR
----------
    .venv\\Scripts\\python src\\03_tabela_tse_ibge.py

SAÍDAS
------
- data/raw/municipios/municipio_tse_ibge.zip         (original do TSE)
- data/raw/municipios/ibge_localidades_municipios.json (original do IBGE)
- data/raw/municipios/registro_downloads.csv
- data/processed/municipios_tse_ibge.parquet e .csv
"""

import csv
import hashlib
import json
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_BRUTO = RAIZ / "data" / "raw" / "municipios"
PASTA_SAIDA = RAIZ / "data" / "processed"

URL_TSE = ("https://cdn.tse.jus.br/estatistica/sead/odsele/"
           "municipio_tse_ibge/municipio_tse_ibge.zip")
URL_IBGE = ("https://servicodados.ibge.gov.br/api/v1/localidades/"
            "municipios?view=nivelado")

ARQ_TSE = PASTA_BRUTO / "municipio_tse_ibge.zip"
ARQ_IBGE = PASTA_BRUTO / "ibge_localidades_municipios.json"

# Códigos IBGE das 27 capitais. O script confere cada um com o nome oficial.
CAPITAIS_IBGE = {
    "1200401": "Rio Branco", "2704302": "Maceió", "1600303": "Macapá",
    "1302603": "Manaus", "2927408": "Salvador", "2304400": "Fortaleza",
    "5300108": "Brasília", "3205309": "Vitória", "5208707": "Goiânia",
    "2111300": "São Luís", "5103403": "Cuiabá", "5002704": "Campo Grande",
    "3106200": "Belo Horizonte", "1501402": "Belém", "2507507": "João Pessoa",
    "4106902": "Curitiba", "2611606": "Recife", "2211001": "Teresina",
    "3304557": "Rio de Janeiro", "2408102": "Natal", "4314902": "Porto Alegre",
    "1100205": "Porto Velho", "1400100": "Boa Vista", "4205407": "Florianópolis",
    "3550308": "São Paulo", "2800308": "Aracaju", "1721000": "Palmas",
}

# Códigos TSE antigos que não estão na tabela oficial, ligados à mão.
CORRESPONDENCIAS_MANUAIS = [
    {
        "cd_municipio_tse": "91065",
        "nm_municipio_tse": "Boa Esperança do Norte",
        "cd_municipio_ibge": "5101837",
        "obs": ("Código TSE usado só em 2002. Município extinto depois e "
                "recriado em 2026 com o código TSE 73709."),
    },
]


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------
def sem_acento(texto: str) -> str:
    """Padroniza nomes só para comparar: sem acento, maiúsculas, sem hífen."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.upper().replace("-", " ").replace("'", "").replace("  ", " ").strip()


def baixar(url: str, destino: Path):
    """Baixa um arquivo (se ainda não existir) e registra URL, data e SHA-256."""
    if destino.exists():
        print(f"{destino.name} já existe, pulando o download.")
        return
    print(f"Baixando {url} ...")
    resposta = requests.get(url, timeout=300)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)

    registro = PASTA_BRUTO / "registro_downloads.csv"
    novo = not registro.exists()
    with open(registro, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if novo:
            escritor.writerow(["arquivo_salvo", "url", "data_download",
                               "tamanho_bytes", "sha256"])
        escritor.writerow([destino.name, url,
                           datetime.now().strftime("%Y-%m-%d %H:%M"),
                           len(resposta.content),
                           hashlib.sha256(resposta.content).hexdigest()])


# ---------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    PASTA_BRUTO.mkdir(parents=True, exist_ok=True)
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    # 1. Baixa as duas fontes oficiais
    baixar(URL_TSE, ARQ_TSE)
    baixar(URL_IBGE, ARQ_IBGE)

    # 2. Lê a tabela do TSE (dtype=str mantém os zeros à esquerda: "01007")
    with zipfile.ZipFile(ARQ_TSE) as z:
        tse = pd.read_csv(z.open("municipio_tse_ibge.csv"), sep=";",
                          encoding="latin1", dtype=str)
    tabela = pd.DataFrame({
        "cd_municipio_tse": tse["CD_MUNICIPIO_TSE"].str.zfill(5),
        "cd_municipio_ibge": tse["CD_MUNICIPIO_IBGE"],
        "sg_uf": tse["SG_UF"],
        "cd_uf_ibge": tse["CD_UF_IBGE"],
        "nm_municipio_tse": tse["NM_MUNICIPIO_TSE"],
        "correspondencia_manual": 0,
        "obs": "",
    })
    data_tabela_tse = tse["DT_GERACAO"].iloc[0]

    # 3. Acrescenta os códigos antigos ligados à mão
    for caso in CORRESPONDENCIAS_MANUAIS:
        base = tabela[tabela["cd_municipio_ibge"] == caso["cd_municipio_ibge"]].iloc[0]
        tabela = pd.concat([tabela, pd.DataFrame([{
            "cd_municipio_tse": caso["cd_municipio_tse"],
            "cd_municipio_ibge": caso["cd_municipio_ibge"],
            "sg_uf": base["sg_uf"],
            "cd_uf_ibge": base["cd_uf_ibge"],
            "nm_municipio_tse": caso["nm_municipio_tse"],
            "correspondencia_manual": 1,
            "obs": caso["obs"],
        }])], ignore_index=True)

    # 4. Lê a lista do IBGE e traz nome atual e regiões geográficas
    ibge = pd.DataFrame(json.loads(ARQ_IBGE.read_text(encoding="utf-8")))
    ibge = pd.DataFrame({
        "cd_municipio_ibge": ibge["municipio-id"].astype(str),
        "nm_municipio_ibge": ibge["municipio-nome"],
        "uf_ibge": ibge["UF-sigla"],
        "regiao": ibge["regiao-nome"],
        "cd_mesorregiao": ibge["mesorregiao-id"].astype(str),
        "nm_mesorregiao": ibge["mesorregiao-nome"],
        "cd_microrregiao": ibge["microrregiao-id"].astype(str),
        "nm_microrregiao": ibge["microrregiao-nome"],
    })
    tabela = tabela.merge(ibge, on="cd_municipio_ibge", how="left")

    # 5. Dummy de capital pelo código IBGE (mais seguro que pelo nome)
    tabela["capital"] = tabela["cd_municipio_ibge"].isin(CAPITAIS_IBGE).astype(int)

    # -----------------------------------------------------------------------
    # 6. CONFERÊNCIAS (o script para com erro se alguma falhar)
    # -----------------------------------------------------------------------
    print("\nConferências:")
    # a) Todo código IBGE da tabela do TSE existe na lista oficial do IBGE
    sem_ibge = tabela["nm_municipio_ibge"].isna().sum()
    assert sem_ibge == 0, f"{sem_ibge} códigos IBGE não existem na lista do IBGE"
    print(f"  ok: todos os {tabela['cd_municipio_ibge'].nunique()} códigos IBGE "
          f"existem na lista oficial do IBGE ({len(ibge)} municípios)")
    # b) A UF é a mesma nas duas fontes
    assert (tabela["sg_uf"] == tabela["uf_ibge"]).all(), "UF diferente entre TSE e IBGE"
    print("  ok: a UF é a mesma no TSE e no IBGE em todas as linhas")
    # c) Cada código TSE aparece uma só vez; cada código IBGE também (fora os manuais)
    assert tabela["cd_municipio_tse"].is_unique, "código TSE repetido"
    assert tabela.query("correspondencia_manual == 0")["cd_municipio_ibge"].is_unique
    print("  ok: correspondência um-para-um (exceto o caso manual)")
    # d) As 27 capitais têm o nome esperado
    caps = tabela[tabela["capital"] == 1].drop_duplicates("cd_municipio_ibge")
    for _, linha in caps.iterrows():
        esperado = CAPITAIS_IBGE[linha["cd_municipio_ibge"]]
        assert sem_acento(linha["nm_municipio_ibge"]) == sem_acento(esperado), linha
    assert len(caps) == 27
    print("  ok: 27 capitais conferidas pelo nome")
    # e) Nomes diferentes entre TSE e IBGE: só informa (são grafias/renomeações)
    difere = tabela[tabela["nm_municipio_tse"].map(sem_acento)
                    != tabela["nm_municipio_ibge"].map(sem_acento)]
    print(f"  aviso: {len(difere)} municípios com nome diferente no TSE e no IBGE "
          f"(grafia ou mudança de nome). Exemplos:")
    for _, linha in difere.head(5).iterrows():
        print(f"    {linha['sg_uf']}: TSE '{linha['nm_municipio_tse']}' x "
              f"IBGE '{linha['nm_municipio_ibge']}'")

    # f) Se o banco de presidente já existe, confere se todo município dele
    #    tem correspondência
    banco = PASTA_SAIDA / "presidente_municipio.parquet"
    if banco.exists():
        pres = pd.read_parquet(banco, columns=["cd_municipio_tse"]).drop_duplicates()
        sem_par = pres[~pres["cd_municipio_tse"].isin(tabela["cd_municipio_tse"])]
        assert sem_par.empty, f"Municípios do banco de presidente sem par:\n{sem_par}"
        print(f"  ok: os {len(pres)} municípios do banco de presidente (1994-2026) "
              f"têm código IBGE")

    # 7. Salva
    tabela = tabela.drop(columns="uf_ibge")
    tabela["data_tabela_tse"] = data_tabela_tse
    colunas = ["cd_municipio_tse", "cd_municipio_ibge", "sg_uf", "cd_uf_ibge",
               "nm_municipio_tse", "nm_municipio_ibge", "regiao", "capital",
               "cd_mesorregiao", "nm_mesorregiao", "cd_microrregiao",
               "nm_microrregiao", "correspondencia_manual", "obs",
               "data_tabela_tse"]
    tabela = tabela[colunas].sort_values(["sg_uf", "nm_municipio_ibge"])
    tabela.to_parquet(PASTA_SAIDA / "municipios_tse_ibge.parquet", index=False)
    tabela.to_csv(PASTA_SAIDA / "municipios_tse_ibge.csv", sep=";",
                  index=False, encoding="utf-8-sig")
    print(f"\nSalvo data/processed/municipios_tse_ibge.parquet e .csv "
          f"({len(tabela)} linhas)")


if __name__ == "__main__":
    main()
