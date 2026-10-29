"""Charla de Inversión · Mercado en vivo (versión pública).

Lee SOLO pestañas publicadas en la web (archivo CSV público):
MAPA PUBLICO, DolarPublico y WEB PUBLICA. No usa la llave de la planilla,
así que no puede ver la cartera ni ningún monto personal.
"""

import io
import os
import re
import urllib.request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Configuración ─────────────────────────────────────────────────────────
# Código del enlace "Publicar en la web" (lo que va entre /d/e/ y /pub).
PUB_ID = "2PACX-1vQfYooArXw9l-fxotZxgysJF-3twkJ9ZpPq6FJ-zFPHIJ44aYX_ubCH23xiIbgufVru0Y8VzYDiuTmu"

GIDS = {
    "mapa": 458890457,      # MAPA PUBLICO
    "dolar": 1963614617,    # DolarPublico
    "web": 778001,          # WEB PUBLICA
}

BLOG = "https://charladeinversion.wordpress.com"
TELEGRAM = "https://t.me/charladeinversion"

NAVY = "#12304f"
TG_BLUE = "#229ed9"

st.set_page_config(
    page_title="Charla de Inversión · Mercado en vivo",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1.6rem; max-width: 1250px;}}
      .hero {{background:{NAVY}; color:#fff; border-radius:14px;
              padding:22px 26px; margin-bottom:18px;}}
      .hero h1 {{color:#fff; margin:0; font-size:2rem;}}
      .hero p {{color:#d6e2ef; margin:6px 0 0 0;}}
      .hero a {{color:#fff; font-weight:600; text-decoration:none;
                border:1px solid #ffffff55; border-radius:8px;
                padding:6px 12px; margin-right:8px; display:inline-block;
                margin-top:12px;}}
      .hero a.tg {{background:{TG_BLUE}; border-color:{TG_BLUE};}}
      .nota {{color:#6b7a8c; font-size:0.85rem;}}
      .ctx {{background:#eef5fc; border-left:4px solid {TG_BLUE};
             padding:10px 14px; border-radius:6px; margin:6px 0 14px 0;
             color:#12304f;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Lectura de datos ──────────────────────────────────────────────────────
def _csv_url(gid: int) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/e/{PUB_ID}/pub"
        f"?gid={gid}&single=true&output=csv"
    )


@st.cache_data(ttl=600, show_spinner=False)
def leer(nombre: str) -> pd.DataFrame:
    """Devuelve la pestaña como tabla de texto, sin encabezados."""
    local = os.environ.get("CHARLA_LOCAL_DATA")
    if local:
        return pd.read_csv(os.path.join(local, f"{nombre}.csv"), header=None,
                           dtype=str, keep_default_na=False)
    req = urllib.request.Request(_csv_url(GIDS[nombre]),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        texto = r.read().decode("utf-8")
    return pd.read_csv(io.StringIO(texto), header=None, dtype=str,
                       keep_default_na=False)


def num(x) -> float | None:
    """Convierte '$1.234,5', 'USD57,20', '1,71', '-4,25%' a número."""
    if x is None:
        return None
    s = str(x).strip()
    if not s or s in {"—", "-", "s/d"}:
        return None
    s = re.sub(r"[^0-9,.\-]", "", s)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_pct(v, dec=2):
    if v is None or pd.isna(v):
        return "s/d"
    return f"{v:+.{dec}f}%".replace(".", ",")


def fmt_pesos(v, dec=0):
    if v is None or pd.isna(v):
        return "s/d"
    t = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${t}"


def _col(raw: pd.DataFrame, texto: str, defecto: int) -> int:
    """Busca la columna cuyo encabezado (fila 1) contiene `texto`."""
    for i, v in enumerate(raw.iloc[0].tolist()):
        if texto.lower() in str(v).lower():
            return i
    return defecto


def tabla_mapa() -> pd.DataFrame:
    raw = leer("mapa")
    c_var = _col(raw, "Var. del d", 6)
    datos = {
        "Sector": raw.iloc[1:, 0],
        "Ticker": raw.iloc[1:, 1],
        "USD": raw.iloc[1:, 2],
        "CEDEAR": raw.iloc[1:, 3],
        "Var_txt": raw.iloc[1:, c_var],
    }
    df = pd.DataFrame({k: [str(x) for x in v.tolist()] for k, v in datos.items()})
    df = df[df["Ticker"].str.strip() != ""].copy()
    df["Sector"] = [s.strip() or "Otros" for s in df["Sector"]]
    df["Ticker"] = [t.strip() for t in df["Ticker"]]
    df["Var"] = pd.to_numeric(pd.Series([num(x) for x in df["Var_txt"]],
                                        index=df.index, dtype="object"),
                              errors="coerce")
    return df.reset_index(drop=True)


def tabla_dolar() -> dict:
    raw = leer("dolar")
    datos = {}
    for _, fila in raw.iterrows():
        clave = str(fila.iloc[0]).strip()
        if clave:
            datos[clave] = [str(v).strip() for v in fila.iloc[1:].tolist()]
    return datos


def tabla_web():
    raw = leer("web")
    get = lambda r, c: raw.iat[r, c] if r < len(raw) and c < raw.shape[1] else ""
    meta = {"fecha": get(0, 1), "contexto": get(1, 1)}

    sen = raw.iloc[4:, 0:5].copy()
    sen.columns = ["Ticker", "Señal", "RSI", "Precio CEDEAR", "Tipo"]
    sen = sen[sen["Ticker"].str.strip() != ""].reset_index(drop=True)

    inf = raw.iloc[4:, 6:9].copy()
    inf.columns = ["Mes", "Mensual", "Anual"]
    inf["Mensual"] = inf["Mensual"].map(num)
    inf["Anual"] = inf["Anual"].map(num)
    inf = inf[inf["Mensual"].notna()].reset_index(drop=True)

    ban = raw.iloc[4:, 10:13].copy()
    ban.columns = ["Fecha", "Piso", "Techo"]
    ban["Fecha"] = pd.to_datetime(ban["Fecha"], format="%d/%m/%Y",
                                  errors="coerce")
    ban["Piso"] = ban["Piso"].map(num)
    ban["Techo"] = ban["Techo"].map(num)
    ban = ban.dropna(subset=["Fecha", "Piso", "Techo"]).reset_index(drop=True)
    return meta, sen, inf, ban


def tabla_balances():
    raw = leer("web")
    get = lambda r, c: raw.iat[r, c] if r < len(raw) and c < raw.shape[1] else ""
    textos = {"noticias": get(0, 15), "resumen": get(1, 15)}
    if raw.shape[1] < 20:
        return textos, pd.DataFrame()
    bal = raw.iloc[4:, 14:20].copy()
    bal.columns = ["Empresa", "Fecha", "Resultado", "Claves", "Reaccion",
                   "Lectura"]
    bal = bal[bal["Empresa"].astype(str).str.strip() != ""]
    return textos, bal.reset_index(drop=True)


def md(texto: str) -> str:
    """Texto seguro para markdown (sin fórmulas $...$)."""
    return str(texto).replace("$", "\\$")


# ── Encabezado ────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero">
      <h1>📈 Charla de Inversión · Mercado en vivo</h1>
      <p>Mapa de CEDEARs, macro argentina y señales técnicas del día,
         con datos que se actualizan solos. Por <b>El profesor</b>.</p>
      <a href="{BLOG}" target="_blank">📝 Leer el blog</a>
      <a class="tg" href="{TELEGRAM}" target="_blank">📲 Canal de Telegram</a>
    </div>
    """,
    unsafe_allow_html=True,
)

if PUB_ID.startswith("PEGAR") and not os.environ.get("CHARLA_LOCAL_DATA"):
    st.error("Falta configurar el enlace público de la planilla (PUB_ID).")
    st.stop()

col_a, col_b = st.columns([5, 1])
with col_b:
    if st.button("🔄 Actualizar", width="stretch"):
        st.cache_data.clear()
        st.rerun()
with col_a:
    st.markdown('<span class="nota">Los datos se refrescan cada 10 minutos '
                'o con el botón.</span>', unsafe_allow_html=True)

tab_mapa, tab_macro, tab_sen, tab_bal = st.tabs(
    ["🗺️ Mercado hoy", "🌎 Macro", "🚦 Señales del día",
     "📑 Balances y noticias"]
)

# ── Mercado hoy ───────────────────────────────────────────────────────────
with tab_mapa:
    try:
        df = tabla_mapa()
    except Exception:
        st.warning("No pude leer el mapa de CEDEARs en este momento. "
                   "Probá de nuevo en unos minutos.")
        df = None

    if df is not None and len(df):
        sectores = sorted(df["Sector"].unique())
        elegidos = st.multiselect("Filtrar sectores", sectores,
                                  placeholder="Todos los sectores")
        vista = df[df["Sector"].isin(elegidos)] if elegidos else df
        con_dato = vista[vista["Var"].notna()]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Activos con dato", len(con_dato))
        m2.metric("Suben", int((con_dato["Var"] > 0).sum()))
        m3.metric("Bajan", int((con_dato["Var"] < 0).sum()))
        m4.metric("Variación promedio", fmt_pct(con_dato["Var"].mean()))

        if con_dato.empty:
            st.warning("Todavía no llegaron las variaciones del día. "
                       "Probá de nuevo en unos minutos.")
            with st.expander("Detalle técnico"):
                st.code(f"filas={len(vista)} | muestra Var: "
                        f"{vista['Var_txt'].head(5).tolist()} | "
                        f"encabezado: {leer('mapa').iloc[0].tolist()[:8]}")

        st.subheader("Mapa de calor del día")
        mapa = con_dato.copy()
        mapa["etiqueta"] = mapa["Var"].map(lambda v: fmt_pct(v))
        mapa["peso"] = 1
        fig = px.treemap(
            mapa,
            path=[px.Constant("Todos los CEDEARs"), "Sector", "Ticker"],
            values="peso",
            color="Var",
            color_continuous_scale=[[0, "#d9363e"], [0.5, "#eef1f4"],
                                    [1, "#1f6fd1"]],
            range_color=[-4, 4],
            custom_data=["etiqueta", "USD", "CEDEAR"],
        )
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]}",
            hovertemplate=("<b>%{label}</b><br>Var. del día: %{customdata[0]}"
                           "<br>Precio USD: %{customdata[1]}"
                           "<br>CEDEAR: %{customdata[2]}<extra></extra>"),
            marker=dict(line=dict(width=1, color="#ffffff")),
        )
        fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=640,
                          coloraxis_colorbar=dict(title="Var. %"))
        st.plotly_chart(fig, width="stretch")
        st.markdown('<span class="nota">Azul = sube, rojo = baja. '
                    'Todos los cuadros tienen el mismo tamaño.</span>',
                    unsafe_allow_html=True)

        st.subheader("Ganadores y perdedores del día")
        cols = ["Ticker", "Sector", "Var", "USD", "CEDEAR"]
        nombres = {"Var": "Var. del día", "USD": "Precio USD",
                   "CEDEAR": "Precio CEDEAR"}
        g, p = st.columns(2)
        top = con_dato.sort_values("Var", ascending=False).head(10)[cols]
        low = con_dato.sort_values("Var", ascending=True).head(10)[cols]
        for t in (top, low):
            t["Var"] = t["Var"].map(fmt_pct)
        with g:
            st.markdown("**🟦 Top 10 que más suben**")
            st.dataframe(top.rename(columns=nombres), hide_index=True,
                         width="stretch")
        with p:
            st.markdown("**🟥 Top 10 que más bajan**")
            st.dataframe(low.rename(columns=nombres), hide_index=True,
                         width="stretch")

# ── Macro ─────────────────────────────────────────────────────────────────
with tab_macro:
    try:
        dol = tabla_dolar()
        meta, sen, inf, ban = tabla_web()
    except Exception:
        st.warning("No pude leer los datos macro en este momento.")
        dol, inf, ban, meta, sen = {}, pd.DataFrame(), pd.DataFrame(), {}, \
            pd.DataFrame()

    def val(clave, i=0):
        return dol.get(clave, ["", ""])[i] if clave in dol else "s/d"

    st.subheader("💵 Dólar")
    d1, d2, d3 = st.columns(3)
    d1.metric("Oficial", val("Oficial"))
    brecha_mep = val("MEP", 1)
    brecha_ccl = val("CCL", 1)
    d2.metric("MEP", val("MEP"))
    d3.metric("CCL", val("CCL"))
    if brecha_mep:
        d2.caption(f"Brecha con el oficial: {brecha_mep}")
    if brecha_ccl:
        d3.caption(f"Brecha con el oficial: {brecha_ccl}")

    st.subheader("🇦🇷 Indicadores")
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Riesgo país", val("Riesgo país"))
    i2.metric("Inflación mensual", val("Inflación mensual"))
    i3.metric("Inflación anual", val("Inflación anual"))
    i4.metric("Banda cambiaria", val("Banda cambiaria").split(":")[0])
    st.markdown(f'<span class="nota">{val("Banda cambiaria")} · '
                f'Actualizado: {val("Actualizado")}</span>',
                unsafe_allow_html=True)

    if len(ban):
        st.subheader("Bandas cambiarias del BCRA")
        oficial = num(val("Oficial"))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ban["Fecha"], y=ban["Techo"],
                                 name="Techo", line=dict(color="#d9363e")))
        fig.add_trace(go.Scatter(x=ban["Fecha"], y=ban["Piso"],
                                 name="Piso", line=dict(color="#1f6fd1"),
                                 fill="tonexty",
                                 fillcolor="rgba(31,111,209,0.07)"))
        if oficial:
            hoy = pd.Timestamp.today().normalize()
            fig.add_trace(go.Scatter(
                x=[hoy], y=[oficial], name="Oficial hoy",
                mode="markers+text", text=[fmt_pesos(oficial)],
                textposition="top center",
                marker=dict(size=12, color=NAVY)))
            fila = ban[ban["Fecha"] <= hoy].tail(1)
            if len(fila):
                piso, techo = fila["Piso"].iat[0], fila["Techo"].iat[0]
                pos = (oficial - piso) / (techo - piso) * 100
                st.markdown(
                    (f"Hoy el oficial ({fmt_pesos(oficial)}) está al "
                     f"**{pos:.0f}%** del camino entre el piso "
                     f"({fmt_pesos(piso)}) y el techo ({fmt_pesos(techo)}).")
                    .replace("$", "\\$"))
        fig.update_layout(height=380, margin=dict(t=10, l=0, r=0, b=0),
                          yaxis_title="$ por dólar",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")

    if len(inf):
        st.subheader("Inflación (INDEC)")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=inf["Mes"], y=inf["Mensual"],
                             name="Mensual", marker_color=NAVY,
                             text=inf["Mensual"].map(
                                 lambda v: f"{v:.1f}%".replace(".", ",")),
                             textposition="outside"))
        fig.update_layout(height=340, margin=dict(t=10, l=0, r=0, b=0),
                          yaxis_title="% mensual", showlegend=False)
        st.plotly_chart(fig, width="stretch")
        ult = inf.tail(1)
        anual = f'{ult["Anual"].iat[0]:.1f}%'.replace(".", ",")
        st.markdown(
            f'<span class="nota">Último dato: {ult["Mes"].iat[0]} · '
            f'interanual {anual}</span>', unsafe_allow_html=True)

    with st.expander("¿Cómo se lee el riesgo país?"):
        st.markdown(
            "- **Menos de 150:** máxima confianza (Uruguay, Perú).\n"
            "- **150 a 350:** economía estable (Brasil, México).\n"
            "- **350 a 500:** zona de umbral: piden más tasa, pero el "
            "crédito sigue abierto.\n"
            "- **500 a 1.000:** zona de alerta: financiarse es muy caro.\n\n"
            f"Más detalle en el [blog]({BLOG}/escala-riesgo-pais/).")

# ── Señales del día ───────────────────────────────────────────────────────
with tab_sen:
    try:
        meta, sen, _, _ = tabla_web()
    except Exception:
        meta, sen = {}, pd.DataFrame()
        st.warning("No pude leer las señales en este momento.")

    st.subheader(f"Señales técnicas del {meta.get('fecha', '')}")
    if meta.get("contexto"):
        st.markdown(f'<div class="ctx">🌎 {meta["contexto"]}</div>',
                    unsafe_allow_html=True)

    if len(sen):
        mostrar = sen.copy()
        mostrar["Precio CEDEAR"] = mostrar["Precio CEDEAR"].map(
            lambda v: fmt_pesos(num(v)) if num(v) else v)
        st.dataframe(mostrar, hide_index=True, width="stretch")
    else:
        st.info("Hoy no hubo señales nuevas.")

    st.markdown("#### ¿Qué significa cada señal?")
    st.markdown(
        "- 🚀 **SOBREVENTA:** el RSI bajó de 30. La acción cayó fuerte en "
        "poco tiempo y puede rebotar.\n"
        "- 🔴 **QUIEBRE SOPORTE:** el precio perforó un piso que venía "
        "respetando.\n"
        "- **RSI:** índice de fuerza relativa, de 0 a 100. Abajo de 30 = "
        "sobrevendida; arriba de 70 = sobrecomprada.\n\n"
        "Las señales salen de una planilla con reglas fijas, probadas con "
        "un backtest de 2020 a 2026.")

    st.markdown(
        f'<a href="{TELEGRAM}" target="_blank" style="display:inline-block;'
        f'background:{TG_BLUE};color:#fff;padding:10px 18px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">'
        f'📲 Recibí las señales todos los días a las 18:30</a>',
        unsafe_allow_html=True)

# ── Balances y noticias ───────────────────────────────────────────────────
with tab_bal:
    try:
        textos, bal = tabla_balances()
    except Exception:
        textos, bal = {}, pd.DataFrame()
        st.warning("No pude leer los balances en este momento.")

    col_n, col_b = st.columns(2)
    with col_n:
        st.subheader("📰 Noticias del día")
        if textos.get("noticias"):
            lineas = [l for l in textos["noticias"].split("\n") if l.strip()]
            st.caption(lineas[0])
            st.markdown("\n".join(f"- {md(l)}" for l in lineas[1:]))
        else:
            st.info("Las noticias del día se publican a las 18:30.")
    with col_b:
        st.subheader("📑 Resumen de balances")
        if textos.get("resumen"):
            lineas = [l for l in textos["resumen"].split("\n") if l.strip()]
            st.caption(lineas[0])
            st.markdown("\n".join(f"- {md(l)}" for l in lineas[1:]))
        else:
            st.info("Hoy no hubo balances de empresas seguidas.")

    if len(bal):
        st.subheader("Informes de los últimos días")
        st.caption("Tocá una empresa para ver el detalle del trimestre.")
        for fecha, grupo in bal.groupby("Fecha", sort=False):
            st.markdown(f"**{fecha}**")
            for _, f in grupo.iterrows():
                with st.expander(f"{f['Resultado']} · {f['Empresa']}"):
                    claves = [l.strip().lstrip("'") for l in
                              str(f["Claves"]).split("\n") if l.strip()]
                    salida = []
                    for c in claves:
                        if c[:1] == "+":
                            salida.append("🟢 " + c[1:].strip())
                        elif c[:1] in "−-":
                            salida.append("🔴 " + c[1:].strip())
                        else:
                            salida.append(c)
                    st.markdown("  \n".join(md(c) for c in salida))
                    if str(f["Reaccion"]).strip():
                        st.markdown(f"**Reacción:** {md(f['Reaccion'])}")
                    if str(f["Lectura"]).strip():
                        st.markdown(f"**Lectura:** {md(f['Lectura'])}")

    st.markdown(
        f'<a href="{TELEGRAM}" target="_blank" style="display:inline-block;'
        f'background:{TG_BLUE};color:#fff;padding:10px 18px;margin-top:8px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">'
        f'📲 Recibí balances y noticias todos los días a las 18:30</a>',
        unsafe_allow_html=True)

# ── Pie ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<p class="nota" style="text-align:center">Contenido educativo. '
    'No es recomendación de inversión ni asesoramiento financiero. '
    'Antes de invertir, analizá tu situación y tu perfil de riesgo.</p>',
    unsafe_allow_html=True)
