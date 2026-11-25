"""
04_baixar_prefeito.py
=====================

O QUE ESTE SCRIPT FAZ
---------------------
Baixa do TSE os votos para PREFEITO por município e zona eleitoral, para todas
as eleições municipais de 1996 a 2024, e salva em data/raw/prefeito/.

COMO FUNCIONA
-------------
O TSE publica, para cada ano, um ZIP com os votos de prefeito E vereador.
A grande maioria das linhas é de vereador (há dezenas de candidatos a
vereador por cidade). Dentro do ZIP existe o arquivo nacional "_BRASIL.csv",
com todos os estados juntos. O script:
  1. lê esse arquivo direto do servidor do TSE, aos poucos;
  2. guarda SOMENTE as linhas em que DS_CARGO = "Prefeito", copiadas
     exatamente como estão no original (nenhum valor é alterado).
É a mesma lógica usada para presidente em 1998 (ver docs/decisoes.md, D18).

Ficam no arquivo todas as eleições que o TSE publica no ZIP: ordinárias e,
em alguns anos, suplementares. A escolha de quais usar é feita no script 05.

COMO RODAR
----------
    .venv\\Scripts\\python src\\04_baixar_prefeito.py

Leva alguns minutos (são ~370 MB de ZIPs no total, lidos direto do TSE).
Se um ano já foi baixado, o script pula esse ano.

SAÍDAS
------
- data/raw/prefeito/votacao_candidato_munzona_{ANO}_prefeito.csv
- data/raw/prefeito/registro_downloads.csv (URL, data, tamanho, SHA-256)
"""

from datetime import datetime
from pathlib import Path

from utils_tse import (URL_VOTACAO_MUNZONA, abrir_zip_remoto, filtrar_cargo,
                       impressao_digital, registrar_download)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SAIDA = RAIZ / "data" / "raw" / "prefeito"

# Eleições municipais com dados no Portal de Dados Abertos do TSE
ANOS = [1996, 2000, 2004, 2008, 2012, 2016, 2020, 2024]


def baixar_ano(ano: int):
    destino = PASTA_SAIDA / f"votacao_candidato_munzona_{ano}_prefeito.csv"
    if destino.exists():
        print(f"[{ano}] já existe, pulando.")
        return

    url = URL_VOTACAO_MUNZONA.format(ano=ano)
    nome_brasil = f"votacao_candidato_munzona_{ano}_BRASIL.csv"
    print(f"[{ano}] lendo {nome_brasil} no servidor do TSE e filtrando prefeito...")

    arquivo_zip, remoto = abrir_zip_remoto(url)
    temporario = destino.with_suffix(".parcial")  # só vira definitivo no fim
    n = filtrar_cargo(arquivo_zip, nome_brasil, temporario, "Prefeito")
    if n == 0:
        temporario.unlink()
        raise RuntimeError(f"[{ano}] nenhuma linha de prefeito encontrada!")
    temporario.replace(destino)

    print(f"[{ano}] salvo {destino.name}: {n:,} linhas, "
          f"{destino.stat().st_size / 1e6:.1f} MB "
          f"(baixados {remoto.bytes_baixados / 1e6:.0f} MB de um ZIP de "
          f"{remoto.tamanho / 1e6:.0f} MB)")

    registrar_download(PASTA_SAIDA, {
        "ano": ano,
        "arquivo_salvo": destino.name,
        "url_zip": url,
        "arquivo_dentro_do_zip": nome_brasil,
        "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tamanho_bytes": destino.stat().st_size,
        "sha256": impressao_digital(destino),
        "observacao": f"filtrado: só linhas com DS_CARGO = Prefeito ({n} linhas)",
    })


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    for ano in ANOS:
        baixar_ano(ano)
    print("\nPronto. Veja data/raw/prefeito/registro_downloads.csv")


if __name__ == "__main__":
    main()
