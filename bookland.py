import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from openai import OpenAI

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Książek')

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Formularz – użytkownik wkleja URL-e, a przetwarzanie uruchamia się po kliknięciu przycisku "Uruchom"
with st.form("url_form"):
    urls_input = st.text_area('Wprowadź adresy URL (po jednym w linii):')
    submit_button = st.form_submit_button("Uruchom")

def get_lubimyczytac_data(url):
    """Pobiera opis i opinie z LubimyCzytac (funkcja bez zmian)"""
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
    Pobiera dane ze strony taniaksiazka.pl.
    Wyodrębnia trzy elementy:
      - Tytuł (z <h1>)
      - Szczegóły (z <div id="szczegoly"> -> <ul class="bullet">)
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

def generate_description_lubimyczytac(book_data):
    """Generuje nowy opis na podstawie danych z LubimyCzytac (funkcja bez zmian)"""
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Jesteś profesjonalnym copywriterem specjalizującym się w tworzeniu opisów książek. "
                    "Twórz angażujące opisy w HTML z wykorzystaniem: <h2>, <p>, <b>, <ul>, <li>. "
                    "Uwzględnij opinie czytelników."
                )
            },
            {
                "role": "user",
                "content": f"OPIS KSIĄŻKI: {book_data.get('description', '')}\nOPINIE CZYTELNIKÓW: {book_data.get('reviews', '')}"
            },
            {
                "role": "user",
                "content": (
                    "Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:\n\n"
                    "1. Zaczynać się od mocnego nagłówka <h2> z kreatywnym hasłem nawiązującym do treści książki.\n"
                    "2. Zawierać sekcje:\n"
                    "   - <p>Wprowadzenie z głównymi zaletami książki</p>\n"
                    "   - <p>Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi</p>\n"
                    "   - <p>Wartości i korzyści dla czytelnika</p>\n"
                    "   - <p>Podsumowanie opinii czytelników z konkretnymi przykładami</p>\n"
                    "   - <h3>Przekonujący call to action</h3>\n\n"
                    "3. Wykorzystać opinie czytelników, aby podkreślić zalety książki.\n"
                    "4. Formatowanie: Używaj tagów HTML, nie Markdown.\n"
                    "5. Styl: angażujący, profesjonalny, zoptymalizowany pod SEO."
                )
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

def generate_description_taniaksiazka(book_data):
    """
    Generuje nowy opis produktu na podstawie danych pobranych ze strony taniaksiazka.pl.
    W prompt do API wchodzą:
      - Tytuł (z <h1>)
      - Szczegóły (z sekcji "Szczegóły")
      - Opis (z sekcji "Opis")
    """
    try:
        title = book_data.get("title", "")
        details = book_data.get("details", "")
        description = book_data.get("description", "")
        
        messages = [
            {
                "role": "system",
                "content": "Jesteś doświadczonym copywriterem specjalizującym się w tworzeniu opisów produktów dla księgarni internetowej."
            },
            {
                "role": "user",
                "content": f"Tytuł: {title}\n\nInformacje o produkcie:\nSzczegóły:\n{details}\n\nOpis:\n{description}"
            },
            {
                "role": "user",
                "content": (
                    "Na podstawie powyższych informacji stwórz angażujący, zoptymalizowany pod SEO opis produktu w HTML. "
                    "Opis powinien zawierać:\n"
                    "1. Nagłówek <h2> z kreatywnym hasłem, odnoszącym się do tytułu i zawartości produktu.\n"
                    "2. Kilka akapitów <p> z kluczowymi informacjami o produkcie.\n"
                    "3. Listę <ul><li> z najważniejszymi szczegółami (np. autorzy, rok wydania, oprawa, ilość stron, język, podtytuł, ISBN, dane producenta).\n"
                    "4. Przekonujący call to action w formie nagłówka <h3>.\n"
                    "Używaj tylko tagów HTML (nie Markdown) i nie dodawaj dodatkowych komentarzy."
                )
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

# Przetwarzanie danych po zatwierdzeniu formularza
# Przetwarzanie danych po zatwierdzeniu formularza
if submit_button:
    if urls_input:
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(urls):
            status_text.info(f'Przetwarzanie {idx+1}/{len(urls)}...')
            progress_bar.progress((idx + 1) / len(urls))
            
            # Sprawdzamy domenę, porównując adres URL w wersji lowercase
            if "lubimyczytac" in url.lower():
                book_data = get_lubimyczytac_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_lubimyczytac(book_data)
                results.append({
                    'URL': url,
                    'Stary opis': book_data.get('description', ''),
                    'Opinie': book_data.get('reviews', ''),
                    'Nowy opis': new_description
                })
            elif "taniaksiazka.pl" in url.lower():
                book_data = get_taniaksiazka_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_taniaksiazka(book_data)
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
