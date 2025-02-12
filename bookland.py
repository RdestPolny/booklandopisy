import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from openai import OpenAI

# --- Konfiguracja domyślnych promptów z placeholderami ---
default_prompt_lubimyczytac = """Na podstawie poniższych danych stwórz zoptymalizowany pod SEO opis książki w HTML.
Dane:
Opis książki: {description}
Opinie czytelników: {reviews}

Opis powinien zawierać:
- Nagłówek <h2> z kreatywnym hasłem.
- Kilka akapitów <p> z kluczowymi informacjami.
- Przekonujący call to action w formie <h3>.

Używaj wyłącznie tagów HTML (nie Markdown) i nie dodawaj dodatkowych komentarzy.
"""

default_prompt_taniaksiazka = """Na podstawie poniższych danych stwórz angażujący, zoptymalizowany pod SEO opis produktu w HTML.
Dane:
Tytuł: {title}
Szczegóły produktu: {details}
Opis produktu: {description}

Opis powinien zawierać:
- Nagłówek <h2> z kreatywnym hasłem odnoszącym się do tytułu.
- Kilka akapitów <p> z kluczowymi informacjami.
- Listę <ul><li> z najważniejszymi szczegółami (np. autorzy, rok wydania, oprawa, ilość stron, język, podtytuł, ISBN, dane producenta).
- Przekonujący call to action w formie <h3>.

Używaj wyłącznie tagów HTML (nie Markdown) i nie dodawaj dodatkowych komentarzy.
"""

# --- Pasek boczny z konfiguracją promptów ---
st.sidebar.header("Konfiguracja promptów")

# Dla domeny Lubimy Czytac
option_lubimyczytac = st.sidebar.selectbox("Prompt dla Lubimy Czytac", ["Domyślny", "Własny"], key="prompt_lubimyczytac_option")
if option_lubimyczytac == "Własny":
    custom_prompt_lubimyczytac = st.sidebar.text_area("Edytuj prompt dla Lubimy Czytac", value="", key="custom_prompt_lubimyczytac")
else:
    custom_prompt_lubimyczytac = st.sidebar.text_area("Edytuj prompt dla Lubimy Czytac", value=default_prompt_lubimyczytac, key="custom_prompt_lubimyczytac")
st.sidebar.markdown(
    "**Legenda dla Lubimy Czytac:**  \n"
    "- `{description}`: Opis książki  \n"
    "- `{reviews}`: Opinie czytelników"
)

# Dla domeny taniaksiazka.pl
option_taniaksiazka = st.sidebar.selectbox("Prompt dla taniaksiazka.pl", ["Domyślny", "Własny"], key="prompt_taniaksiazka_option")
if option_taniaksiazka == "Własny":
    custom_prompt_taniaksiazka = st.sidebar.text_area("Edytuj prompt dla taniaksiazka.pl", value="", key="custom_prompt_taniaksiazka")
else:
    custom_prompt_taniaksiazka = st.sidebar.text_area("Edytuj prompt dla taniaksiazka.pl", value=default_prompt_taniaksiazka, key="custom_prompt_taniaksiazka")
st.sidebar.markdown(
    "**Legenda dla taniaksiazka.pl:**  \n"
    "- `{title}`: Tytuł książki  \n"
    "- `{details}`: Szczegóły produktu  \n"
    "- `{description}`: Opis produktu"
)

# --- Inicjalizacja Streamlit UI głównej części ---
st.title('Generator Opisów Książek')

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Formularz – użytkownik wkleja URL-e, a przetwarzanie uruchamia się po kliknięciu przycisku "Uruchom"
with st.form("url_form"):
    urls_input = st.text_area('Wprowadź adresy URL (po jednym w linii):')
    submit_button = st.form_submit_button("Uruchom")

# --- Funkcje pobierające dane z poszczególnych stron ---

