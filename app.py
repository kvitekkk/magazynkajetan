import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# -----------------------------------------------------------------------------
# 0. KONFIGURACJA STRONY (Musi być na samym początku)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Magazyn Manager",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# NOWOCZESNY DESIGN (CSS)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Import nowoczesnej czcionki */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Tło aplikacji */
    .stApp {
        background-color: #fcfdfd;
    }

    /* Stylizacja nagłówka (Gradient Text) */
    h1 {
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #111827, #4b5563);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }

    /* Karty metryk (na górze) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #6b7280;
    }
    div[data-testid="stMetricValue"] {
        font-weight: 700;
        color: #111827;
    }

    /* Kontenery z obramowaniem (Formularze, Sekcje) */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #ffffff;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        padding: 20px;
    }

    /* Nowoczesna tabela */
    table {
        width: 100%;
        border-collapse: separate; 
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }
    
    thead tr th {
        background-color: #f9fafb !important;
        color: #374151 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em;
        padding: 16px !important;
        border-bottom: 1px solid #e5e7eb !important;
    }
    
    tbody tr td {
        padding: 14px 16px !important;
        border-bottom: 1px solid #f3f4f6 !important;
        color: #1f2937;
        vertical-align: middle;
    }
    
    tbody tr:last-child td {
        border-bottom: none !important;
    }
    
    tbody tr:hover {
        background-color: #f9fafb;
    }

    /* Przyciski */
    button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        transition: all 0.2s;
    }
    button[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 10px -1px rgba(37, 99, 235, 0.3);
    }
    button[kind="secondary"] {
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px;
        border-color: #e5e7eb;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
    }

    /* Dark Mode Support overrides */
    @media (prefers-color-scheme: dark) {
        .stApp { background-color: #111827; }
        h1 { background: -webkit-linear-gradient(45deg, #f3f4f6, #9ca3af); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        div[data-testid="stMetric"], div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: #1f2937;
            border-color: #374151;
        }
        div[data-testid="stMetricLabel"] { color: #9ca3af; }
        div[data-testid="stMetricValue"] { color: #f9fafb; }
        thead tr th { background-color: #374151 !important; color: #e5e7eb !important; border-bottom: 1px solid #4b5563 !important; }
        tbody tr td { border-bottom: 1px solid #374151 !important; color: #d1d5db; }
        tbody tr:hover { background-color: #374151; }
        table { border-color: #374151; }
        button[kind="secondary"] { border-color: #4b5563; color: #e5e7eb; }
        button[kind="secondary"]:hover { border-color: #6b7280; color: #ffffff; }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. POŁĄCZENIE Z SUPABASE
# -----------------------------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except (FileNotFoundError, KeyError):
    st.error("❌ Brak konfiguracji! Upewnij się, że dodałeś SUPABASE_URL i SUPABASE_KEY w .streamlit/secrets.toml.")
    st.stop()

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Błąd połączenia z bazą: {e}")
        st.stop()

supabase: Client = init_connection()

# -----------------------------------------------------------------------------
# 2. FUNKCJE CRUD (Zmodernizowane powiadomienia)
# -----------------------------------------------------------------------------

def handle_error(e):
    err_msg = str(e)
    if "42501" in err_msg:
        st.error("⛔ Brak uprawnień (RLS). Wyłącz RLS w Supabase.")
    elif "404" in err_msg:
        st.error("⛔ Nie znaleziono tabeli lub rekordu.")
    elif "42703" in err_msg:
        st.error(f"⛔ Błąd kolumny (sprawdź nazwy w bazie): {e}")
    else:
        st.error(f"Wystąpił błąd: {e}")

def get_data(table, order_by="id", ascending=False):
    try:
        query = supabase.table(table).select("*").order(order_by, desc=not ascending)
        response = query.execute()
        return response.data
    except Exception as e:
        handle_error(e)
        return []

def get_products_with_categories():
    try:
        response = supabase.table("produkty").select("*, kategorie(nazwa)").order("id", desc=True).execute()
        data = []
        for item in response.data:
            flat = item.copy()
            flat['kategoria_nazwa'] = item['kategorie']['nazwa'] if item.get('kategorie') else "---"
            data.append(flat)
        return data
    except Exception as e:
        handle_error(e)
        return []

def add_category(name):
    try:
        supabase.table("kategorie").insert({"nazwa": name}).execute()
        st.toast(f"✅ Dodano kategorię: {name}", icon="🎉")
        return True
    except Exception as e:
        handle_error(e)
        return False

def delete_category(cat_id):
    try:
        supabase.table("kategorie").delete().eq("id", cat_id).execute()
        st.toast("✅ Kategoria usunięta", icon="🗑️")
        return True
    except Exception as e:
        handle_error(e)
        return False

def add_product(data):
    try:
        supabase.table("produkty").insert(data).execute()
        st.toast(f"✅ Dodano produkt: {data['nazwa']}", icon="📦")
        return True
    except Exception as e:
        handle_error(e)
        return False

def update_product_quantity(product_id, new_quantity):
    """Aktualizuje liczbę sztuk produktu"""
    try:
        supabase.table("produkty").update({"liczba": new_quantity}).eq("id", product_id).execute()
        st.toast(f"✅ Zaktualizowano stan magazynowy", icon="📉")
        return True
    except Exception as e:
        handle_error(e)
        return False

def delete_product(prod_id):
    try:
        supabase.table("produkty").delete().eq("id", prod_id).execute()
        st.toast("✅ Produkt usunięty trwale", icon="🗑️")
        return True
    except Exception as e:
        handle_error(e)
        return False

# -----------------------------------------------------------------------------
# 3. INTERFEJS UŻYTKOWNIKA (UI)
# -----------------------------------------------------------------------------

# Pobranie danych na starcie
categories = get_data("kategorie", order_by="nazwa", ascending=True)
products = get_products_with_categories()

# --- NAGŁÓWEK I METRYKI ---
# Używam columns, aby lepiej wypozycjonować tytuł
col_h1, col_h2 = st.columns([0.7, 0.3])
with col_h1:
    st.title("📦 System Magazynowy")
    st.caption("Panel zarządzania stanami i asortymentem")

# Obliczanie statystyk
total_products = len(products)
total_categories = len(categories)
total_value = sum([p.get('cena', 0) * p.get('liczba', 0) for p in products]) if products else 0

# Wyświetlanie metryk w ładnych kafelkach
m1, m2, m3 = st.columns(3)
m1.metric("Liczba Produktów", total_products)
m2.metric("Wartość Magazynu", f"{total_value:,.2f} zł")
m3.metric("Kategorie", total_categories)

st.markdown("<div style='margin-bottom: 30px'></div>", unsafe_allow_html=True) # Odstęp

# --- GŁÓWNA ZAWARTOŚĆ ---
tab_prod, tab_cat = st.tabs(["🛒 Zarządzanie Produktami", "📂 Konfiguracja Kategorii"])

# === ZAKŁADKA 1: PRODUKTY ===
with tab_prod:
    if not categories:
        st.warning("⚠️ Aby rozpocząć, dodaj pierwszą kategorię w zakładce 'Konfiguracja Kategorii'.")
    else:
        # Layout: Dwie kolumny (Tabela po lewej, Dodawanie po prawej)
        col_left, col_right = st.columns([0.65, 0.35], gap="large")

        # --- SEKCJA: LISTA PRODUKTÓW ---
        with col_left:
            st.subheader("Stan magazynowy")
            if products:
                # Przygotowanie DataFrame
                df = pd.DataFrame(products)
                
                # Dodanie kolumny z łączną wartością (Cena * Ilość)
                df["wartosc_calkowita"] = df["cena"] * df["liczba"]
                
                # Wybór i zmiana nazw kolumn do wyświetlenia
                df_display = df[["nazwa", "cena", "liczba", "wartosc_calkowita", "kategoria_nazwa"]].copy()
                df_display.columns = ["Nazwa", "Cena", "Ilość", "Wartość", "Kategoria"]
                
                # --- SORTOWANIE ---
                with st.container():
                    c_sort1, c_sort2 = st.columns([3, 1])
                    with c_sort1:
                        sort_col = st.selectbox("Sortuj według:", df_display.columns, index=2, label_visibility="collapsed") 
                    with c_sort2:
                        sort_asc = st.toggle("Rosnąco", value=False)
                
                st.markdown("<div style='margin-bottom: 10px'></div>", unsafe_allow_html=True)

                # Sortowanie danych
                df_display = df_display.sort_values(by=sort_col, ascending=sort_asc)
                
                # --- STYLIZACJA (Pasek stanu) ---
                def style_stock_levels(s):
                    max_val = max(s.max(), 1) if not s.empty and s.max() > 0 else 100
                    styles = []
                    for val in s:
                        ratio = val / max_val
                        percent = ratio * 100
                        
                        # Dobór koloru: Nowoczesna paleta
                        if ratio < 0.25:
                            bar_color = "rgba(239, 68, 68, 0.4)" # Czerwony (transparentny)
                        elif ratio < 0.60:
                            bar_color = "rgba(245, 158, 11, 0.4)" # Pomarańczowy
                        else:
                            bar_color = "rgba(16, 185, 129, 0.4)" # Szmaragdowy
                        
                        # Gradient CSS - delikatniejszy
                        style = f"""
                            background: linear-gradient(90deg, {bar_color} {percent:.1f}%, transparent {percent:.1f}%);
                            color: inherit;
                            font-weight: 500;
                            border-radius: 4px;
                        """
                        styles.append(style)
                    return styles

                # Formatowanie wartości i aplikowanie stylu
                styler = df_display.style.format({
                    "Cena": "{:.2f} zł",
                    "Wartość": "{:.2f} zł",
                    "Ilość": "{:d} szt."
                }).apply(style_stock_levels, subset=["Ilość"])
                
                # Wyświetlenie tabeli
                st.table(styler)
                
                # --- OPERACJE NA PRODUKTACH ---
                st.markdown("### ⚡ Szybkie akcje")
                
                op_col1, op_col2 = st.columns(2, gap="medium")
                
                # 1. Zmniejszanie stanu (Wydawanie towaru)
                with op_col1:
                    with st.container(border=True):
                        st.markdown("**📉 Wydanie towaru**")
                        with st.form("decrease_qty_form", clear_on_submit=True):
                            prod_map = {p['nazwa']: p for p in products}
                            sorted_names = df_display["Nazwa"].tolist()
                            
                            selected_prod_name = st.selectbox(
                                "Wybierz produkt", 
                                sorted_names, 
                                key="sel_update_name",
                                label_visibility="collapsed",
                                placeholder="Wybierz produkt..."
                            )
                            
                            st.caption("Liczba sztuk do zdjęcia ze stanu:")
                            qty_to_remove = st.number_input("Ilość", min_value=1, step=1, value=1, label_visibility="collapsed")
                            
                            if st.form_submit_button("Zatwierdź wydanie", use_container_width=True):
                                if selected_prod_name:
                                    p_data = prod_map[selected_prod_name]
                                    current_qty = p_data['liczba']
                                    if current_qty >= qty_to_remove:
                                        new_qty = current_qty - qty_to_remove
                                        if update_product_quantity(p_data['id'], new_qty):
                                            time.sleep(1)
                                            st.rerun()
                                    else:
                                        st.error(f"Błąd: Tylko {current_qty} szt. na stanie!")
                                else:
                                    st.warning("Wybierz produkt.")

                # 2. Usuwanie całkowite
                with op_col2:
                    with st.container(border=True):
                        st.markdown("**🗑️ Usuwanie z bazy**")
                        
                        selected_del_name = st.selectbox(
                            "Produkt do usunięcia", 
                            df_display["Nazwa"].tolist(),
                            key="sel_delete_name",
                            label_visibility="collapsed"
                        )
                        
                        st.markdown("<div style='margin-bottom: 37px'></div>", unsafe_allow_html=True) # Wyrównanie wysokości
                        
                        if st.button("Usuń trwale produkt", type="secondary", use_container_width=True):
                            prod_id_to_del = next((p['id'] for p in products if p['nazwa'] == selected_del_name), None)
                            if prod_id_to_del:
                                if delete_product(prod_id_to_del):
                                    time.sleep(1)
                                    st.rerun()

            else:
                st.info("Magazyn jest pusty.")

        # --- SEKCJA: FORMULARZ DODAWANIA ---
        with col_right:
            with st.container(border=True):
                st.subheader("➕ Nowy towar")
                with st.form("add_prod_form", clear_on_submit=True):
                    f_nazwa = st.text_input("Nazwa", placeholder="np. Opony zimowe")
                    
                    cat_map = {c['nazwa']: c['id'] for c in categories}
                    f_kat = st.selectbox("Kategoria", list(cat_map.keys()))
                    
                    c1, c2 = st.columns(2)
                    f_cena = c1.number_input("Cena (zł)", min_value=0.01, step=0.01)
                    f_liczba = c2.number_input("Ilość (szt.)", min_value=1, step=1, value=1)
                    
                    st.markdown("---")
                    submitted = st.form_submit_button("Dodaj do magazynu", type="primary", use_container_width=True)
                    
                    if submitted:
                        if not f_nazwa:
                            st.error("Podaj nazwę produktu!")
                        else:
                            new_prod_data = {
                                "nazwa": f_nazwa,
                                "cena": f_cena,
                                "liczba": f_liczba,
                                "kategoria_id": cat_map[f_kat]
                            }
                            if add_product(new_prod_data):
                                time.sleep(1)
                                st.rerun()

# === ZAKŁADKA 2: KATEGORIE ===
with tab_cat:
    st.markdown("### 🏷️ Zarządzaj kategoriami")
    
    col_c1, col_c2 = st.columns([0.6, 0.4], gap="large")
    
    with col_c1:
        st.info("Lista dostępnych kategorii")
        if categories:
            for cat in categories:
                # Wyświetlanie każdej kategorii w ładnym rzędzie
                with st.container(border=True):
                    c_row1, c_row2 = st.columns([0.85, 0.15])
                    c_row1.markdown(f"**{cat['nazwa']}**")
                    if c_row2.button("🗑️", key=f"del_c_{cat['id']}", help="Usuń kategorię"):
                        if delete_category(cat['id']):
                            time.sleep(1)
                            st.rerun()
        else:
            st.write("Brak kategorii.")

    with col_c2:
        with st.container(border=True):
            st.write("**Dodaj nową kategorię**")
            with st.form("add_cat_form", clear_on_submit=True):
                new_cat_name = st.text_input("Nazwa", placeholder="np. Elektronika", label_visibility="collapsed")
                submitted_cat = st.form_submit_button("Zapisz", type="primary", use_container_width=True)
                if submitted_cat:
                    if new_cat_name:
                        if add_category(new_cat_name):
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Nazwa nie może być pusta.")
