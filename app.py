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

# Custom CSS dla lepszego wyglądu (kafelki metryk)
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Wsparcie dla trybu ciemnego */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #41424b;
        }
    }
    /* Stylizacja tabeli statycznej */
    table {
        width: 100%;
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
col_title, col_logo = st.columns([3, 1])
with col_title:
    st.title("📦 System Magazynowy")
    st.markdown("Zarządzaj swoim asortymentem w czasie rzeczywistym.")

# Obliczanie statystyk
total_products = len(products)
total_categories = len(categories)
total_value = sum([p.get('cena', 0) * p.get('liczba', 0) for p in products]) if products else 0

# Wyświetlanie metryk w ładnych kafelkach
m1, m2, m3 = st.columns(3)
m1.metric("Liczba Produktów", total_products, border=True)
m2.metric("Wartość Magazynu", f"{total_value:,.2f} zł", border=True)
m3.metric("Kategorie", total_categories, border=True)

st.markdown("---")

# --- GŁÓWNA ZAWARTOŚĆ ---
tab_prod, tab_cat = st.tabs(["🛒 Zarządzanie Produktami", "📂 Konfiguracja Kategorii"])

# === ZAKŁADKA 1: PRODUKTY ===
with tab_prod:
    if not categories:
        st.warning("⚠️ Aby rozpocząć, dodaj pierwszą kategorię w zakładce 'Konfiguracja Kategorii'.")
    else:
        # Layout: Dwie kolumny (Tabela po lewej, Dodawanie po prawej)
        col_left, col_right = st.columns([2, 1], gap="large")

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
                # Dodajemy panel sortowania nad tabelą, bo st.table nie jest interaktywna
                c_sort1, c_sort2 = st.columns([2, 1])
                with c_sort1:
                    sort_col = st.selectbox("Sortuj według:", df_display.columns, index=2) # Domyślnie "Ilość"
                with c_sort2:
                    sort_asc = st.toggle("Rosnąco", value=False) # Domyślnie malejąco (największe na górze)
                
                # Sortowanie danych
                df_display = df_display.sort_values(by=sort_col, ascending=sort_asc)
                
                # --- STYLIZACJA (Pasek stanu) ---
                def style_stock_levels(s):
                    max_val = max(s.max(), 1) if not s.empty and s.max() > 0 else 100
                    styles = []
                    for val in s:
                        ratio = val / max_val
                        percent = ratio * 100
                        
                        # Dobór koloru
                        if ratio < 0.25:
                            bar_color = "#ff4b4b" 
                        elif ratio < 0.60:
                            bar_color = "#ffa421"
                        else:
                            bar_color = "#21c354"
                        
                        # Gradient CSS
                        style = f"""
                            background: linear-gradient(90deg, {bar_color} {percent:.1f}%, transparent {percent:.1f}%);
                            color: black;
                            font-weight: 500;
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
                st.divider()
                st.subheader("Operacje")
                
                op_col1, op_col2 = st.columns(2, gap="medium")
                
                # 1. Zmniejszanie stanu (Wydawanie towaru)
                with op_col1:
                    with st.container(border=True):
                        st.write("📉 **Wydaj towar (Zmniejsz stan)**")
                        with st.form("decrease_qty_form", clear_on_submit=True):
                            # Używamy posortowanej listy produktów w selectboxie, żeby było łatwiej znaleźć
                            # Ale musimy odwołać się do oryginalnego słownika 'products' żeby mieć ID
                            # Tworzymy mapę nazwa -> id z oryginalnych danych
                            prod_map = {p['nazwa']: p for p in products}
                            
                            # Pobieramy listę nazw z wyświetlanej (posortowanej) tabeli
                            sorted_names = df_display["Nazwa"].tolist()
                            
                            # Wybieramy produkt z listy posortowanej
                            selected_prod_name = st.selectbox(
                                "Wybierz produkt", 
                                sorted_names, 
                                key="sel_update_name"
                            )
                            
                            qty_to_remove = st.number_input("Ile sztuk wydać/usunąć?", min_value=1, step=1, value=1)
                            
                            if st.form_submit_button("Zatwierdź zmianę", use_container_width=True):
                                p_data = prod_map[selected_prod_name]
                                current_qty = p_data['liczba']
                                if current_qty >= qty_to_remove:
                                    new_qty = current_qty - qty_to_remove
                                    if update_product_quantity(p_data['id'], new_qty):
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.error(f"Błąd: Na stanie masz tylko {current_qty} szt.!")

                # 2. Usuwanie całkowite
                with op_col2:
                    with st.container(border=True):
                        st.write("🗑️ **Usuń produkt z bazy**")
                        
                        # Podobnie jak wyżej, używamy posortowanej listy nazw
                        selected_del_name = st.selectbox(
                            "Produkt do usunięcia", 
                            df_display["Nazwa"].tolist(),
                            key="sel_delete_name"
                        )
                        
                        st.warning("Tej operacji nie można cofnąć.")
                        if st.button("Usuń trwale", type="primary", use_container_width=True):
                            # Pobieramy ID na podstawie nazwy
                            prod_id_to_del = next((p['id'] for p in products if p['nazwa'] == selected_del_name), None)
                            if prod_id_to_del:
                                if delete_product(prod_id_to_del):
                                    time.sleep(1)
                                    st.rerun()

            else:
                st.info("Magazyn jest pusty.")

        # --- SEKCJA: FORMULARZ DODAWANIA ---
        with col_right:
            st.success("➕ Dodaj nowy towar")  # Używamy success jako nagłówka kontenera
            with st.container(border=True):
                with st.form("add_prod_form", clear_on_submit=True):
                    f_nazwa = st.text_input("Nazwa produktu", placeholder="np. Opony zimowe")
                    
                    cat_map = {c['nazwa']: c['id'] for c in categories}
                    f_kat = st.selectbox("Kategoria", list(cat_map.keys()))
                    
                    c1, c2 = st.columns(2)
                    f_cena = c1.number_input("Cena (zł)", min_value=0.01, step=0.01)
                    f_liczba = c2.number_input("Ilość (szt.)", min_value=1, step=1, value=1)
                    
                    submitted = st.form_submit_button("Zatwierdź", use_container_width=True)
                    
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
    
    col_c1, col_c2 = st.columns(2, gap="large")
    
    with col_c1:
        st.info("Lista dostępnych kategorii")
        if categories:
            for cat in categories:
                # Wyświetlanie każdej kategorii w ładnym rzędzie
                with st.container(border=True):
                    c_row1, c_row2 = st.columns([4, 1])
                    c_row1.markdown(f"**{cat['nazwa']}**")
                    if c_row2.button("🗑️", key=f"del_c_{cat['id']}", help="Usuń kategorię"):
                        if delete_category(cat['id']):
                            time.sleep(1)
                            st.rerun()
        else:
            st.write("Brak kategorii.")

    with col_c2:
        with st.form("add_cat_form", clear_on_submit=True):
            st.write("Nowa kategoria")
            new_cat_name = st.text_input("Nazwa", placeholder="np. Elektronika", label_visibility="collapsed")
            if st.form_submit_button("Dodaj kategorię", use_container_width=True):
                if new_cat_name:
                    if add_category(new_cat_name):
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Nazwa nie może być pusta.")