def get_lubimyczytac_data(url):
    """Pobiera opis i opinie z LubimyCzytac"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = bs(response.text, 'html.parser')
        
        # Pobieranie opisu książki
        description_div = soup.find('div', id='book-description')
        description = description_div.get_text(strip=True) if description_div else ''
        
        # Pobieranie opinii
        reviews = []
        for review in soup.select('p.expandTextNoJS.p-expanded.js-expanded'):
            text = review.get_text(strip=True)
            if len(text) > 50:
                reviews.append(text)
        
        return {
            'description': description,
            'reviews': "\n\n---\n\n".join(reviews) if reviews else '',
            'error': None
        }
    except Exception as e:
        return {
            'description': '',
            'reviews': '',
            'error': f"Błąd pobierania: {str(e)}"
        }

def get_taniaksiazka_data(url):
    """
    Pobiera dane ze strony taniaksiazka.pl:
      - Tytuł (z <h1>)
      - Szczegóły (z <div id="szczegoly">, element <ul class="bullet">)
      - Opis (z <div id="product-description">)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = bs(response.text, 'html.parser')
        
        # Pobieramy tytuł książki z <h1>
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Pobieramy szczegóły – szukamy diva o id "szczegoly" i wewnątrz <ul class="bullet">
        details_text = ""
        details_div = soup.find("div", id="szczegoly")
        if details_div:
            ul = details_div.find("ul", class_="bullet")
            if ul:
                li_elements = ul.find_all("li")
                details_list = [li.get_text(separator=" ", strip=True) for li in li_elements]
                details_text = "\n".join(details_list)
        
        # Pobieramy opis – szukamy diva o id "product-description"
        description_text = ""
        description_div = soup.find("div", id="product-description")
        if description_div:
            description_text = description_div.get_text(separator="\n", strip=True)
        
        return {
            'title': title,
            'details': details_text,
            'description': description_text,
            'error': None
        }
    except Exception as e:
        return {
            'title': '',
            'details': '',
            'description': '',
            'error': f"Błąd pobierania: {str(e)}"
        }

# --- Funkcje generujące opisy, wykorzystujące edytowalne prompt-y z placeholderami ---

def generate_description_lubimyczytac(book_data, prompt_template):
    """
    Generuje nowy opis na podstawie danych z LubimyCzytac.
    W miejscu placeholderów {description} i {reviews} w prompt_template wstawiane są dane.
    """
    try:
        prompt_filled = prompt_template.format(
            description=book_data.get('description', ''),
            reviews=book_data.get('reviews', '')
        )
        messages = [
            {
                "role": "system",
                "content": "Jesteś profesjonalnym copywriterem specjalizującym się w tworzeniu opisów książek. Twórz angażujące opisy w HTML z wykorzystaniem tagów <h2>, <p>, <b>, <ul>, <li>."
            },
            {
                "role": "user",
                "content": prompt_filled
            }
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Błąd generowania opisu: {str(e)}")
        return ""

def generate_description_taniaksiazka(book_data, prompt_template):
    """
    Generuje nowy opis produktu na podstawie danych ze strony taniaksiazka.pl.
    W miejscu placeholderów {title}, {details} oraz {description} w prompt_template wstawiane są dane.
    """
    try:
        prompt_filled = prompt_template.format(
            title=book_data.get('title', ''),
            details=book_data.get('details', ''),
            description=book_data.get('description', '')
        )
        messages = [
            {
                "role": "system",
                "content": "Jesteś doświadczonym copywriterem specjalizującym się w tworzeniu opisów produktów dla księgarni internetowej."
            },
            {
                "role": "user",
                "content": prompt_filled
            }
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Błąd generowania opisu: {str(e)}")
        return ""

# --- Przetwarzanie danych po zatwierdzeniu formularza ---
if submit_button:
    if urls_input:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(urls):
            status_text.info(f'Przetwarzanie {idx+1}/{len(urls)}...')
            progress_bar.progress((idx + 1) / len(urls))
            url_lower = url.lower()
            
            if "lubimyczytac" in url_lower:
                book_data = get_lubimyczytac_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_lubimyczytac(book_data, custom_prompt_lubimyczytac)
                results.append({
                    'URL': url,
                    'Stary opis': book_data.get('description', ''),
                    'Opinie': book_data.get('reviews', ''),
                    'Nowy opis': new_description
                })
            elif "taniaksiazka.pl" in url_lower:
                book_data = get_taniaksiazka_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_taniaksiazka(book_data, custom_prompt_taniaksiazka)
                results.append({
                    'URL': url,
                    'Tytuł': book_data.get('title', ''),
                    'Szczegóły': book_data.get('details', ''),
                    'Opis': book_data.get('description', ''),
                    'Nowy opis': new_description
                })
            else:
                st.error(f"Nieobsługiwana domena dla {url}")
                continue
                
            time.sleep(3)  # Ograniczenie częstotliwości zapytań
            
        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Pobierz dane",
                data=csv,
                file_name='wygenerowane_opisy.csv',
                mime='text/csv'
            )
        else:
            st.warning("Nie udało się wygenerować żadnych opisów")
    else:
        st.warning("Proszę wprowadzić adresy URL.")
