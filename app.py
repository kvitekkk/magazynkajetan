import streamlit as st
from supabase import create_client, Client
import pandas as pd
import time

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA
# -----------------------------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except (FileNotFoundError, KeyError):
    st.error("❌ Brak konfiguracji! Upewnij się, że dodałeś SUPABASE_URL i SUPABASE_KEY w .streamlit/secrets.toml lub w panelu Streamlit Cloud.")
    st.stop()

@st.cache_resource
def init_connection():
    """Tworzy połączenie z Supabase"""
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Nie udało się połączyć z Supabase. Sprawdź poprawność URL i klucza API.\nBłąd: {e}")
        st.stop()

supabase: Client = init_connection()

# -----------------------------------------------------------------------------
# 2. FUNKCJE (CRUD)
# -----------------------------------------------------------------------------

def handle_api_error(e):
    """Pomocnicza funkcja do tłumaczenia błędów z bazy"""
    err_msg = str(e)
    if "42501" in err_msg or "permission denied" in err_msg:
        return "⛔ BŁĄD UPRAWNIEŃ (RLS): Twoje tabele istnieją, ale Supabase blokuje do nich dostęp. \n\nRozwiązanie: Wejdź w Supabase -> Table Editor -> Edit Table -> Odznacz 'Enable Row Level Security (RLS)' lub dodaj odpowiednie Policies."
    elif "404" in err_msg or "relation" in err_msg and "does not exist" in err_msg:
        return "⛔ BŁĄD TABELI: Tabela nie istnieje lub ma inną nazwę niż w kodzie (szukam: 'produkty' i 'kategorie')."
    elif "42703" in err_msg:
        return f"⛔ BŁĄD KOLUMNY: Próbujesz użyć kolumny, która nie istnieje w bazie (np. 'liczba' - sprawdź czy dodałeś ją w Supabase!). Szczegóły: {e}"
    else:
        return f"Wystąpił nieoczekiwany błąd bazy danych: {e}"

def get_categories():
    try:
        response = supabase.table("kategorie").select("*").order("nazwa").execute()
        return response.data
    except Exception as e:
        st.error(handle_api_error(e))
        return []

def add_category(name):
    """Zwraca True jeśli sukces, False jeśli błąd"""
    try:
        supabase.table("kategorie").insert({"nazwa": name}).execute()
        st.success(f"✅ Dodano kategorię: {name}")
        return True
    except Exception as e:
        st.error(handle_api_error(e))
        return False

def delete_category(category_id):
    try:
        supabase.table("kategorie").delete().eq("id", category_id).execute()
        st.success("✅ Usunięto kategorię.")
        return True
    except Exception as e:
        st.error(handle_api_error(e))
        return False

def get_products():
    try:
        response = supabase.table("produkty").select("*, kategorie(nazwa)").order("id", desc=True).execute()
        
        data = []
        for item in response.data:
            flat_item = item.copy()
            if item.get('kategorie'):
                flat_item['kategoria_nazwa'] = item['kategorie']['nazwa']
            else:
                flat_item['kategoria_nazwa'] = "---"
            data.append(flat_item)
        return data
    except Exception as e:
        st.error(handle_api_error(e))
        return []

def add_product(nazwa, cena, liczba, kategoria_id):
    """Zwraca True jeśli sukces, False jeśli błąd"""
    try:
        data = {
            "nazwa": nazwa,
            "cena": cena,
            "liczba": liczba,
            "kategoria_id": kategoria_id
        }
        supabase.table("produkty").insert(data).execute()
        st.success(f"✅ Dodano produkt: {nazwa}")
        return True
    except Exception as e:
        st.error(handle_api_error(e))
        return False

def delete_product(product_id):
    try:
        supabase.table("produkty").delete().eq("id", product_id).execute()
        st.success("✅ Usunięto produkt.")
        return True
    except Exception as e:
        st.error(handle_api_error(e))
        return False

# -----------------------------------------------------------------------------
# 3. INTERFEJS (FRONTEND)
# -----------------------------------------------------------------------------

st.title("📦 Magazyn - Panel Sterowania")

categories = get_categories()

tab_products, tab_categories = st.tabs(["🛒 Lista Produktów", "📂 Edycja Kategorii"])

# --- ZAKŁADKA 2: KATEGORIE ---
with tab_categories:
    st.subheader("Dodaj nową kategorię")
    with st.form("cat_form", clear_on_submit=True):
        new_cat = st.text_input("Nazwa")
        if st.form_submit_button("Zapisz kategorię"):
            if new_cat:
                if add_category(new_cat):
                    time.sleep(1) # Czekamy chwilę, żeby użytkownik zobaczył sukces
                    st.rerun()
            else:
                st.warning("Wpisz nazwę.")

    st.divider()
    st.subheader("Istniejące kategorie")
    if categories:
        for cat in categories:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{cat.get('nazwa', 'Bez nazwy')}** (ID: {cat.get('id')})")
            if c2.button("Usuń", key=f"del_c_{cat['id']}"):
                if delete_category(cat['id']):
                    time.sleep(0.5)
                    st.rerun()
    else:
        st.info("Brak kategorii lub problem z połączeniem.")

# --- ZAKŁADKA 1: PRODUKTY ---
with tab_products:
    if not categories:
        st.warning("⚠️ Aby dodawać produkty, musisz mieć zdefiniowane kategorie. Sprawdź zakładkę 'Edycja Kategorii'.")
    else:
        with st.expander("➕ Dodaj nowy produkt", expanded=False):
            with st.form("prod_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    p_name = st.text_input("Nazwa produktu")
                with col2:
                    cat_map = {c['nazwa']: c['id'] for c in categories}
                    p_cat_name = st.selectbox("Kategoria", list(cat_map.keys()))
                
                col3, col4 = st.columns(2)
                with col3:
                    p_price = st.number_input("Cena (PLN)", min_value=0.0, step=0.01)
                with col4:
                    p_quantity = st.number_input("Ilość (szt.)", min_value=0, step=1, value=1)
                
                if st.form_submit_button("Dodaj produkt"):
                    if p_name:
                        # Przekazujemy sterowanie do funkcji i sprawdzamy wynik
                        success = add_product(p_name, p_price, p_quantity, cat_map[p_cat_name])
                        if success:
                            time.sleep(1) # Opóźnienie dla lepszego UX
                            st.rerun()
                    else:
                        st.error("Nazwa produktu jest wymagana.")

    st.divider()
    
    products = get_products()
    if products:
        df = pd.DataFrame(products)
        
        wanted_cols = ['id', 'nazwa', 'cena', 'liczba', 'kategoria_nazwa']
        available_cols = [c for c in wanted_cols if c in df.columns]
        
        st.dataframe(
            df[available_cols], 
            use_container_width=True,
            column_config={
                "cena": st.column_config.NumberColumn("Cena", format="%.2f zł"),
                "liczba": st.column_config.NumberColumn("Ilość", format="%d szt."),
                "nazwa": "Nazwa",
                "kategoria_nazwa": "Kategoria"
            }
        )

        st.caption("Aby usunąć produkt, wybierz go poniżej:")
        p_to_del = st.selectbox("Wybierz do usunięcia", products, format_func=lambda x: f"{x['nazwa']} ({x['cena']} zł)")
        if st.button("🗑️ Usuń wybrany produkt"):
            if delete_product(p_to_del['id']):
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("Brak produktów w bazie.")
