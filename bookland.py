import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from openai import OpenAI

# ------------------------#
# Domyślne prompty z unikalnymi zmiennymi
# ------------------------#

default_prompt_lubimyczytac = """Na podstawie poniższych danych stwórz zoptymalizowany pod SEO opis książki w HTML.
Dane:
Opis książki: {lubimy_description}
Opinie czytelników: {lubimy_reviews}

Opis powinien zawierać:
- Nagłówek <h2> z kreatywnym hasłem.
- Kilka akapitów <p> z kluczowymi informacjami.
- Przekonujący call to action w formie <h3>.

Używaj wyłącznie tagów HTML (nie Markdown) i nie dodawaj dodatkowych komentarzy.
"""

default_prompt_taniaksiazka = """Na podstawie poniższych danych stwórz angażujący, zoptymalizowany pod SEO opis produktu w HTML.
Dane:
Tytuł: {taniaksiazka_title}
Szczegóły produktu: {taniaksiazka_details}
Opis produktu: {taniaksiazka_description}

Opis powinien zawierać:
- Nagłówek <h2> z kreatywnym hasłem odnoszącym się do tytułu.
- Kilka akapitów <p> z kluczowymi informacjami.
- Listę <ul><li> z najważniejszymi szczegółami (np. autorzy, rok wydania, oprawa, ilość stron, język, podtytuł, ISBN, dane producenta).
- Przekonujący call to action w formie <h3>.

Używaj wyłącznie tagów HTML (nie Markdown) i nie dodawaj dodatkowych komentarzy.
"""

# ------------------------#
# Pasek boczny – konfiguracja promptów
# ------------------------#

st.sidebar.header("Konfiguracja promptów")

# Konfiguracja promptu dla Lubimy Czytac (uproszczona)
option_lubimyczytac = st.sidebar.selectbox("Prompt dla Lubimy Czytac", ["Domyślny", "Własny"], key="prompt_lubimy_option")
if option_lubimyczytac == "Własny":
    custom_prompt_lubimyczytac = st.sidebar.text_area("Edytuj prompt dla Lubimy Czytac", value="", key="custom_prompt_lubimy")
else:
    custom_prompt_lubimyczytac = st.sidebar.text_area("Edytuj prompt dla Lubimy Czytac", value=default_prompt_lubimyczytac, key="custom_prompt_lubimy")
st.sidebar.markdown(
    "**Legenda dla Lubimy Czytac:**  \n"
    "- `{lubimy_description}`: Opis książki  \n"
    "- `{lubimy_reviews}`: Opinie czytelników"
)

# Zaawansowana konfiguracja promptów dla taniaksiazka.pl
if "taniaksiazka_prompts" not in st.session_state:
    st.session_state.taniaksiazka_prompts = [{"name": "Domyślny", "text": default_prompt_taniaksiazka}]

st.sidebar.header("Prompty dla taniaksiazka.pl")
selected_taniaksiazka_prompt_index = st.sidebar.selectbox(
    "Wybierz prompt",
    list(range(len(st.session_state.taniaksiazka_prompts))),
    format_func=lambda i: st.session_state.taniaksiazka_prompts[i]["name"],
    key="selected_taniaksiazka_prompt_index"
)
edited_taniaksiazka_prompt = st.sidebar.text_area(
    "Edytuj wybrany prompt", 
    value=st.session_state.taniaksiazka_prompts[selected_taniaksiazka_prompt_index]["text"], 
    key="edited_taniaksiazka_prompt"
)
if st.sidebar.button("Zapisz zmiany dla wybranego promptu"):
    st.session_state.taniaksiazka_prompts[selected_taniaksiazka_prompt_index]["text"] = edited_taniaksiazka_prompt
    st.sidebar.success("Prompt zaktualizowany!")

st.sidebar.markdown(
    "**Legenda dla taniaksiazka.pl:**  \n"
    "- `{taniaksiazka_title}`: Tytuł książki  \n"
    "- `{taniaksiazka_details}`: Szczegóły produktu  \n"
    "- `{taniaksiazka_description}`: Opis produktu"
)

new_prompt_name = st.sidebar.text_input("Nazwa nowego promptu", key="new_prompt_name")
new_prompt_text = st.sidebar.text_area("Tekst nowego promptu", value="", key="new_prompt_text")
if st.sidebar.button("Dodaj nowy prompt"):
    if new_prompt_name and new_prompt_text:
        st.session_state.taniaksiazka_prompts.append({"name": new_prompt_name, "text": new_prompt_text})
        st.sidebar.success(f"Prompt '{new_prompt_name}' dodany!")
    else:
        st.sidebar.error("Wprowadź nazwę i tekst nowego promptu.")

# ------------------------#
# Główna część aplikacji
# ------------------------#

st.title('Generator Opisów Książek')

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Formularz – użytkownik wkleja URL-e, przetwarzanie uruchamia się po kliknięciu "Uruchom"
with st.form("url_form"):
    urls_input = st.text_area('Wprowadź adresy URL (po jednym w linii):')
    submit_button = st.form_submit_button("Uruchom")

# ------------------------#
# Funkcje pobierające dane
# ------------------------#

def get_lubimyczytac_data(url):
    """Pobiera opis i opinie z Lubimy Czytac."""
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

# ------------------------#
# Funkcje generujące opisy z wykorzystaniem promptów
# ------------------------#

def generate_description_lubimyczytac(book_data, prompt_template):
    """
    Generuje nowy opis na podstawie danych z Lubimy Czytac.
    W miejsce placeholderów {lubimy_description} i {lubimy_reviews} w prompt_template wstawiane są dane.
    """
    try:
        prompt_filled = prompt_template.format(
            lubimy_description=book_data.get('description', ''),
            lubimy_reviews=book_data.get('reviews', '')
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
    W miejsce placeholderów {taniaksiazka_title}, {taniaksiazka_details} oraz {taniaksiazka_description} w prompt_template wstawiane są dane.
    """
    try:
        prompt_filled = prompt_template.format(
            taniaksiazka_title=book_data.get('title', ''),
            taniaksiazka_details=book_data.get('details', ''),
            taniaksiazka_description=book_data.get('description', '')
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

# ------------------------#
# Przetwarzanie danych po zatwierdzeniu formularza
# ------------------------#

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
                # Używamy wybranego promptu dla taniaksiazka.pl
                custom_prompt = st.session_state.taniaksiazka_prompts[selected_taniaksiazka_prompt_index]["text"]
                new_description = generate_description_taniaksiazka(book_data, custom_prompt)
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
