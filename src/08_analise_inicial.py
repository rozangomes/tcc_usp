"""
08_analise_inicial.py
=====================

O QUE ESTE SCRIPT FAZ
---------------------
Primeiros gráficos e testes simples com os dois painéis do script 07
(semana 3 do plano). Tudo aqui mostra ASSOCIAÇÃO entre os votos, não
causalidade.

1. GRÁFICOS (output/figuras/)
   fig1_prefeito_presidente.png
       Para cada candidato a presidente: % médio de votos nos municípios em
       que o prefeito é do partido dele × nos demais municípios.
   fig2_prefeituras_por_partido.png
       % das prefeituras conquistadas por partido em cada eleição municipal,
       com as faixas cinzas marcando quando o partido estava na Presidência.

2. CORRELAÇÕES (output/tabelas/correlacoes.csv)
   Correlação de Pearson, entre os municípios, entre:
   - direção A: o % do partido para prefeito em t e o % do candidato a
     presidente do mesmo partido em t+2;
   - direção B: o % do presidente eleito em t (1º turno) e o % do partido
     dele para prefeito em t+2.
   A correlação vai de -1 a +1: perto de 0 = sem relação; positiva = onde
   um é alto o outro também tende a ser.

3. REGRESSÕES SIMPLES (output/tabelas/regressoes.csv e regressoes.txt)
   Mínimos quadrados ordinários (MQO), com erros-padrão agrupados por
   município (porque o mesmo município aparece várias vezes).
   - Modelo A: % do candidato a presidente ~ mesmo_partido, com interação
     com capital e com os ciclos recentes, comparando cada candidato com ele
     mesmo dentro de cada UF (efeito fixo candidato × UF). O modelo A2
     acrescenta o % do partido na eleição presidencial anterior.
   - Modelo B: % do partido para prefeito (e "elegeu o prefeito") ~
     partido_do_presidente, com interações com capital e ciclo recente,
     comparando cada partido com ele mesmo dentro de cada UF (efeito fixo
     partido × UF) e com efeito fixo de ano. O modelo B2 acrescenta o % do
     partido na eleição municipal anterior.
   Ver D29-D31 em docs/decisoes.md.

COMO RODAR
----------
    .venv\\Scripts\\python src\\08_analise_inicial.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # gera os arquivos sem abrir janela
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from partidos import sucessor

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "processed"
FIG = RAIZ / "output" / "figuras"
TAB = RAIZ / "output" / "tabelas"

# Candidatos incluídos na direção A: partido com pelo menos 30 prefeitos
# eleitos em t e média de pelo menos 5% dos votos nos municípios em t+2
# (abaixo disso a comparação é instável ou irrelevante; D29).
MIN_PREFEITOS = 30
MIN_PCT_MEDIO = 5.0

# "Ciclos recentes" (hipótese secundária do CLAUDE.md): 2022, 2024 e 2026
RECENTES_PRES = {2022, 2026}
RECENTES_MUN = {2024}

# Cores e tinta (paleta de referência validada; ver docs/decisoes.md D31)
AZUL, LARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA_2, TINTA_MUDA = "#0b0b0b", "#52514e", "#898781"
GRADE, FAIXA, FUNDO = "#e6e5e0", "#ecebe6", "#fcfcfb"


# ---------------------------------------------------------------------------
# Ferramentas
# ---------------------------------------------------------------------------
def estilo(ax):
    """Eixos discretos: sem moldura em cima e à direita, grade clara."""
    ax.set_facecolor(FUNDO)
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    for lado in ["left", "bottom"]:
        ax.spines[lado].set_color(TINTA_MUDA)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def mqo_com_efeito_fixo(df, y, xs, grupo, cluster, col_ano=None):
    """
    Regressão MQO "absorvendo" um efeito fixo: de cada variável subtrai-se a
    média do seu grupo (ex.: candidato × UF). Assim cada candidato é
    comparado com ele mesmo, dentro da mesma UF. Os erros-padrão são
    agrupados por município (cluster).
    Devolve o resultado do statsmodels.
    """
    extra = [col_ano] if col_ano else []
    d = df[[y] + xs + [grupo, cluster] + extra].dropna()
    if col_ano:
        # Efeito fixo de ano: um "dummy" (0/1) por ano, menos o primeiro ano
        # que sobrou depois de tirar as linhas vazias (evita colinearidade)
        anos = pd.get_dummies(d[col_ano], prefix="ano", drop_first=True, dtype=float)
        d = pd.concat([d, anos], axis=1)
        xs = xs + list(anos.columns)
    cols = [y] + xs
    medias = d.groupby(grupo)[cols].transform("mean")
    dm = d[cols] - medias
    modelo = sm.OLS(dm[y], dm[xs])
    return modelo.fit(cov_type="cluster", cov_kwds={"groups": d[cluster]}), len(d)


def tabela_coef(res, n, nome, y):
    t = pd.DataFrame({"modelo": nome, "variavel_resposta": y,
                      "termo": res.params.index, "coeficiente": res.params.values,
                      "erro_padrao": res.bse.values, "p_valor": res.pvalues.values,
                      "ic95_inf": res.conf_int()[0].values,
                      "ic95_sup": res.conf_int()[1].values, "n_obs": n})
    return t[~t["termo"].str.startswith("ano_")]  # esconde os dummies de ano


# ---------------------------------------------------------------------------
# Direção A — prefeito t -> presidente t+2
# ---------------------------------------------------------------------------
def selecionar_candidatos(a):
    g = a.groupby(["ano_presidente", "candidato_presidente", "partido_presidente"])
    resumo = g.agg(n_prefeitos=("mesmo_partido", "sum"),
                   pct_medio=("pct_votos_presidente", "mean")).reset_index()
    ok = resumo[(resumo["n_prefeitos"] >= MIN_PREFEITOS)
                & (resumo["pct_medio"] >= MIN_PCT_MEDIO)]
    chave = ["ano_presidente", "candidato_presidente"]
    return a.merge(ok[chave], on=chave), ok


def figura1(a_sel):
    tab = (a_sel.groupby(["ano_presidente", "candidato_presidente",
                          "partido_presidente", "mesmo_partido"])["pct_votos_presidente"]
           .mean().unstack().reset_index())
    n = a_sel.groupby(["ano_presidente", "candidato_presidente"])["mesmo_partido"].sum()
    tab["n"] = [n[(r.ano_presidente, r.candidato_presidente)] for r in tab.itertuples()]
    tab = tab.sort_values(["ano_presidente", 1], ascending=[False, True]).reset_index(drop=True)
    tab.to_csv(TAB / "fig1_dados.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8.5, 0.34 * len(tab) + 1.6))
    fig.patch.set_facecolor(FUNDO)
    estilo(ax)
    ax.grid(axis="y", visible=False)
    y = np.arange(len(tab))
    ax.hlines(y, tab[0], tab[1], color=TINTA_MUDA, linewidth=2, zorder=1)
    ax.scatter(tab[0], y, s=55, color=AZUL, edgecolor=FUNDO, linewidth=2, zorder=2,
               label="Prefeito de outro partido")
    ax.scatter(tab[1], y, s=55, color=LARANJA, edgecolor=FUNDO, linewidth=2, zorder=3,
               label="Prefeito do partido do candidato")
    rotulos = [f"{r.ano_presidente}  {r.candidato_presidente.title()} ({r.partido_presidente})"
               f"  n={r.n}" for r in tab.itertuples()]
    ax.set_yticks(y, rotulos, fontsize=8.5, color=TINTA)
    # separa os anos com uma linha clara
    for i in range(1, len(tab)):
        if tab.loc[i, "ano_presidente"] != tab.loc[i - 1, "ano_presidente"]:
            ax.axhline(i - 0.5, color=GRADE, linewidth=1)
    ax.set_xlim(0, 80)
    ax.set_xlabel("% médio de votos válidos no município (1º turno para presidente)",
                  color=TINTA_2, fontsize=9)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False,
              fontsize=9, labelcolor=TINTA, borderaxespad=0.3)
    fig.suptitle("Voto para presidente conforme o partido do prefeito eleito dois anos antes",
                 x=0.01, ha="left", fontsize=11, color=TINTA, fontweight="bold")
    fig.text(0.01, 0.005, "Médias simples entre municípios, sem controles. n = número de "
             "municípios com prefeito do partido. Fonte: TSE.", fontsize=7.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.985))
    fig.savefig(FIG / "fig1_prefeito_presidente.png", dpi=200, facecolor=FUNDO)
    plt.close(fig)


def correlacao_a(a_sel, b):
    """% do partido para prefeito em t × % do candidato a presidente em t+2."""
    pref = b[["ano_municipal", "cd_municipio_tse", "partido", "pct_prefeito_1t"]].copy()
    linhas = []
    for (ano_p, cand, part), g in a_sel.groupby(
            ["ano_presidente", "candidato_presidente", "partido_presidente"]):
        t = ano_p - 2
        p = pref[pref["ano_municipal"] == t].copy()
        p["partido_t2"] = p["partido"].map({l: sucessor(l, t, ano_p) for l in p["partido"].unique()})
        p = p[p["partido_t2"] == part].groupby("cd_municipio_tse")["pct_prefeito_1t"].sum()
        x = g.set_index("cd_municipio_tse")["pct_votos_presidente"]
        xy = pd.concat([p.reindex(x.index).fillna(0.0), x], axis=1).dropna()
        linhas.append({"direcao": "A: prefeito t -> presidente t+2",
                       "ano_origem": t, "ano_destino": ano_p, "partido": part,
                       "candidato": cand, "n_municipios": len(xy),
                       "correlacao": xy.iloc[:, 0].corr(xy.iloc[:, 1])})
    return linhas


# ---------------------------------------------------------------------------
# Direção B — presidente t -> prefeito t+2
# ---------------------------------------------------------------------------
def figura2(b, res):
    partidos = ["PT", "PSDB", "PSL", "MDB", "PP", "DEM", "PSD", "PL"]
    total = res.dropna(subset=["partido_eleito"]).groupby("ano").size()
    ganhos = b.groupby(["ano_municipal", "partido"])["elegeu_prefeito"].sum()
    pres = b.groupby("ano_municipal")["partido_presidente_eleito"].first()
    anos = sorted(b["ano_municipal"].unique())
    tabela = []

    fig, eixos = plt.subplots(2, 4, figsize=(11, 5.2), sharex=True, sharey=True)
    fig.patch.set_facecolor(FUNDO)
    for ax, part in zip(eixos.flat, partidos):
        estilo(ax)
        ax.grid(axis="x", visible=False)
        # faixa cinza: eleições municipais em que o partido tinha o presidente eleito
        for ano in anos:
            if pres[ano] == part:
                ax.axvspan(ano - 2, ano + 2, color=FAIXA, zorder=0)
        anos_p = [a for a in anos if (a, part) in ganhos.index]
        vals = [100 * ganhos[(a, part)] / total[a] for a in anos_p]
        ax.plot(anos_p, vals, color=AZUL, linewidth=2, marker="o", markersize=5,
                markeredgecolor=FUNDO, markeredgewidth=1.5)
        tabela += [{"partido": part, "ano_municipal": a, "pct_prefeituras": v,
                    "partido_do_presidente": int(pres[a] == part)} for a, v in zip(anos_p, vals)]
        ax.set_title(part, fontsize=10, color=TINTA, loc="left", fontweight="bold")
        ax.set_xticks([1996, 2004, 2012, 2020], ["1996", "2004", "2012", "2020"])
        ax.set_xlim(1994, 2026)
    for ax in eixos[:, 0]:
        ax.set_ylabel("% das prefeituras", color=TINTA_2, fontsize=9)
    fig.suptitle("Prefeituras conquistadas por partido, 1996–2024",
                 x=0.01, ha="left", fontsize=11, color=TINTA, fontweight="bold")
    fig.text(0.01, 0.92, "Faixa cinza: eleição municipal dois anos depois de o partido "
             "eleger o presidente.", fontsize=8.5, color=TINTA_2)
    fig.text(0.01, 0.005, "PSL e DEM formaram o União Brasil em 2022; PR voltou a se chamar "
             "PL em 2019 (as séries juntam os nomes antigos). Fonte: TSE.",
             fontsize=7.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.91))
    fig.savefig(FIG / "fig2_prefeituras_por_partido.png", dpi=200, facecolor=FUNDO)
    plt.close(fig)
    pd.DataFrame(tabela).to_csv(TAB / "fig2_dados.csv", sep=";", decimal=",",
                                index=False, encoding="utf-8-sig")


def correlacao_b(b, pres):
    """% do presidente eleito em t (1º turno) × % do partido dele para prefeito em t+2."""
    linhas = []
    for (t, t2, part, nome), g in b.groupby(["ano_presidente", "ano_municipal",
                                             "partido_presidente_eleito", "presidente_eleito"]):
        p = pres[(pres["ano"] == t) & (pres["turno"] == 1) & (pres["nm_urna_candidato"] == nome)]
        x = p.set_index("cd_municipio_tse")["pct_votos"]
        mun = g[["cd_municipio_tse"]].drop_duplicates().set_index("cd_municipio_tse")
        yv = (g[g["partido_do_presidente"] == 1].set_index("cd_municipio_tse")["pct_prefeito_1t"]
              .reindex(mun.index).fillna(0.0))
        xy = pd.concat([x.reindex(mun.index), yv], axis=1).dropna()
        linhas.append({"direcao": "B: presidente t -> prefeito t+2",
                       "ano_origem": t, "ano_destino": t2, "partido": part,
                       "candidato": nome, "n_municipios": len(xy),
                       "correlacao": xy.iloc[:, 0].corr(xy.iloc[:, 1])})
    return linhas


# ---------------------------------------------------------------------------
def regressoes(a_sel, b):
    saida, textos = [], []

    # --- Modelo A ---
    a = a_sel.copy()
    a["mesmo_x_capital"] = a["mesmo_partido"] * a["capital"]
    a["mesmo_x_recente"] = a["mesmo_partido"] * a["ano_presidente"].isin(RECENTES_PRES).astype(int)
    a["grupo"] = a["ano_presidente"].astype(str) + a["candidato_presidente"] + a["sg_uf"]
    xs = ["mesmo_partido", "mesmo_x_capital", "mesmo_x_recente", "capital"]
    for nome, extra in [("A1", []), ("A2", ["pct_presidente_eleicao_anterior"])]:
        r, n = mqo_com_efeito_fixo(a, "pct_votos_presidente", xs + extra, "grupo",
                                   "cd_municipio_tse")
        saida.append(tabela_coef(r, n, nome, "pct_votos_presidente"))
        textos.append(f"===== Modelo {nome} (efeito fixo candidato × UF) =====\n{r.summary()}")

    # --- Modelo B ---
    b = b.copy()
    b["recente"] = b["ano_municipal"].isin(RECENTES_MUN).astype(int)
    b["pres_x_capital"] = b["partido_do_presidente"] * b["capital"]
    b["pres_x_recente"] = b["partido_do_presidente"] * b["recente"]
    b["grupo"] = b["partido"] + b["sg_uf"]
    xs = ["partido_do_presidente", "pres_x_capital", "pres_x_recente", "capital"]
    for y in ["pct_prefeito_1t", "elegeu_prefeito"]:
        for nome, extra in [("B1", []), ("B2", ["pct_prefeito_eleicao_anterior"])]:
            r, n = mqo_com_efeito_fixo(b, y, xs + extra, "grupo", "cd_municipio_tse",
                                       col_ano="ano_municipal")
            saida.append(tabela_coef(r, n, nome, y))
            textos.append(f"===== Modelo {nome}, resposta = {y} "
                          f"(efeito fixo partido × UF + ano) =====\n{r.summary()}")

    coef = pd.concat(saida, ignore_index=True)
    coef.to_csv(TAB / "regressoes.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    (TAB / "regressoes.txt").write_text("\n\n".join(textos), encoding="utf-8")
    return coef


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    a = pd.read_parquet(PASTA / "painel_prefeito_presidente.parquet")
    b = pd.read_parquet(PASTA / "painel_presidente_prefeito.parquet")
    res = pd.read_parquet(PASTA / "prefeito_municipio.parquet")
    pres = pd.read_parquet(PASTA / "presidente_municipio_candidato.parquet")

    a_sel, cands = selecionar_candidatos(a)
    print(f"Direção A: {len(cands)} candidatos a presidente incluídos "
          f"(≥{MIN_PREFEITOS} prefeitos do partido e ≥{MIN_PCT_MEDIO:.0f}% de média)")

    figura1(a_sel)
    figura2(b, res)
    print("Gráficos salvos em output/figuras/")

    cor = pd.DataFrame(correlacao_a(a_sel, b) + correlacao_b(b, pres))
    cor.to_csv(TAB / "correlacoes.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print("\nCorrelações (Pearson, entre municípios):")
    print(cor.round(2).to_string(index=False))

    coef = regressoes(a_sel, b)
    print("\nRegressões (coeficientes principais; erros-padrão agrupados por município):")
    mostrar = coef[~coef["termo"].isin(["capital"])]
    print(mostrar[["modelo", "variavel_resposta", "termo", "coeficiente", "erro_padrao",
                   "p_valor", "n_obs"]].round(3).to_string(index=False))
    print("\nTabelas salvas em output/tabelas/")


if __name__ == "__main__":
    main()
