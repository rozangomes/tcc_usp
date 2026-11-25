"""
utils_tse.py
============

Funções compartilhadas pelos scripts que baixam dados do TSE.
Este arquivo não é rodado sozinho; os scripts numerados o "importam".

O QUE TEM AQUI
--------------
- ArquivoRemoto / abrir_zip_remoto: leem um ZIP que está no servidor do TSE
  baixando só os pedaços necessários (requisição por intervalo, "HTTP Range"),
  em vez do arquivo inteiro.
- filtrar_cargo: copia de um CSV do TSE só as linhas de um cargo (ex.:
  "Prefeito"), sem alterar nenhum valor.
- impressao_digital: calcula o SHA-256 de um arquivo, para provar depois que
  é o mesmo arquivo baixado.
- registrar_download: acrescenta uma linha ao registro de downloads.
"""

import csv
import hashlib
import io
import zipfile
from pathlib import Path

import requests

# Endereço padrão dos ZIPs de votação por candidato, município e zona
URL_VOTACAO_MUNZONA = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
    "votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
)

# Os CSVs do TSE usam ";" como separador e codificação "latin1".
SEPARADOR = ";"
CODIFICACAO = "latin1"


class ArquivoRemoto(io.RawIOBase):
    """
    Faz um arquivo que está na internet se comportar como um arquivo local.

    A biblioteca zipfile só sabe ler arquivos. Quando ela pede "me dê os bytes
    de X a Y", esta classe busca exatamente esse trecho no servidor do TSE.
    """

    def __init__(self, url: str):
        self.url = url
        self.posicao = 0
        self.sessao = requests.Session()
        resposta = self.sessao.head(url, timeout=60)  # só o tamanho, sem baixar
        resposta.raise_for_status()
        self.tamanho = int(resposta.headers["Content-Length"])
        self.bytes_baixados = 0

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
        resposta = self.sessao.get(
            self.url, headers={"Range": f"bytes={self.posicao}-{fim}"}, timeout=300
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
    # Buffer de 4 MB: evita milhares de pedidos pequenos ao servidor
    leitor = io.BufferedReader(remoto, buffer_size=4 * 1024 * 1024)
    return zipfile.ZipFile(leitor), remoto


def filtrar_cargo(arquivo_zip, nome_interno: str, destino: Path, cargo: str) -> int:
    """
    Lê o CSV `nome_interno` de dentro do ZIP, linha por linha, e grava em
    `destino` só o cabeçalho e as linhas em que DS_CARGO == cargo.
    As linhas são copiadas exatamente como estão no original.
    Lê aos poucos (sem carregar o arquivo inteiro na memória), porque os
    arquivos nacionais têm milhões de linhas de vereador/deputado.
    Devolve o número de linhas gravadas (sem contar o cabeçalho).
    """
    alvo = cargo.upper()
    marcador = f'"{cargo}"'.upper()  # atalho rápido antes de analisar a linha
    n = 0
    with arquivo_zip.open(nome_interno) as bruto, \
            open(destino, "w", encoding=CODIFICACAO, newline="") as saida:
        texto = io.TextIOWrapper(bruto, encoding=CODIFICACAO, newline="")
        cabecalho = texto.readline()
        colunas = next(csv.reader([cabecalho], delimiter=SEPARADOR))
        pos_cargo = colunas.index("DS_CARGO")
        saida.write(cabecalho)
        for linha in texto:
            # A maioria das linhas é de outro cargo: descarta rápido
            if marcador not in linha.upper():
                continue
            campos = next(csv.reader([linha], delimiter=SEPARADOR))
            if campos[pos_cargo].upper() == alvo:
                saida.write(linha)
                n += 1
    return n


def impressao_digital(caminho: Path) -> str:
    """SHA-256 do arquivo: um código que muda se qualquer byte mudar."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def registrar_download(pasta: Path, linha: dict):
    """Acrescenta uma linha a <pasta>/registro_downloads.csv."""
    registro = pasta / "registro_downloads.csv"
    novo = not registro.exists()
    with open(registro, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linha.keys()))
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)
