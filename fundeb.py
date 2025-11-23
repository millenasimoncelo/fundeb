# ================================================================
# app_fundeb.py – Painel Fundeb, VAAT, VAAR & ICMS – Zetta
# ================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
# BLOCO 2 – CARREGAMENTO UNIVERSAL DE DADOS (COMPLETO E CORRETO)
# ================================================================
@st.cache_data(show_spinner=True)
def carregar_dados():

    import os
    import pandas as pd
    import numpy as np

    # Nome exato do arquivo
    nome_arquivo = "Levantamento LOA municípios ES - 2020 a 2025.xlsx"

    # Tenta localizar em caminhos relativos
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

    # Carrega aba principal
    df = pd.read_excel(caminho_encontrado, sheet_name="Planilha1")

    # Se existir aba de habilitação VAAT 2026, carrega
    abas = pd.ExcelFile(caminho_encontrado).sheet_names
    if "Habilitação VAAT 2026" in abas:
        df_vaat_hab = pd.read_excel(caminho_encontrado, sheet_name="Habilitação VAAT 2026")
    else:
        df_vaat_hab = pd.DataFrame()

    # ------------------------------------------------------------
    # Padronização de colunas
    # ------------------------------------------------------------
    df.columns = [c.strip() for c in df.columns]

    def _coerce_numeric(col):
        if pd.api.types.is_numeric_dtype(col):
            return col
        col = col.astype(str)
        col = col.str.replace(".", "", regex=False)
        col = col.str.replace(",", ".", regex=False)
        col = col.replace({"-": np.nan, "--": np.nan, "nan": np.nan, "None": np.nan, "": np.nan})
        return pd.to_numeric(col, errors="coerce")

    # Lista das colunas numéricas
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

    # Coerção para ANO e Código IBGE
    if "ANO" in df.columns:
        df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce").astype("Int64")
    if "Código IBGE" in df.columns:
        df["Código IBGE"] = pd.to_numeric(df["Código IBGE"], errors="coerce").astype("Int64")

    # ------------------------------------------------------------
    # Criação das colunas derivadas oficiais
    # ------------------------------------------------------------
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

    # Receita ampliada
    df["Recursos_Educacao_Ampliados"] = df["Fundeb_Total"] + df["ICMS_Educacional"]

    # Dependências relativas
    df["Dep_Fundeb_orcamento"] = df["Fundeb_Total"] / df["Orcamento_Total"]
    df["Dep_Fundeb_despesa_educ"] = df["Fundeb_Total"] / df["Despesa_Educacao"]

    # Junta habilitação VAAT 2026, se existir
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


df = carregar_dados()


# ================================================================
# BLOCO 3 – SIDEBAR E NAVEGAÇÃO
# ================================================================
st.sidebar.image("assets/logotipo_zetta_branco.png", use_container_width=True)
st.sidebar.title("Navegação")

anos_disponiveis = sorted([int(a) for a in df["ANO"].dropna().unique()])
ano_default = anos_disponiveis[-1] if anos_disponiveis else None
ano_sel = st.sidebar.selectbox("Ano de análise", anos_disponiveis, index=len(anos_disponiveis)-1)

municipios = sorted(df["MUNICÍPIO"].astype(str).unique())
municipio_sel = st.sidebar.selectbox("Município (para análises focadas)", municipios)

