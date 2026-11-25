"""
01_baixar_presidente.py
=======================

O QUE ESTE SCRIPT FAZ
---------------------
Baixa do TSE os votos para PRESIDENTE por município e zona eleitoral, para
todas as eleições gerais de 1994 a 2026, e salva em data/raw/presidente/.

POR QUE ELE É UM POUCO DIFERENTE DE UM DOWNLOAD COMUM
-----------------------------------------------------
O TSE publica, para cada ano, um único ZIP com os votos de TODOS os cargos
(presidente, governador, senador, deputados). Esses ZIPs são enormes: de
40 MB a quase 600 MB cada, cerca de 2,4 GB no total.

Mas, dentro de cada ZIP, existe um arquivo separado só com os cargos de
abrangência nacional, ou seja, presidente. Ele termina em "_BR.csv" e tem
poucos megabytes. Um ZIP guarda no final um "índice" dizendo onde cada
arquivo interno começa. Então o script:
  1. lê só o índice do ZIP, no servidor do TSE;
  2. baixa apenas o pedaço do ZIP que contém o arquivo "_BR.csv".
Isso se chama "requisição por intervalo" (HTTP Range). O arquivo salvo é
exatamente o original do TSE, sem nenhuma alteração.

EXCEÇÃO: 1998
-------------
No ZIP de 1998 não existe o arquivo "_BR.csv", e os arquivos de cada estado
não trazem presidente. O voto para presidente só está no arquivo nacional
completo "_BRASIL.csv", que tem todos os cargos. Para 1998, o script lê esse
arquivo e guarda SOMENTE as linhas de presidente, sem mudar nenhum valor.
Essa decisão está registrada em docs/decisoes.md.

E 1989?
-------
O TSE só publica 1989 por UF (estado), não por município. Por isso a série
municipal começa em 1994. Ver docs/decisoes.md.

COMO RODAR
----------
    .venv\\Scripts\\python src\\01_baixar_presidente.py

Se um ano já foi baixado, o script pula esse ano. Para baixar de novo, apague
o arquivo correspondente em data/raw/presidente/.

SAÍDAS
------
- data/raw/presidente/votacao_candidato_munzona_{ANO}_BR.csv  (originais do TSE)
- data/raw/presidente/votacao_candidato_munzona_1998_presidente.csv (1998, filtrado)
- data/raw/presidente/registro_downloads.csv  (URL, data, tamanho e "impressão
  digital" SHA-256 de cada arquivo, para provar que é o mesmo arquivo depois)
"""

import csv
import hashlib
import io
import zipfile
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------

# Pasta raiz do projeto (a pasta acima de src/)
RAIZ = Path(__file__).resolve().parent.parent

# Onde os arquivos brutos serão salvos
PASTA_SAIDA = RAIZ / "data" / "raw" / "presidente"

# Anos de eleição geral com dados por município no TSE.
# (1989 não entra: o TSE só tem por UF.)
ANOS = [1994, 1998, 2002, 2006, 2010, 2014, 2018, 2022, 2026]

# Endereço padrão dos ZIPs no Portal de Dados Abertos do TSE
URL_MODELO = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
    "votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
)

# Os arquivos do TSE usam ponto e vírgula como separador e a codificação
# "latin1" (padrão antigo do Windows para acentos em português).
SEPARADOR = ";"
CODIFICACAO = "latin1"


# ---------------------------------------------------------------------------
# PEÇA TÉCNICA: um "arquivo" que, na verdade, está no servidor do TSE
# ---------------------------------------------------------------------------
class ArquivoRemoto(io.RawIOBase):
    """
    Faz um arquivo que está na internet se comportar como um arquivo local.

    A biblioteca zipfile, do Python, só sabe ler arquivos. Quando ela pede
    "me dê os bytes de X a Y", esta classe busca exatamente esse trecho no
    servidor do TSE, em vez de baixar o ZIP inteiro.
    """

    def __init__(self, url: str):
        self.url = url
        self.posicao = 0
        self.sessao = requests.Session()
        # Pergunta ao servidor o tamanho total do arquivo, sem baixá-lo
        resposta = self.sessao.head(url, timeout=60)
        resposta.raise_for_status()
        self.tamanho = int(resposta.headers["Content-Length"])
        self.bytes_baixados = 0  # contador, só para informar no final

    # As funções abaixo são as que o zipfile usa para "ler" o arquivo.
    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.posicao

    def seek(self, deslocamento, origem=io.SEEK_SET):
        if origem == io.SEEK_SET:
            self.posicao = deslocamento
        elif origem == io.SEEK_CUR:
            self.posicao += deslocamento
        else:  # io.SEEK_END
            self.posicao = self.tamanho + deslocamento
        return self.posicao

    def readinto(self, destino):
        if self.posicao >= self.tamanho:
            return 0
        fim = min(self.posicao + len(destino), self.tamanho) - 1
        # O cabeçalho "Range" pede ao servidor só o trecho de bytes desejado
        resposta = self.sessao.get(
            self.url,
            headers={"Range": f"bytes={self.posicao}-{fim}"},
            timeout=300,
        )
        resposta.raise_for_status()
        dados = resposta.content
        destino[: len(dados)] = dados
        self.posicao += len(dados)
        self.bytes_baixados += len(dados)
        return len(dados)


