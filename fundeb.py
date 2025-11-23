# ================================================================
# fundeb.py – Painel Fundeb, VAAT, VAAR & ICMS – Zetta
# ================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# ================================================================
# FUNÇÃO DE FORMATAÇÃO MONETÁRIA (PADRÃO BRASILEIRO, SEM DECIMAIS)
# ================================================================
def formatar_reais(valor):
    """
    Converte valores numéricos para o padrão brasileiro:
    R$ 1.234.567

    - Sempre sem casas decimais
    - Aceita valores None e NaN
    """
    if valor is None or pd.isna(valor):
        return "-"

    try:
        valor_fmt = f"{float(valor):,.0f}"
        valor_br = (
            valor_fmt
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        return f"R$ {valor_br}"
    except Exception:
        return "-"


# ================================================================
# BLOCO 1 – CONFIGURAÇÕES GERAIS E ESTILO
# ================================================================
st.set_page_config(
    page_title="Painel Fundeb & Complementações – Zetta",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif;
    color:#5F6169;
}

/* Cards */
.big-card{
    background:#3A0057;
    color:#fff;
    padding:28px;
    border-radius:14px;
    text-align:center;
    box-shadow:0 0 12px rgba(0,0,0,.15);
}
.small-card,.white-card{
    padding:22px;
    border-radius:12px;
    text-align:center;
    border:1px solid #E0E0E0;
    box-shadow:0 0 6px rgba(0,0,0,.08);
}
.small-card{
    background:#F3F3F3;
    color:#3A0057;
}
.white-card{
    background:#fff;
    color:#3A0057;
}

/* Abas */
.stTabs [data-baseweb="tab-list"] { gap: 10px; }
.stTabs [data-baseweb="tab"] {
  background:#fff;
  color:#3A0057;
  border:1px solid #E5D9EF;
  border-radius:10px;
  padding:10px 16px;
}
.stTabs [aria-selected="true"] {
  background:#3A0057 !important;
  color:#fff !important;
}

/* Tabelas */
.dataframe td, .dataframe th {
  text-align: center !important;
  vertical-align: middle !important;
}
</style>
""", unsafe_allow_html=True)

# ================================================================
# BLOCO 2 – CARREGAMENTO UNIVERSAL DE DADOS
# ================================================================
@st.cache_data(show_spinner=True)
def carregar_dados():
    import os
    import pandas as pd
    import numpy as np

    nome_arquivo = "loa.xlsx"

    caminhos_possiveis = [
        nome_arquivo,
        os.path.join("data", nome_arquivo),
        os.path.join("dados", nome_arquivo),
        os.path.join("Data", nome_arquivo),
        os.path.join("Dados", nome_arquivo),
    ]

    caminho_encontrado = None
    for c in caminhos_possiveis:
        if os.path.exists(c):
            caminho_encontrado = c
            break

    if caminho_encontrado is None:
        st.error(f"""
        ❌ Arquivo não encontrado.

        Coloque o arquivo:
        **{nome_arquivo}**

        ➤ na mesma pasta do *fundeb.py*  
        **OU**  
        ➤ dentro da pasta **data/** ou **dados/**.
        """)
        st.stop()

    df = pd.read_excel(caminho_encontrado, sheet_name="Planilha1")

    abas = pd.ExcelFile(caminho_encontrado).sheet_names
    if "Habilitação VAAT 2026" in abas:
        df_vaat_hab = pd.read_excel(caminho_encontrado, sheet_name="Habilitação VAAT 2026")
    else:
        df_vaat_hab = pd.DataFrame()

    df.columns = [c.strip() for c in df.columns]

    def _coerce_numeric(col):
        if pd.api.types.is_numeric_dtype(col):
            return col
        col = col.astype(str)
        col = col.str.replace(".", "", regex=False)
        col = col.str.replace(",", ".", regex=False)
        col = col.replace({"-": np.nan, "--": np.nan, "nan": np.nan, "None": np.nan, "": np.nan})
        return pd.to_numeric(col, errors="coerce")

    num_cols = [
        "Orçamento",
        "Despesa Educação",
        "Receita Cota-parte ICMS Estimada",
        "Receita Fundeb Estimada",
        "Cota-parte ICMS Realizada",
        "ICMS Educacional",
        "Receita total do Fundeb Realizada",
        "VAAF",
        "VAAT anterior à Complementação-VAAT (art. 16, IV) (R$)",
        "VAAT com a Complementação da União-VAAT (art. 16, V) (R$)",
        "Complementação da União-VAAT (art. 16, VI) (R$)",
        "Complementação da União-VAAR (R$)",
        "VAAT Mínimo Brasil",
    ]

    for c in num_cols:
        if c in df.columns:
            df[c] = _coerce_numeric(df[c])

    if "ANO" in df.columns:
        df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce").astype("Int64")
    if "Código IBGE" in df.columns:
        df["Código IBGE"] = pd.to_numeric(df["Código IBGE"], errors="coerce").astype("Int64")

    # Colunas derivadas
    df["Fundeb_Base"] = df.get("Receita total do Fundeb Realizada", 0)
    df["Compl_VAAF"] = df.get("VAAF", 0).fillna(0)
    df["Compl_VAAT"] = df.get("Complementação da União-VAAT (art. 16, VI) (R$)", 0).fillna(0)
    df["Compl_VAAR"] = df.get("Complementação da União-VAAR (R$)", 0).fillna(0)

    df["Fundeb_Total"] = (
        df["Fundeb_Base"] +
        df["Compl_VAAF"] +
        df["Compl_VAAT"] +
        df["Compl_VAAR"]
    )

    df["ICMS_Educacional"] = df.get("ICMS Educacional", 0).fillna(0)
    df["ICMS_CotaParte"] = df.get("Cota-parte ICMS Realizada", np.nan)

    df["Orcamento_Total"] = df.get("Orçamento", np.nan)
    df["Despesa_Educacao"] = df.get("Despesa Educação", np.nan)

    df["Recursos_Educacao_Ampliados"] = df["Fundeb_Total"] + df["ICMS_Educacional"]

    df["Dep_Fundeb_orcamento"] = df["Fundeb_Total"] / df["Orcamento_Total"]
    df["Dep_Fundeb_despesa_educ"] = df["Fundeb_Total"] / df["Despesa_Educacao"]

    if not df_vaat_hab.empty and "Código IBGE" in df_vaat_hab.columns:
        df_vaat_hab["Código IBGE"] = pd.to_numeric(df_vaat_hab["Código IBGE"], errors="coerce").astype("Int64")
        df = df.merge(
            df_vaat_hab[["Código IBGE", "Veficação  § 4º do art. 13 da  Lei nº 14.113/20"]],
            on="Código IBGE",
            how="left"
        )
        df.rename(
            columns={"Veficação  § 4º do art. 13 da  Lei nº 14.113/20": "Status_VAAT_2026"},
            inplace=True
        )

    return df


# ================================================================
# BLOCO 2b – CARREGAMENTO DO MAPA (GEOJSON)
# ================================================================
@st.cache_data(show_spinner=True)
def carregar_mapa_es():
    caminho_geo = "es_municipios.geojson"  # mesmo nível do fundeb.py

    if not os.path.exists(caminho_geo):
        st.error(
            "Arquivo 'es_municipios.geojson' não encontrado.\n\n"
            "Coloque o arquivo na mesma pasta do 'fundeb.py'."
        )
        st.stop()

    with open(caminho_geo, "r", encoding="utf-8") as f:
        geojson_es = json.load(f)

    return geojson_es


df = carregar_dados()
mapa_es = carregar_mapa_es()

# Código IBGE como string (7 dígitos) para ligar com o mapa
if "Código IBGE" in df.columns:
    df["Codigo_IBGE_str"] = (
        df["Código IBGE"]
        .astype("Int64")
        .astype(str)
        .str.zfill(7)
    )

# ================================================================
# BLOCO 3 – SIDEBAR E NAVEGAÇÃO
# ================================================================
st.sidebar.image("assets/logotipo_zetta_branco.png", use_container_width=True)
st.sidebar.title("Navegação")

anos_disponiveis = sorted([int(a) for a in df["ANO"].dropna().unique()])
ano_sel = st.sidebar.selectbox("Ano de análise", anos_disponiveis, index=len(anos_disponiveis)-1)

municipios = sorted(df["MUNICÍPIO"].astype(str).unique())
municipio_sel = st.sidebar.selectbox("Município (para análises focadas)", municipios)

menu = st.sidebar.radio(
    "Escolha a seção:",
    [
        "📊 Visão geral dos recursos",
        "💰 Fundeb – Diagnóstico",
        "🏛️ Complementações da União (VAAT & VAAR)",
        "📈 Comparativos e cruzamentos",
        "🗺️ Mapa estadual (visão conceitual)",
        "💡 Insights automáticos",
        "📎 Downloads"
    ],
    index=0
)

df_ano = df[df["ANO"] == ano_sel].copy()

# ================================================================
# BLOCO 4 – SEÇÃO: VISÃO GERAL DOS RECURSOS
# ================================================================
if menu == "📊 Visão geral dos recursos":
    st.title("📊 Visão geral dos recursos educacionais")

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        # Agregados estaduais
        total_fundeb_base = df_ano["Fundeb_Base"].sum()
        total_compl = (df_ano["Compl_VAAF"] + df_ano["Compl_VAAT"] + df_ano["Compl_VAAR"]).sum()
        total_icms_educ = df_ano["ICMS_Educacional"].sum()

        total_orcamento = df_ano["Orcamento_Total"].sum()
        total_desp_educ = df_ano["Despesa_Educacao"].sum()

        dep_fundeb_educ = total_fundeb_base / total_desp_educ if total_desp_educ > 0 else np.nan
        dep_fundeb_orc = total_fundeb_base / total_orcamento if total_orcamento > 0 else np.nan

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="big-card">
                <h3>Fundeb base – {ano_sel}</h3>
                <h1 style='font-size:34px;margin-top:-4px;'>{formatar_reais(total_fundeb_base)}</h1>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="big-card">
                <h3>Complementações (VAAF+VAAT+VAAR)</h3>
                <h1 style='font-size:34px;margin-top:-4px;'>{formatar_reais(total_compl)}</h1>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="big-card">
                <h3>ICMS Educacional – {ano_sel}</h3>
                <h1 style='font-size:34px;margin-top:-4px;'>{formatar_reais(total_icms_educ)}</h1>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"""
        **Peso do Fundeb base:**

        • Fundeb base / Despesa em educação: 
        **{(dep_fundeb_educ*100 if pd.notna(dep_fundeb_educ) else 0):.1f}%**  
        • Fundeb base / Orçamento total da prefeitura:
        **{(dep_fundeb_orc*100 if pd.notna(dep_fundeb_orc) else 0):.1f}%**
        """)

        st.markdown("---")
        st.subheader("Evolução anual – Fundeb base, complementações e ICMS Educacional")

        evol = (
            df.groupby("ANO", as_index=False)
            .agg(
                Fundeb_Base=("Fundeb_Base", "sum"),
                Complementacoes=("Compl_VAAF", "sum"),
                Compl_VAAT=("Compl_VAAT", "sum"),
                Compl_VAAR=("Compl_VAAR", "sum"),
                ICMS_Educacional=("ICMS_Educacional", "sum")
            )
            .dropna(subset=["ANO"])
            .sort_values("ANO")
        )
        evol["Complementacoes"] = evol["Complementacoes"] + evol["Compl_VAAT"] + evol["Compl_VAAR"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=evol["ANO"], y=evol["Fundeb_Base"],
            mode="lines+markers", name="Fundeb base"
        ))
        fig.add_trace(go.Scatter(
            x=evol["ANO"], y=evol["Complementacoes"],
            mode="lines+markers", name="Complementações (VAAF+VAAT+VAAR)"
        ))
        fig.add_trace(go.Scatter(
            x=evol["ANO"], y=evol["ICMS_Educacional"],
            mode="lines+markers", name="ICMS Educacional"
        ))
        fig.update_layout(
            template="simple_white",
            height=420,
            xaxis_title="Ano",
            yaxis_title="Valor (R$)",
            title="Evolução dos principais recursos educacionais (Estado + municípios do ES)"
        )
        st.plotly_chart(fig, use_container_width=True)

# ================================================================
# BLOCO 5 – SEÇÃO: FUNDEB – DIAGNÓSTICO
# ================================================================
elif menu == "💰 Fundeb – Diagnóstico":
    st.title("💰 Fundeb – Diagnóstico por município")

    df_mun = df[df["MUNICÍPIO"] == municipio_sel].copy()
    df_mun = df_mun.sort_values("ANO")

    if df_mun.empty:
        st.warning("Não há dados para o município selecionado.")
    else:
        st.markdown(f"### {municipio_sel} – trajetória do Fundeb")

        fig_fund_mun = px.bar(
            df_mun,
            x="ANO",
            y="Fundeb_Total",
            labels={"ANO": "Ano", "Fundeb_Total": "Fundeb total (R$)"},
        )
        fig_fund_mun.update_layout(
            template="simple_white",
            height=420,
            yaxis_title="Fundeb total (R$)",
            title=f"Evolução do Fundeb (base + complementações) – {municipio_sel}"
        )
        st.plotly_chart(fig_fund_mun, use_container_width=True)

        st.markdown("#### Crescimento ou queda ano a ano do Fundeb")

        base_tab = df_mun[["ANO", "Fundeb_Base", "Fundeb_Total"]].copy()
        base_tab = base_tab.sort_values("ANO")
        base_tab["Diferença absoluta (Fundeb Total)"] = base_tab["Fundeb_Total"].diff()
        base_tab["Diferença percentual (Fundeb Total)"] = base_tab["Fundeb_Total"].pct_change()

        base_exib = base_tab.copy()
        base_exib["Fundeb_Base"] = base_exib["Fundeb_Base"].map(formatar_reais)
        base_exib["Fundeb_Total"] = base_exib["Fundeb_Total"].map(formatar_reais)
        base_exib["Diferença absoluta (Fundeb Total)"] = base_exib["Diferença absoluta (Fundeb Total)"].map(
            formatar_reais
        )
        base_exib["Diferença percentual (Fundeb Total)"] = base_exib["Diferença percentual (Fundeb Total)"].map(
            lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "-"
        )

        st.dataframe(
            base_exib.set_index("ANO"),
            use_container_width=True
        )

        st.caption(
            "Fundeb_Base = receita do Fundeb antes das complementações. "
            "Fundeb_Total = Fundeb_Base + VAAF + VAAT + VAAR."
        )

# ================================================================
# BLOCO 6 – SEÇÃO: COMPLEMENTAÇÕES DA UNIÃO (VAAT & VAAR)
# ================================================================
elif menu == "🏛️ Complementações da União (VAAT & VAAR)":
    st.title("🏛️ Complementações da União – VAAT & VAAR")

    st.info(
        "O Espírito Santo, por não estar abaixo do valor mínimo por aluno do VAAF, "
        "não recebe a complementação VAAF – nem o Estado, nem seus municípios. "
        "Por isso, os valores de VAAF permanecem zerados nesta base."
    )

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        # ---------------- VAAT ----------------
        st.subheader("🔹 Complementação VAAT – mínimo Brasil, valores e complementos")

        df_vaat = df_ano.copy()
        df_vaat["Recebe_VAAT"] = df_vaat["Compl_VAAT"] > 0

        col_vaat1, col_vaat2 = st.columns([1.4, 1])
        with col_vaat1:
            qtde_recebe = int(df_vaat["Recebe_VAAT"].sum())
            st.markdown(f"""
            <div class="white-card">
                <h4>Municípios que recebem VAAT – {ano_sel}</h4>
                <h2 style='margin-top:-4px;'>{qtde_recebe} de {len(df_vaat)}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col_vaat2:
            valor_total_vaat = df_vaat["Compl_VAAT"].sum()
            st.markdown(f"""
            <div class="small-card">
                <h4>Total de complementação VAAT</h4>
                <h2 style='margin-top:-4px;'>{formatar_reais(valor_total_vaat)}</h2>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### VAAT mínimo, valor com complementação e complementação recebida")
        cols_exibir = [
            "MUNICÍPIO",
            "VAAT Mínimo Brasil",
            "VAAT anterior à Complementação-VAAT (art. 16, IV) (R$)",
            "VAAT com a Complementação da União-VAAT (art. 16, V) (R$)",
            "Compl_VAAT",
        ]
        df_vaat_sorted = df_vaat.sort_values("Compl_VAAT", ascending=False)
        df_vaat_tab = df_vaat_sorted[cols_exibir].copy()
        df_vaat_tab.rename(columns={
            "VAAT Mínimo Brasil": "VAAT mínimo (Brasil)",
            "VAAT anterior à Complementação-VAAT (art. 16, IV) (R$)": "VAAT antes da compl. (R$)",
            "VAAT com a Complementação da União-VAAT (art. 16, V) (R$)": "VAAT após compl. (R$)",
            "Compl_VAAT": "Complementação VAAT (R$)",
        }, inplace=True)

        for c in [
            "VAAT mínimo (Brasil)",
            "VAAT antes da compl. (R$)",
            "VAAT após compl. (R$)",
            "Complementação VAAT (R$)",
        ]:
            df_vaat_tab[c] = df_vaat_tab[c].map(formatar_reais)

        st.dataframe(df_vaat_tab, use_container_width=True, hide_index=True)

        # Estatísticas VAAT (mín, mediana, média, máx + município selecionado)
        st.markdown("#### Estatísticas da complementação VAAT")
        valores_vaat_validos = df_vaat["Compl_VAAT"][df_vaat["Compl_VAAT"] > 0]
        if not valores_vaat_validos.empty:
            med_vaat = valores_vaat_validos.median()
            media_vaat = valores_vaat_validos.mean()
            minimo_vaat = valores_vaat_validos.min()
            maximo_vaat = valores_vaat_validos.max()
            valor_mun_vaat = df_vaat.loc[df_vaat["MUNICÍPIO"] == municipio_sel, "Compl_VAAT"]
            valor_mun_vaat = float(valor_mun_vaat.iloc[0]) if not valor_mun_vaat.empty else np.nan

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Mínimo (entre os que recebem)", formatar_reais(minimo_vaat))
            c2.metric("Mediana", formatar_reais(med_vaat))
            c3.metric("Média", formatar_reais(media_vaat))
            c4.metric("Máximo", formatar_reais(maximo_vaat))
            c5.metric(f"{municipio_sel}", formatar_reais(valor_mun_vaat))
        else:
            st.info("Nenhum município recebeu VAAT no ano selecionado na base utilizada.")

        st.markdown("#### Mapa – Municípios que recebem VAAT")
        df_vaat_mapa = df_vaat.copy()
        df_vaat_mapa["Codigo_IBGE_str"] = (
            df_vaat_mapa["Código IBGE"]
            .astype("Int64")
            .astype(str)
            .str.zfill(7)
        )

        fig_vaat_mapa = px.choropleth(
            df_vaat_mapa,
            geojson=mapa_es,
            locations="Codigo_IBGE_str",
            featureidkey="properties.CD_MUN",
            color="Compl_VAAT",
            hover_name="MUNICÍPIO",
            color_continuous_scale="Purples",
            labels={"Compl_VAAT": "VAAT (R$)"},
        )
        fig_vaat_mapa.update_geos(fitbounds="locations", visible=False)
        fig_vaat_mapa.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=500,
            coloraxis_colorbar_title="VAAT (R$)"
        )
        st.plotly_chart(fig_vaat_mapa, use_container_width=True)

        st.markdown("---")
        st.subheader("🔹 Complementação VAAR – habilitação, ranking e disparidades")

        df_vaar = df_ano.copy()
        df_vaar["Recebe_VAAR"] = df_vaar["Compl_VAAR"] > 0
        df_vaar["Status_VAAR"] = np.where(df_vaar["Recebe_VAAR"], "Habilitado (recebeu VAAR)", "Não habilitado")

        # Cards para VAAR
        col_vaar1, col_vaar2 = st.columns([1.4, 1])
        with col_vaar1:
            qtde_recebe_vaar = int(df_vaar["Recebe_VAAR"].sum())
            st.markdown(f"""
            <div class="white-card">
                <h4>Municípios que recebem VAAR – {ano_sel}</h4>
                <h2 style='margin-top:-4px;'>{qtde_recebe_vaar} de {len(df_vaar)}</h2>
            </div>
            """, unsafe_allow_html=True)
        with col_vaar2:
            valor_total_vaar = df_vaar["Compl_VAAR"].sum()
            st.markdown(f"""
            <div class="small-card">
                <h4>Total de complementação VAAR</h4>
                <h2 style='margin-top:-4px;'>{formatar_reais(valor_total_vaar)}</h2>
            </div>
            """, unsafe_allow_html=True)

        contagem = df_vaar["Status_VAAR"].value_counts().reset_index()
        contagem.columns = ["Status_VAAR", "Quantidade"]

        fig_status = px.bar(
            contagem,
            x="Status_VAAR",
            y="Quantidade",
            text="Quantidade",
            labels={"Status_VAAR": "", "Quantidade": "Municípios"},
        )
        fig_status.update_layout(
            template="simple_white",
            height=420,
            title="Municípios habilitados vs. não habilitados ao VAAR (a partir dos recebimentos)",
            xaxis_tickangle=-10
        )
        st.plotly_chart(fig_status, use_container_width=True)

        st.markdown("#### Ranking VAAR – valores recebidos por município")
        rank_vaar = df_vaar[["MUNICÍPIO", "Compl_VAAR"]].copy()
        rank_vaar = rank_vaar.sort_values("Compl_VAAR", ascending=False)

        rank_vaar_exib = rank_vaar.copy()
        rank_vaar_exib["Compl_VAAR"] = rank_vaar_exib["Compl_VAAR"].map(
            lambda v: formatar_reais(v) if v > 0 else "-"
        )

        st.dataframe(rank_vaar_exib, use_container_width=True, hide_index=True)

        st.markdown("#### Disparidade nos valores de VAAR recebidos")
        valores_validos = df_vaar["Compl_VAAR"][df_vaar["Compl_VAAR"] > 0]
        if not valores_validos.empty:
            med = valores_validos.median()
            media = valores_validos.mean()
            minimo = valores_validos.min()
            maximo = valores_validos.max()
            valor_mun_vaar = df_vaar.loc[df_vaar["MUNICÍPIO"] == municipio_sel, "Compl_VAAR"]
            valor_mun_vaar = float(valor_mun_vaar.iloc[0]) if not valor_mun_vaar.empty else np.nan

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Mínimo (entre os que recebem)", formatar_reais(minimo))
            c2.metric("Mediana", formatar_reais(med))
            c3.metric("Média", formatar_reais(media))
            c4.metric("Máximo", formatar_reais(maximo))
            c5.metric(f"{municipio_sel}", formatar_reais(valor_mun_vaar))
        else:
            st.info("Nenhum município recebeu VAAR no ano selecionado na base utilizada.")

        st.markdown("#### Mapa – Municípios que receberam VAAR")
        df_vaar_mapa = df_vaar.copy()
        df_vaar_mapa["Codigo_IBGE_str"] = (
            df_vaar_mapa["Código IBGE"]
            .astype("Int64")
            .astype(str)
            .str.zfill(7)
        )

        fig_vaar_mapa = px.choropleth(
            df_vaar_mapa,
            geojson=mapa_es,
            locations="Codigo_IBGE_str",
            featureidkey="properties.CD_MUN",
            color="Compl_VAAR",
            hover_name="MUNICÍPIO",
            color_continuous_scale="Tealrose",
            labels={"Compl_VAAR": "VAAR (R$)"},
        )
        fig_vaar_mapa.update_geos(fitbounds="locations", visible=False)
        fig_vaar_mapa.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=500,
            coloraxis_colorbar_title="VAAR (R$)"
        )
        st.plotly_chart(fig_vaar_mapa, use_container_width=True)

# ================================================================
# BLOCO 7 – SEÇÃO: COMPARATIVOS E CRUZAMENTOS
# ================================================================
elif menu == "📈 Comparativos e cruzamentos":
    st.title("📈 Comparativos e cruzamentos – Fundeb, ICMS e complementações")

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        st.markdown("### Quanto cada município recebe somando todas as fontes (Fundeb + VAAT + VAAR + ICMS Educacional)")

        df_tot = df_ano.copy()
        df_tot["Total_Receitas_Chave"] = df_tot["Fundeb_Total"] + df_tot["ICMS_Educacional"]
        df_tot = df_tot.sort_values("Total_Receitas_Chave", ascending=True)

        # Cores destacando o município selecionado
        def cores_por_municipio(series_mun, cor_normal, cor_dest):
            return [
                cor_dest if m == municipio_sel else cor_normal
                for m in series_mun
            ]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=df_tot["MUNICÍPIO"],
            x=df_tot["Fundeb_Base"],
            name="Fundeb base",
            orientation="h",
            marker=dict(color=cores_por_municipio(df_tot["MUNICÍPIO"], "#C2A4CF", "#3A0057")),
        ))
        fig_bar.add_trace(go.Bar(
            y=df_tot["MUNICÍPIO"],
            x=df_tot["Compl_VAAT"],
            name="Compl. VAAT",
            orientation="h",
            marker=dict(color=cores_por_municipio(df_tot["MUNICÍPIO"], "#B3E6FF", "#0077B6")),
        ))
        fig_bar.add_trace(go.Bar(
            y=df_tot["MUNICÍPIO"],
            x=df_tot["Compl_VAAR"],
            name="Compl. VAAR",
            orientation="h",
            marker=dict(color=cores_por_municipio(df_tot["MUNICÍPIO"], "#FFE0B2", "#FF8C00")),
        ))
        fig_bar.add_trace(go.Bar(
            y=df_tot["MUNICÍPIO"],
            x=df_tot["ICMS_Educacional"],
            name="ICMS Educacional",
            orientation="h",
            marker=dict(color=cores_por_municipio(df_tot["MUNICÍPIO"], "#D0F0C0", "#228B22")),
        ))
        fig_bar.update_layout(
            barmode="stack",
            template="simple_white",
            height=700,
            title=f"Recursos educacionais por município – {ano_sel}",
            xaxis_title="Valor (R$)",
            yaxis_title="Município",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("### Estrutura dos recursos educacionais por município (participação percentual)")
        df_dep = df_ano.copy()
        df_dep["Total_Recursos"] = df_dep["Fundeb_Base"] + df_dep["Compl_VAAT"] + df_dep["Compl_VAAR"] + df_dep["ICMS_Educacional"]
        df_dep = df_dep[df_dep["Total_Recursos"] > 0].copy()

        for col in ["Fundeb_Base", "Compl_VAAT", "Compl_VAAR", "ICMS_Educacional"]:
            df_dep[f"perc_{col}"] = df_dep[col] / df_dep["Total_Recursos"]

        df_long = df_dep.melt(
            id_vars=["MUNICÍPIO"],
            value_vars=["perc_Fundeb_Base", "perc_Compl_VAAT", "perc_Compl_VAAR", "perc_ICMS_Educacional"],
            var_name="Fonte",
            value_name="Percentual"
        )
        df_long["Fonte"] = df_long["Fonte"].replace({
            "perc_Fundeb_Base": "Fundeb base",
            "perc_Compl_VAAT": "Compl. VAAT",
            "perc_Compl_VAAR": "Compl. VAAR",
            "perc_ICMS_Educacional": "ICMS Educacional",
        })

        fig_stack = px.bar(
            df_long,
            y="MUNICÍPIO",
            x="Percentual",
            color="Fonte",
            orientation="h",
            labels={"MUNICÍPIO": "Município", "Percentual": "Participação no total de recursos"},
        )
        fig_stack.update_layout(
            template="simple_white",
            height=800,
            xaxis_tickformat=".0%",
            title="Estrutura percentual dos recursos educacionais por município",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.0)
        )
        st.plotly_chart(fig_stack, use_container_width=True)

        st.markdown("### Municípios com pouco ICMS Educacional e muito VAAR (e o contrário)")
        df_disp = df_ano.copy()
        df_disp = df_disp[(df_disp["ICMS_Educacional"] > 0) | (df_disp["Compl_VAAR"] > 0)]

        if df_disp.empty:
            st.info("Não há dados suficientes para comparar ICMS Educacional e VAAR.")
        else:
            fig_scatter = px.scatter(
                df_disp,
                x="ICMS_Educacional",
                y="Compl_VAAR",
                text="MUNICÍPIO",
                labels={"ICMS_Educacional": "ICMS Educacional (R$)", "Compl_VAAR": "VAAR (R$)"},
            )
            fig_scatter.update_traces(textposition="top center", marker=dict(size=10))
            fig_scatter.update_layout(
                template="simple_white",
                height=520,
                title="Relação entre ICMS Educacional e VAAR por município"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# ================================================================
# BLOCO 8 – SEÇÃO: MAPA ESTADUAL (AGORA REAL)
# ================================================================
elif menu == "🗺️ Mapa estadual (visão conceitual)":
    st.title("🗺️ Mapa estadual – recursos educacionais")

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        st.markdown("Escolha qual indicador deseja visualizar no mapa:")

        opcoes_indicador = {
            "Fundeb base (Receita total do Fundeb Realizada)": "Fundeb_Base",
            "Complementações (VAAF + VAAT + VAAR)": "Compl_Total",
            "Fundeb total (base + complementações)": "Fundeb_Total",
            "ICMS Educacional": "ICMS_Educacional",
        }

        df_mapa = df_ano.copy()
        df_mapa["Compl_Total"] = (
            df_mapa["Compl_VAAF"] +
            df_mapa["Compl_VAAT"] +
            df_mapa["Compl_VAAR"]
        )

        escolha = st.selectbox(
            "Indicador para o mapa:",
            list(opcoes_indicador.keys())
        )
        col_ind = opcoes_indicador[escolha]

        df_mapa["Codigo_IBGE_str"] = (
            df_mapa["Código IBGE"]
            .astype("Int64")
            .astype(str)
            .str.zfill(7)
        )

        fig_mapa = px.choropleth(
            df_mapa,
            geojson=mapa_es,
            locations="Codigo_IBGE_str",
            featureidkey="properties.CD_MUN",
            color=col_ind,
            hover_name="MUNICÍPIO",
            color_continuous_scale="Viridis",
            labels={col_ind: "Valor (R$)"},
        )
        fig_mapa.update_geos(fitbounds="locations", visible=False)
        fig_mapa.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=520,
            coloraxis_colorbar_title="R$"
        )

        st.plotly_chart(fig_mapa, use_container_width=True)

# ================================================================
# BLOCO 9 – SEÇÃO: INSIGHTS AUTOMÁTICOS
# ================================================================
elif menu == "💡 Insights automáticos":
    st.title("💡 Insights automáticos – alertas estratégicos")

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        st.markdown(f"### Ano de referência: {ano_sel}")

        anos_ordenados = sorted(df["ANO"].dropna().unique())
        insights = []

        # 1) Fundeb caindo há 3 anos
        if len(anos_ordenados) >= 3:
            ultimos3 = anos_ordenados[-3:]
            df_3 = df[df["ANO"].isin(ultimos3)].copy()

            queda_mun = []
            for mun, grupo in df_3.groupby("MUNICÍPIO"):
                g = grupo.sort_values("ANO")
                if len(g) == 3:
                    vals = g["Fundeb_Total"].values
                    if np.all(np.diff(vals) < 0):
                        queda_mun.append(mun)
            if queda_mun:
                insights.append(
                    f"- ⚠️ **Fundeb em queda contínua nos últimos 3 anos** em: {', '.join(sorted(queda_mun))}."
                )

        # 2) Municípios não habilitados ao VAAR (sem recebimento)
        df_vaar_ano = df_ano.copy()
        nao_hab = df_vaar_ano.loc[df_vaar_ano["Compl_VAAR"] <= 0, "MUNICÍPIO"].tolist()
        if nao_hab:
            insights.append(
                f"- 🚫 **Municípios que não receberam VAAR em {ano_sel}** (podem estar deixando recursos na mesa): "
                f"{', '.join(sorted(nao_hab))}."
            )

        # 3) Dependência elevada do Fundeb (>= 50% da despesa em educação)
        dep_alta = df_ano[df_ano["Dep_Fundeb_despesa_educ"] >= 0.50]
        if not dep_alta.empty:
            lista = dep_alta["MUNICÍPIO"].tolist()
            insights.append(
                f"- 📌 **Municípios em que o Fundeb representa 50% ou mais da despesa em educação**: "
                f"{', '.join(sorted(lista))}."
            )

        # 4) Municípios com alta receita de Fundeb, mas baixa receita de ICMS Educacional
        q3_fundeb = df_ano["Fundeb_Total"].quantile(0.75)
        q1_icms = df_ano["ICMS_Educacional"].quantile(0.25)
        filtro_oportunidade = df_ano[
            (df_ano["Fundeb_Total"] >= q3_fundeb) &
            (df_ano["ICMS_Educacional"] <= q1_icms)
        ]
        if not filtro_oportunidade.empty:
            insights.append(
                "- 💡 **Municípios com Fundeb elevado, mas ICMS Educacional relativamente baixo** "
                "(podem se beneficiar de melhor desempenho educacional e gestão das condicionalidades): "
                f"{', '.join(sorted(filtro_oportunidade['MUNICÍPIO'].tolist()))}."
            )

        if insights:
            st.markdown("#### Principais alertas gerados automaticamente")
            for item in insights:
                st.markdown(item)
        else:
            st.info("Não foram identificados alertas relevantes com as regras atuais. Mesmo assim, o painel "
                    "pode ser explorado para identificar oportunidades específicas.")

# ================================================================
# BLOCO 10 – SEÇÃO: DOWNLOADS
# ================================================================
elif menu == "📎 Downloads":
    st.title("📎 Downloads – bases consolidadas")

    st.markdown("""
    Aqui você pode exportar as bases utilizadas no painel para aprofundar análises
    em Excel, R, Python ou qualquer outra ferramenta.
    """)

    csv_completo = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")

    st.download_button(
        "⬇️ Baixar base completa (todos os anos e municípios)",
        data=csv_completo,
        file_name="fundeb_icms_complementacoes_es.csv",
        mime="text/csv",
    )

    if not df_ano.empty:
        csv_ano = df_ano.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            f"⬇️ Baixar base filtrada para {ano_sel}",
            data=csv_ano,
            file_name=f"fundeb_icms_complementacoes_es_{ano_sel}.csv",
            mime="text/csv",
        )

# ================================================================
# RODAPÉ
# ================================================================
st.markdown(
    """
    <hr style='margin-top:40px;'>
    <div style='text-align:center; color:#7E7E7E; font-size:13px;'>
        Desenvolvido por <b>Zetta Inteligência em Dados</b> · Painel Fundeb, Complementações & ICMS · 2025
    </div>
    """,
    unsafe_allow_html=True
)