# (Deixei o seletor preparado para futuro per capita, mas ainda não uso.)
st.sidebar.radio(
    "Escala de valor",
    ["Total (R$)", "Per capita (R$ por habitante/matrícula)"],
    index=0,
    help="No momento, os cálculos per capita dependem da futura inclusão de coluna de matrículas/população."
)

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
        total_fundeb = df_ano["Fundeb_Total"].sum()
        total_icms_educ = df_ano["ICMS_Educacional"].sum()
        total_orcamento = df_ano["Orcamento_Total"].sum()
        total_desp_educ = df_ano["Despesa_Educacao"].sum()

        dep_fundeb_educ = total_fundeb / total_desp_educ if total_desp_educ > 0 else np.nan
        dep_fundeb_orc = total_fundeb / total_orcamento if total_orcamento > 0 else np.nan

        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown(f"""
            <div class="big-card">
                <h3>Fundeb (base + complementações) – {ano_sel}</h3>
                <h1 style='font-size:40px;margin-top:-4px;'>R$ {total_fundeb:,.0f}</h1>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="small-card">
                <h4>ICMS Educacional – {ano_sel}</h4>
                <h2 style='margin-top:-4px;'>R$ {total_icms_educ:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f"""
            <div class="white-card">
                <h4>Fundeb / Despesa em Educação</h4>
                <h2 style='margin-top:-4px;'>{(dep_fundeb_educ*100 if pd.notna(dep_fundeb_educ) else 0):.1f}%</h2>
                <p style='font-size:12px;margin-top:4px;'>Dependência da rede municipal em relação ao Fundeb.</p>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="white-card">
                <h4>Fundeb / Orçamento Municipal Total</h4>
                <h2 style='margin-top:-4px;'>{(dep_fundeb_orc*100 if pd.notna(dep_fundeb_orc) else 0):.1f}%</h2>
                <p style='font-size:12px;margin-top:4px;'>Peso do Fundeb no orçamento anual da prefeitura.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Evolução anual do Fundeb (base + complementações)")

        evol = (
            df.groupby("ANO", as_index=False)["Fundeb_Total"]
            .sum()
            .dropna(subset=["ANO"])
            .sort_values("ANO")
        )
        fig = px.line(
            evol,
            x="ANO",
            y="Fundeb_Total",
            markers=True,
            labels={"ANO": "Ano", "Fundeb_Total": "Fundeb (R$)"},
        )
        fig.update_layout(
            template="simple_white",
            height=420,
            yaxis_tickprefix="R$ ",
            title="Evolução do Fundeb total (Estado + municípios do ES)"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Dependência municipal do Fundeb – Despesa em Educação")
        dep_mun = df_ano.copy()
        dep_mun = dep_mun.dropna(subset=["Dep_Fundeb_despesa_educ"])
        dep_mun = dep_mun.sort_values("Dep_Fundeb_despesa_educ", ascending=False)

        top_dep = dep_mun.head(15)
        if not top_dep.empty:
            fig_dep = px.bar(
                top_dep,
                x="Dep_Fundeb_despesa_educ",
                y="MUNICÍPIO",
                orientation="h",
                labels={"Dep_Fundeb_despesa_educ": "Fundeb / Despesa Educação", "MUNICÍPIO": "Município"},
            )
            fig_dep.update_layout(
                template="simple_white",
                height=520,
                xaxis_tickformat=".0%",
                title="Municípios mais dependentes do Fundeb para financiar a educação"
            )
            st.plotly_chart(fig_dep, use_container_width=True)
        else:
            st.info("Ainda não há dados suficientes de despesa em educação para calcular essa dependência.")

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
            yaxis_tickprefix="R$ ",
            title=f"Evolução do Fundeb (base + complementações) – {municipio_sel}"
        )
        st.plotly_chart(fig_fund_mun, use_container_width=True)

        st.markdown("#### Crescimento ou queda ano a ano do Fundeb")
        base_tab = df_mun[["ANO", "Fundeb_Base", "Fundeb_Total"]].copy()
        base_tab = base_tab.sort_values("ANO")
        base_tab["Diferença absoluta (Fundeb Total)"] = base_tab["Fundeb_Total"].diff()
        base_tab["Diferença percentual (Fundeb Total)"] = base_tab["Fundeb_Total"].pct_change()

        # Apenas anos 2023–2025, se existirem
        anos_interesse = [2023, 2024, 2025]
        base_tab = base_tab[base_tab["ANO"].isin(anos_interesse)]

        base_exib = base_tab.copy()
        base_exib["Fundeb_Base"] = base_exib["Fundeb_Base"].map(lambda v: f"R$ {v:,.0f}" if pd.notna(v) else "-")
        base_exib["Fundeb_Total"] = base_exib["Fundeb_Total"].map(lambda v: f"R$ {v:,.0f}" if pd.notna(v) else "-")
        base_exib["Diferença absoluta (Fundeb Total)"] = base_exib["Diferença absoluta (Fundeb Total)"].map(
            lambda v: f"R$ {v:,.0f}" if pd.notna(v) else "-"
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
        # --- VAAT: quem recebe, quanto e relação com VAAT mínimo
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
                <h2 style='margin-top:-4px;'>R$ {valor_total_vaat:,.0f}</h2>
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
        # Ordena antes pela coluna numérica, depois formata
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
            df_vaat_tab[c] = df_vaat_tab[c].map(lambda v: f"R$ {v:,.0f}" if pd.notna(v) else "-")

        st.dataframe(df_vaat_tab, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔹 Complementação VAAR – habilitação, ranking e disparidades")

        df_vaar = df_ano.copy()
        df_vaar["Recebe_VAAR"] = df_vaar["Compl_VAAR"] > 0
        df_vaar["Status_VAAR"] = np.where(df_vaar["Recebe_VAAR"], "Habilitado (recebeu VAAR)", "Não habilitado")

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
            lambda v: f"R$ {v:,.0f}" if v > 0 else "-"
        )

        st.dataframe(rank_vaar_exib, use_container_width=True, hide_index=True)

        st.markdown("#### Disparidade nos valores de VAAR recebidos")
        valores_validos = df_vaar["Compl_VAAR"][df_vaar["Compl_VAAR"] > 0]
        if not valores_validos.empty:
            med = valores_validos.median()
            media = valores_validos.mean()
            minimo = valores_validos.min()
            maximo = valores_validos.max()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Mínimo (entre os que recebem)", f"R$ {minimo:,.0f}")
            c2.metric("Mediana", f"R$ {med:,.0f}")
            c3.metric("Média", f"R$ {media:,.0f}")
            c4.metric("Máximo", f"R$ {maximo:,.0f}")
        else:
            st.info("Nenhum município recebeu VAAR no ano selecionado na base utilizada.")

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

        top = df_tot.sort_values("Total_Receitas_Chave", ascending=False).head(20)

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=top["MUNICÍPIO"],
            y=top["Fundeb_Base"],
            name="Fundeb base",
        ))
        fig_bar.add_trace(go.Bar(
            x=top["MUNICÍPIO"],
            y=top["Compl_VAAT"],
            name="Compl. VAAT",
        ))
        fig_bar.add_trace(go.Bar(
            x=top["MUNICÍPIO"],
            y=top["Compl_VAAR"],
            name="Compl. VAAR",
        ))
        fig_bar.add_trace(go.Bar(
            x=top["MUNICÍPIO"],
            y=top["ICMS_Educacional"],
            name="ICMS Educacional",
        ))
        fig_bar.update_layout(
            barmode="stack",
            template="simple_white",
            height=520,
            title=f"Top 20 municípios em recursos educacionais – {ano_sel}",
            xaxis_tickangle=-35,
            yaxis_tickprefix="R$ "
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("### Dependência do município de cada tipo de recurso (participação percentual)")
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
            x="MUNICÍPIO",
            y="Percentual",
            color="Fonte",
            labels={"MUNICÍPIO": "Município", "Percentual": "Participação no total de recursos"},
        )
        fig_stack.update_layout(
            template="simple_white",
            height=540,
            xaxis_tickangle=-35,
            yaxis_tickformat=".0%",
            title="Estrutura dos recursos educacionais por município"
        )
        st.plotly_chart(fig_stack, use_container_width=True)

        st.markdown("### Municípios com pouco ICMS Educacional e muito VAAR (e o contrário)")
        df_disp = df_ano.copy()
        # Considera apenas quem tem pelo menos um dos dois > 0
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
# BLOCO 8 – SEÇÃO: MAPA ESTADUAL (VISÃO CONCEITUAL)
# ================================================================
elif menu == "🗺️ Mapa estadual (visão conceitual)":
    st.title("🗺️ Mapa estadual – visão conceitual")

    st.warning(
        "Para exibir o mapa temático com os valores por município, será necessário "
        "conectar um arquivo GeoJSON ou shapefile dos municípios do Espírito Santo. "
        "No momento, este bloco apresenta apenas a lógica conceitual."
    )

    st.markdown("""
    **Sugestão de implementação futura:**

    1. Obter um arquivo GeoJSON com os municípios do ES (por exemplo, via IBGE).
    2. Garantir que o código IBGE do GeoJSON seja compatível com a coluna `Código IBGE` desta base.
    3. Utilizar `plotly.express.choropleth` para colorir o mapa com:
       - Fundeb_Total
       - Compl_VAAR
       - ICMS_Educacional

    Assim que o GeoJSON estiver disponível, este bloco pode ser facilmente ativado.
    """)

# ================================================================
# BLOCO 9 – SEÇÃO: INSIGHTS AUTOMÁTICOS
# ================================================================
elif menu == "💡 Insights automáticos":
    st.title("💡 Insights automáticos – alertas estratégicos")

    if df_ano.empty:
        st.warning("Não há dados para o ano selecionado.")
    else:
        st.markdown(f"### Ano de referência: {ano_sel}")

        # 1) Municípios com Fundeb caindo há 3 anos (se houver histórico)
        anos_ordenados = sorted(df["ANO"].dropna().unique())
        insights = []

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

        # 3) Dependência elevada do Fundeb (> 85% da despesa em educação)
        dep_alta = df_ano[df_ano["Dep_Fundeb_despesa_educ"] >= 0.85]
        if not dep_alta.empty:
            lista = dep_alta["MUNICÍPIO"].tolist()
            insights.append(
                f"- 📌 **Municípios em que o Fundeb representa 85% ou mais da despesa em educação**: "
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
