import streamlit as st
from supabase import create_client, Client
import pandas as pd

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA I POŁĄCZENIE Z SUPABASE
# -----------------------------------------------------------------------------
# Pobieramy dane logowania z sekretów Streamlit (lokalnie .streamlit/secrets.toml, w chmurze Settings -> Secrets)
try:
    SUPABASE_URL = st.secrets[https://eelyrtkxgoocqdsuiers.supabase.co]
    SUPABASE_KEY = st.secrets[sb_publishable_sadHenKcMQIJBf0LUb2HRQ_toFYN9Rt]
except FileNotFoundError:
    st.error("Nie znaleziono sekretów! Upewnij się, że skonfigurowałeś .streamlit/secrets.toml lub sekrety w Streamlit Cloud.")
    st.stop()

@st.cache_resource
def init_connection():
    """Inicjalizacja klienta Supabase"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_connection()

# -----------------------------------------------------------------------------
# 2. FUNKCJE POMOCNICZE (CRUD)
# -----------------------------------------------------------------------------

def get_categories():
    """Pobiera wszystkie kategorie"""
    response = supabase.table("categories").select("*").order("name").execute()
    return response.data

def add_category(name):
    """Dodaje nową kategorię"""
    try:
        supabase.table("categories").insert({"name": name}).execute()
        st.success(f"Dodano kategorię: {name}")
    except Exception as e:
        st.error(f"Błąd podczas dodawania kategorii: {e}")

def delete_category(category_id):
    """Usuwa kategorię"""
    try:
        supabase.table("categories").delete().eq("id", category_id).execute()
        st.success("Usunięto kategorię.")
    except Exception as e:
        st.error(f"Błąd usuwania (upewnij się, że kategoria jest pusta): {e}")

def get_products():
    """Pobiera produkty wraz z nazwami kategorii (join)"""
    # Zakładamy relację: products.category_id -> categories.id
    response = supabase.table("products").select("*, categories(name)").order("created_at", desc=True).execute()
    
    # Przekształcenie danych do płaskiej struktury dla DataFrame
    data = []
    for item in response.data:
        flat_item = item.copy()
        if item.get('categories'):
            flat_item['category_name'] = item['categories']['name']
        else:
            flat_item['category_name'] = "Brak"
        data.append(flat_item)
    return data

def add_product(name, price, description, category_id):
    """Dodaje nowy produkt"""
    try:
        data = {
            "name": name,
            "price": price,
            "description": description,
            "category_id": category_id
        }
        supabase.table("products").insert(data).execute()
        st.success(f"Dodano produkt: {name}")
    except Exception as e:
        st.error(f"Błąd podczas dodawania produktu: {e}")

def delete_product(product_id):
    """Usuwa produkt"""
    try:
        supabase.table("products").delete().eq("id", product_id).execute()
        st.success("Usunięto produkt.")
    except Exception as e:
        st.error(f"Błąd: {e}")

# -----------------------------------------------------------------------------
# 3. INTERFEJS UŻYTKOWNIKA (STREAMLIT)
# -----------------------------------------------------------------------------

st.title("📦 Panel Zarządzania Magazynem")
st.markdown("Prosta aplikacja CRUD zintegrowana z Supabase.")

# Zakładki dla lepszej organizacji
tab1, tab2 = st.tabs(["🛒 Produkty", "📂 Kategorie"])

# --- ZAKŁADKA: KATEGORIE ---
with tab2:
    st.header("Zarządzanie Kategoriami")
    
    # Formularz dodawania
    with st.form("new_category"):
        new_cat_name = st.text_input("Nazwa nowej kategorii")
        submitted_cat = st.form_submit_button("Dodaj kategorię")
        if submitted_cat and new_cat_name:
            add_category(new_cat_name)
            st.rerun() # Odśwież stronę, by zobaczyć zmiany

    st.divider()
    
    # Wyświetlanie listy
    categories = get_categories()
    if categories:
        df_cat = pd.DataFrame(categories)
        # Wyświetlamy tabelę, ale dodajemy też przyciski usuwania
        for cat in categories:
            col1, col2 = st.columns([4, 1])
            col1.text(f"ID: {cat['id']} | {cat['name']}")
            if col2.button("Usuń", key=f"del_cat_{cat['id']}"):
                delete_category(cat['id'])
                st.rerun()
    else:
        st.info("Brak kategorii w bazie.")

# --- ZAKŁADKA: PRODUKTY ---
with tab1:
    st.header("Zarządzanie Produktami")

    # Pobieramy kategorie do listy rozwijanej
    categories_list = get_categories()
    if not categories_list:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce 'Kategorie'!")
    else:
        # Formularz dodawania produktu
        with st.form("new_product"):
            col_a, col_b = st.columns(2)
            with col_a:
                prod_name = st.text_input("Nazwa produktu")
                prod_price = st.number_input("Cena (PLN)", min_value=0.01, step=0.01)
            with col_b:
                # Tworzymy mapę nazwa -> id
                cat_options = {c['name']: c['id'] for c in categories_list}
                selected_cat_name = st.selectbox("Kategoria", list(cat_options.keys()))
                
            prod_desc = st.text_area("Opis produktu")
            
            submitted_prod = st.form_submit_button("Dodaj produkt")
            
            if submitted_prod and prod_name:
                cat_id = cat_options[selected_cat_name]
                add_product(prod_name, prod_price, prod_desc, cat_id)
                st.rerun()

    st.divider()

    # Wyświetlanie produktów
    products = get_products()
    if products:
        # Prezentacja w ładnej tabeli interaktywnej
        df_prods = pd.DataFrame(products)
        # Wybieramy tylko interesujące kolumny do wyświetlenia
        display_df = df_prods[['id', 'name', 'price', 'category_name', 'description']]
        st.dataframe(display_df, use_container_width=True)

        st.subheader("Usuwanie produktu")
        # Prosty selectbox do wyboru ID do usunięcia (bezpieczniejsze niż przyciski przy dużej liście)
        prod_to_delete = st.selectbox("Wybierz produkt do usunięcia", 
                                      options=products, 
                                      format_func=lambda x: f"{x['name']} ({x['price']} PLN)")
        
        if st.button("Usuń wybrany produkt", type="primary"):
            delete_product(prod_to_delete['id'])
            st.rerun()
    else:
        st.info("Brak produktów w bazie.")
