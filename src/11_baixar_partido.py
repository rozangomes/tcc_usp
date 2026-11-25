"""
11_baixar_partido.py
====================

O QUE ESTE SCRIPT FAZ
---------------------
Baixa do TSE os arquivos de VOTAÇÃO POR PARTIDO, por município e zona
eleitoral ("votacao_partido_munzona"), para:
  - as eleições gerais de 1994 a 2026 (deputado federal e deputado
    estadual/distrital);
  - as eleições municipais de 1996 a 2024 (vereador).
Ver D36 em docs/decisoes.md.

POR QUE ESSES DADOS
-------------------
Nas eleições proporcionais o eleitor pode votar no candidato ou só na
legenda (no partido). O arquivo por partido traz as duas coisas somadas por
partido, o que dá a melhor medida da força de cada partido em cada
município, independente de ter candidato a prefeito ou a presidente.

COMO FUNCIONA
-------------
Os ZIPs por partido são pequenos (6 a 30 MB), então são baixados inteiros e
guardados sem nenhuma alteração em data/raw/partido/ (fora do Git). A
escolha das linhas (cargos, eleição ordinária etc.) é feita no script 12.

COMO RODAR
----------
    .venv\\Scripts\\python src\\11_baixar_partido.py
Se um ano já foi baixado, o script pula esse ano.

SAÍDAS
------
- data/raw/partido/votacao_partido_munzona_{ANO}.zip
- data/raw/partido/registro_downloads.csv (URL, data, tamanho, SHA-256)
"""

from datetime import datetime
from pathlib import Path

import requests

from utils_tse import impressao_digital, registrar_download

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SAIDA = RAIZ / "data" / "raw" / "partido"

URL = ("https://cdn.tse.jus.br/estatistica/sead/odsele/"
       "votacao_partido_munzona/votacao_partido_munzona_{ano}.zip")

ANOS_GERAIS = list(range(1994, 2027, 4))      # 1994, 1998, ..., 2026
ANOS_MUNICIPAIS = list(range(1996, 2025, 4))  # 1996, 2000, ..., 2024


def baixar(ano: int):
    destino = PASTA_SAIDA / f"votacao_partido_munzona_{ano}.zip"
    if destino.exists():
        print(f"[{ano}] já existe, pulando.")
        return
    url = URL.format(ano=ano)
    temporario = destino.with_suffix(".parcial")  # só vira definitivo no fim
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(temporario, "wb") as f:
            for bloco in r.iter_content(1024 * 1024):
                f.write(bloco)
    temporario.replace(destino)
    print(f"[{ano}] salvo {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
    registrar_download(PASTA_SAIDA, {
        "ano": ano,
        "arquivo_salvo": destino.name,
        "url_zip": url,
        "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tamanho_bytes": destino.stat().st_size,
        "sha256": impressao_digital(destino),
        "observacao": "ZIP original, sem alteração",
    })


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    for ano in sorted(ANOS_GERAIS + ANOS_MUNICIPAIS):
        baixar(ano)


if __name__ == "__main__":
    main()
