import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from supabase import create_client, Client

# Configurazione pagina
st.set_page_config(page_title="Pocket Manager Pro", page_icon="🎓", layout="centered")

# Dati di default potenziati
DEFAULT_DATA = {
    "pockets": {
        "Conto Principale": 200.0,
        "Cassa Borsa di Studio": 1500.0,
        "Telefono": 600.0,
        "Emergenze": 500.0
    },
    "budget_target": {
        "Benzina": 95.0,
        "Casa": 50.0,
        "Svago": 30.0,
        "E-cig": 25.0
    },
    "spese": [],
    "rate_telefono": []
}

# Connessione al DB Cloud (salvata in cache per efficienza)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def carica_dati():
    response = supabase.table("app_data").select("dati").eq("id", 1).execute()
    
    # Se il database è completamente vuoto (nessun dato restituito)
    if len(response.data) == 0:
        return DEFAULT_DATA
        
    dati_db = response.data[0]['dati']
    
    # Se la riga esiste ma il JSON è vuoto '{}'
    if not dati_db:
        return DEFAULT_DATA
        
    return dati_db

def salva_dati(dati_aggiornati):
    # 'upsert' è magico: se l'ID 1 non esiste lo crea, se esiste lo aggiorna!
    supabase.table("app_data").upsert({"id": 1, "dati": dati_aggiornati}).execute()

dati = carica_dati()

# ... QUI INIZIA IL RESTO DEL CODICE (st.title("🎓 Pocket Manager Pro") ecc.) ...
st.title("🎓 Pocket Manager Pro")
st.caption("Gestione avanzata per Borsa di Studio, Budget e Simulazioni d'acquisto")

# Nuova struttura a 5 schede
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "💸 Spese", "📈 Grafici", "🔮 Simulatore", "⚙️ Impostazioni"
])

# ----------------- TAB 1: DASHBOARD -----------------
with tab1:
    st.subheader("I tuoi Pocket Revolut")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💳 Conto Principale", f"{dati['pockets']['Conto Principale']:.2f} €")
        st.metric("🚨 Emergenze", f"{dati['pockets']['Emergenze']:.2f} €")
    with col2:
        st.metric("🎓 Cassa Borsa di Studio", f"{dati['pockets']['Cassa Borsa di Studio']:.2f} €")
        st.metric("📱 Fondo Telefono", f"{dati['pockets']['Telefono']:.2f} €")

    st.divider()
    st.subheader("Avanzamento Categorie")
    
    df_spese = pd.DataFrame(dati["spese"])
    for cat, target in dati["budget_target"].items():
        speso_cat = df_spese[df_spese["categoria"] == cat]["importo"].sum() if not df_spese.empty and cat in df_spese["categoria"].values else 0.0
        pct = min(speso_cat / target, 1.0) if target > 0 else 0.0
        st.write(f"**{cat}:** {speso_cat:.2f} € su {target:.2f} €")
        st.progress(pct)

# ----------------- TAB 2: AGGIUNGI SPESA -----------------
with tab2:
    st.subheader("Registra un'uscita")
    with st.form("form_spesa", clear_on_submit=True):
        data_spesa = st.date_input("Data", datetime.now())
        categoria = st.selectbox("Categoria", list(dati["budget_target"].keys()) + ["Altro"])
        importo = st.number_input("Importo (€)", min_value=0.01, step=0.50, format="%.2f")
        pocket_sorgente = st.selectbox("Preleva da", list(dati["pockets"].keys()))
        note = st.text_input("Note", placeholder="es. Pieno benzina")
        
        if st.form_submit_button("Salva Spesa"):
            dati["spese"].append({
                "data": str(data_spesa), "categoria": categoria,
                "importo": importo, "pocket": pocket_sorgente, "note": note
            })
            dati["pockets"][pocket_sorgente] -= importo
            salva_dati(dati)
            st.success("Spesa registrata! Saldo aggiornato.")
            st.rerun()

    if dati["spese"]:
        st.divider()
        st.subheader("Storico Spese")
        st.dataframe(pd.DataFrame(dati["spese"]).sort_values(by="data", ascending=False), use_container_width=True)