def abrir_zip_remoto(url: str):
    """Abre o ZIP do TSE sem baixá-lo inteiro. Devolve (zip, arquivo_remoto)."""
    remoto = ArquivoRemoto(url)
    # O "buffer" de 4 MB evita fazer milhares de pedidos pequenos ao servidor
    leitor = io.BufferedReader(remoto, buffer_size=4 * 1024 * 1024)
    return zipfile.ZipFile(leitor), remoto


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------
def impressao_digital(caminho: Path) -> str:
    """
    Calcula o SHA-256 do arquivo: um código que muda se qualquer byte mudar.
    Serve para provar, no futuro, que o arquivo usado é o mesmo baixado hoje.
    """
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def registrar(linha: dict):
    """Acrescenta uma linha ao registro de downloads (cria o arquivo se preciso)."""
    registro = PASTA_SAIDA / "registro_downloads.csv"
    novo = not registro.exists()
    with open(registro, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linha.keys()))
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)


# ---------------------------------------------------------------------------
# DOWNLOAD DE CADA ANO
# ---------------------------------------------------------------------------
def baixar_ano(ano: int):
    url = URL_MODELO.format(ano=ano)
    nome_br = f"votacao_candidato_munzona_{ano}_BR.csv"
    destino_br = PASTA_SAIDA / nome_br
    destino_1998 = PASTA_SAIDA / f"votacao_candidato_munzona_{ano}_presidente.csv"

    # Se já baixamos este ano, não baixa de novo
    if destino_br.exists() or destino_1998.exists():
        print(f"[{ano}] já existe em data/raw/presidente/, pulando.")
        return

    print(f"[{ano}] abrindo o ZIP no servidor do TSE...")
    arquivo_zip, remoto = abrir_zip_remoto(url)
    nomes_internos = arquivo_zip.namelist()

    if nome_br in nomes_internos:
        # CASO NORMAL: copia o arquivo "_BR.csv" exatamente como está
        conteudo = arquivo_zip.read(nome_br)
        destino_br.write_bytes(conteudo)
        destino = destino_br
        arquivo_interno = nome_br
        observacao = "arquivo _BR.csv original, sem alteração"
    else:
        # CASO 1998: não há "_BR.csv", e os arquivos de cada UF não trazem
        # presidente (conferido em 25/11/2026). O presidente só aparece no
        # arquivo nacional completo "_BRASIL.csv" (todos os cargos, ~55 MB
        # compactado). Lemos esse arquivo e guardamos só as linhas em que o
        # cargo é "Presidente". Nenhum valor é alterado.
        nome_brasil = f"votacao_candidato_munzona_{ano}_BRASIL.csv"
        print(f"[{ano}] sem arquivo _BR.csv; filtrando presidente em "
              f"{nome_brasil} (pode demorar alguns minutos)...")
        linhas = arquivo_zip.read(nome_brasil).decode(CODIFICACAO).splitlines()
        cabecalho = linhas[0]
        colunas = [c.strip('"') for c in cabecalho.split(SEPARADOR)]
        pos_cargo = colunas.index("DS_CARGO")
        linhas_presidente = [
            linha for linha in linhas[1:]
            if linha.split(SEPARADOR)[pos_cargo].strip('"').upper() == "PRESIDENTE"
        ]
        if not linhas_presidente:
            raise RuntimeError(f"[{ano}] nenhuma linha de presidente encontrada!")
        # Grava com a mesma codificação e separador do original
        with open(destino_1998, "w", encoding=CODIFICACAO, newline="") as f:
            f.write(cabecalho + "\r\n")
            f.write("\r\n".join(linhas_presidente) + "\r\n")
        destino = destino_1998
        arquivo_interno = nome_brasil
        observacao = (f"filtrado: só linhas com DS_CARGO = Presidente "
                      f"({len(linhas_presidente)} linhas)")

    tamanho_mb = destino.stat().st_size / 1e6
    baixado_mb = remoto.bytes_baixados / 1e6
    print(f"[{ano}] salvo {destino.name} ({tamanho_mb:.1f} MB; "
          f"baixados {baixado_mb:.1f} MB de um ZIP de {remoto.tamanho / 1e6:.0f} MB)")

    registrar({
        "ano": ano,
        "arquivo_salvo": destino.name,
        "url_zip": url,
        "arquivo_dentro_do_zip": arquivo_interno,
        "data_download": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tamanho_bytes": destino.stat().st_size,
        "sha256": impressao_digital(destino),
        "observacao": observacao,
    })


def main():
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    for ano in ANOS:
        baixar_ano(ano)
    print("\nPronto. Veja data/raw/presidente/registro_downloads.csv")


if __name__ == "__main__":
    main()
