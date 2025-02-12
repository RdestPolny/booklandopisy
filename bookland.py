import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from openai import OpenAI

# ------------------------#
# Domyślne prompt'y z unikalnymi zmiennymi
# ------------------------#

default_prompt_lubimyczytac = """Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:

Dane:
Tytuł książki: {lubimy_title}
Opis książki: {lubimy_description}
Opinie czytelników: {lubimy_reviews}

Opis powinien zawierać:
1. Zaczyna się od mocnego nagłówka <h2> z kreatywnym hasłem nawiązującym do treści książki.
2. Zawiera sekcje:
   - <p>Wprowadzenie z głównymi zaletami książki</p>
   - <p>Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi</p>
   - <p>Wartości i korzyści dla czytelnika</p>
   - <p>Podsumowanie opinii czytelników z konkretnymi przykładami</p>
   - <h3>Przekonujący call to action</h3>
3. Wykorzystuje opinie czytelników, aby:
   - Podkreślić najczęściej wymieniane zalety książki
   - Wzmocnić wiarygodność opisu
   - Dodać emocje i autentyczność
4. Formatowanie:
   - Używaj tagów HTML: <h2>, <p>, <b>, <h3>
   - Wyróżniaj kluczowe frazy za pomocą <b>
   - Nie używaj znaczników Markdown, tylko HTML
   - Nie dodawaj komentarzy ani wyjaśnień, tylko sam opis
5. Styl:
   - Opis ma być angażujący, ale profesjonalny
   - Używaj słownictwa dostosowanego do gatunku książki
   - Unikaj powtórzeń
   - Zachowaj spójność tonu
6. Przykład formatu:
```html
<h2>Przygoda na świeżym powietrzu z tatą Oli czeka na każdą rodzinę!</h2>
<p>„Tata Oli. Tom 3. Z tatą Oli na biwaku” to <b>pełna humoru</b> i <b>przygód</b> opowieść, która z pewnością zachwyci najmłodszych czytelników oraz ich rodziców. Ta książka łączy w sobie <b>fantastyczne ilustracje</b> z doskonałym tekstem, który bawi do łez, a jednocześnie skłania do refleksji nad <b>relacjami rodzinnymi</b>.</p>
<p>W tej części tata Oli postanawia <b>oderwać dzieci</b> od ekranów i zorganizować im prawdziwy <b>biwak</b>. Wspólnie stają przed nie lada wyzwaniem: muszą <b>rozpalić ognisko</b>, <b>łowić ryby</b> i cieszyć się <b>urokami natury</b>. Jednak zamiast sielanki, napotykają na wiele zabawnych przeszkód, co prowadzi do sytuacji pełnych <b>śmiechu</b> i <b>niespodzianek</b>. Tata Oli, z typową dla siebie pomysłowością, staje przed wyzwaniami, które pokazują, że nie zawsze wszystko idzie zgodnie z planem, a <b>życie na łonie natury</b> może być pełne <b>przygód</b>.</p>
<p>Książka ta wartościowo rozwija wyobraźnię dzieci, pokazując, że <b>spędzanie czasu z rodziną</b> na świeżym powietrzu może być nie tylko zabawne, ale również <b>edukacyjne</b>. Dzięki humorystycznym sytuacjom z udziałem taty Oli, dzieci uczą się, że dorośli także mają swoje słabości, co czyni tę lekturę <b>uniwersalną</b>.</p>
<p>„Z tatą Oli na biwaku” to idealna propozycja dla <b>dzieci w wieku przedszkolnym i wczesnoszkolnym</b>, a także dla rodziców, którzy pragną spędzić czas z dziećmi w <b>zabawny</b> i <b>interaktywny</b> sposób. To książka, która rozbawi i dostarczy wielu emocji.</p>
<p>Czytelnicy zachwycają się nie tylko <b>lekkością</b> i <b>humorem</b> tekstu, ale także <b>ilustracjami</b>, które wzbogacają opowieść. Wiele osób zauważa, że tata Oli staje się wzorem dla dzieci, pokazując, iż <b>rodzicielstwo</b> to sztuka kompromisu i <b>radości</b>, nawet w trudnych sytuacjach.</p>
<h3>Nie czekaj! Przeżyj niezapomniane chwile z tatą Oli i jego dziećmi na biwaku, zamów swoją książkę już dziś!</h3>
```"""

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
# Sidebar – wybór promptu
# ------------------------#

selected_prompt = st.sidebar.selectbox("Wybierz prompt", ["LC - książki", "TK - Podręczniki"])

if selected_prompt == "LC - książki":
    st.sidebar.markdown(
        "**Legenda dla LC - książki:**  \n"
        "- `{lubimy_title}`: Tytuł książki  \n"
        "- `{lubimy_description}`: Opis książki  \n"
        "- `{lubimy_reviews}`: Opinie czytelników"
    )
elif selected_prompt == "TK - Podręczniki":
    st.sidebar.markdown(
        "**Legenda dla TK - Podręczniki:**  \n"
        "- `{taniaksiazka_title}`: Tytuł książki  \n"
        "- `{taniaksiazka_details}`: Szczegóły produktu  \n"
        "- `{taniaksiazka_description}`: Opis produktu"
    )

# ------------------------#
# Główna część aplikacji
# ------------------------#

st.title('Generator Opisów Książek')
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

with st.form("url_form"):
    urls_input = st.text_area('Wprowadź adresy URL (po jednym w linii):')
    submit_button = st.form_submit_button("Uruchom")

# ------------------------#
# Funkcje pobierające dane
# ------------------------#

def get_lubimyczytac_data(url):
    """Pobiera tytuł, opis i opinie z Lubimy Czytac."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = bs(response.text, 'html.parser')
        
        # Pobieranie tytułu książki z <h1 class="book__title">
        title_tag = soup.find('h1', class_='book__title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
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
            'title': title,
            'description': description,
            'reviews': "\n\n---\n\n".join(reviews) if reviews else '',
            'error': None
        }
    except Exception as e:
        return {
            'title': '',
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
    W miejsce placeholderów {lubimy_title}, {lubimy_description} i {lubimy_reviews} w prompt_template wstawiane są dane.
    """
    try:
        prompt_filled = prompt_template.format(
            lubimy_title=book_data.get('title', ''),
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
            
            # Dla Lubimy Czytac – oczekiwany prompt to "LC - książki"
            if "lubimyczytac" in url_lower:
                if selected_prompt != "LC - książki":
                    st.error(f"Wybrano prompt '{selected_prompt}', ale URL '{url}' pochodzi z Lubimy Czytac. Pomijam ten URL.")
                    continue
                book_data = get_lubimyczytac_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_lubimyczytac(book_data, default_prompt_lubimyczytac)
                results.append({
                    'URL': url,
                    'Tytuł': book_data.get('title', ''),
                    'Stary opis': book_data.get('description', ''),
                    'Opinie': book_data.get('reviews', ''),
                    'Nowy opis': new_description
                })
            # Dla taniaksiazka.pl – oczekiwany prompt to "TK - Podręczniki"
            elif "taniaksiazka.pl" in url_lower:
                if selected_prompt != "TK - Podręczniki":
                    st.error(f"Wybrano prompt '{selected_prompt}', ale URL '{url}' pochodzi z taniaksiazka.pl. Pomijam ten URL.")
                    continue
                book_data = get_taniaksiazka_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                new_description = generate_description_taniaksiazka(book_data, default_prompt_taniaksiazka)
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