# ----------------- TAB 3: GRAFICI -----------------
with tab3:
    st.subheader("Analisi Visiva")
    if dati["spese"] and not df_spese.empty:
        # Grafico a Ciambella
        fig_pie = px.pie(df_spese, values='importo', names='categoria', 
                         title='Distribuzione Spese per Categoria', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Grafico a Barre (Budget vs Spesa)
        budget_data = []
        for cat, target in dati["budget_target"].items():
            speso = df_spese[df_spese["categoria"] == cat]["importo"].sum() if cat in df_spese["categoria"].values else 0.0
            budget_data.append({"Categoria": cat, "Tipo": "Speso reale", "Importo": speso})
            budget_data.append({"Categoria": cat, "Tipo": "Budget target", "Importo": target})
            
        df_budget = pd.DataFrame(budget_data)
        fig_bar = px.bar(df_budget, x='Categoria', y='Importo', color='Tipo', 
                         barmode='group', title='Confronto Spesa vs Target')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Nessuna spesa registrata per generare i grafici.")

# ----------------- TAB 4: SIMULATORE -----------------
with tab4:
    st.subheader("Simulatore di Acquisto")
    st.write("Vuoi comprare un tablet o una spesa imprevista? Scopri l'impatto sul tuo budget.")
    
    oggetto = st.text_input("Cosa vuoi acquistare?", "Tablet")
    prezzo = st.number_input("Costo totale dell'oggetto (€)", min_value=1.0, value=300.0, step=10.0)
    pocket_sim = st.selectbox("Su quale Pocket peserà?", list(dati["pockets"].keys()))
    
    st.markdown("---")
    saldo_disp = dati["pockets"][pocket_sim]
    st.write(f"Saldo attuale in **{pocket_sim}**: `{saldo_disp:.2f} €`")
    
    for rate in [1, 3, 5, 12]:
        rata_mensile = prezzo / rate
        impatto = (rata_mensile / saldo_disp) * 100 if saldo_disp > 0 else 999
        
        titolo = {1: "💰 Unica soluzione", 3: "💳 3 Rate (Klarna/PayPal)", 
                  5: "📦 5 Rate (Amazon)", 12: "🏦 12 Rate (Finanziamento)"}[rate]
            
        if rate == 1 and prezzo > saldo_disp:
            st.error(f"**{titolo}** da {rata_mensile:.2f}€ - ❌ Fondi insufficienti.")
        else:
            if impatto <= 15:
                st.success(f"**{titolo}** da {rata_mensile:.2f}€/mese - ✅ Consigliato (impatto: {impatto:.1f}%)")
            elif impatto <= 33:
                st.warning(f"**{titolo}** da {rata_mensile:.2f}€/mese - ⚠️ Fattibile (impatto medio: {impatto:.1f}%)")
            else:
                st.error(f"**{titolo}** da {rata_mensile:.2f}€/mese - ❌ Sconsigliato (impatto alto: {impatto:.1f}%)")

# ----------------- TAB 5: IMPOSTAZIONI -----------------
with tab5:
    st.subheader("Aggiorna Budget Pocket")
    with st.form("form_pockets"):
        nuovi_saldi = {}
        for p_name, p_val in dati["pockets"].items():
            nuovi_saldi[p_name] = st.number_input(f"Saldo {p_name} (€)", value=float(p_val), step=10.0)
        
        if st.form_submit_button("Salva Nuovi Saldi"):
            dati["pockets"] = nuovi_saldi
            salva_dati(dati)
            st.success("Saldi aggiornati con successo!")
            st.rerun()
            
    st.divider()
    st.subheader("Aggiungi Nuova Categoria")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        nuova_cat = st.text_input("Nome Categoria (es. Abbonamenti)")
    with col_c2:
        nuovo_target = st.number_input("Target Mensile (€)", min_value=0.0, step=5.0)
        
    if st.button("Aggiungi Categoria"):
        if nuova_cat and nuova_cat not in dati["budget_target"]:
            dati["budget_target"][nuova_cat] = nuovo_target
            salva_dati(dati)
            st.success(f"Categoria '{nuova_cat}' aggiunta!")
            st.rerun()
        elif nuova_cat in dati["budget_target"]:
            st.warning("Questa categoria esiste già.")