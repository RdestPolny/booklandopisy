import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import requests
from bs4 import BeautifulSoup as bs
from playwright.sync_api import sync_playwright
import time

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Produktów')

# Containers for status messages
status_container = st.empty()
progress_bar = st.empty()

# Input fields - dwa pola na URLe
col1, col2 = st.columns(2)
with col1:
    bookland_urls_input = st.text_area('Wprowadź adresy URL z Bookland (po jednym w linii):')
with col2:
    taniaksiazka_urls_input = st.text_area('Wprowadź odpowiadające adresy URL z TaniaKsiazka (po jednym w linii):')

# Initialize OpenAI client
client = OpenAI(api_key='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')

def create_url_pairs(bookland_urls, taniaksiazka_urls):
    """Łączy URLe w pary na podstawie ich indeksów."""
    if len(bookland_urls) != len(taniaksiazka_urls):
        st.error("Liczba adresów z obu źródeł musi być taka sama!")
        return []
    
    return list(zip(bookland_urls, taniaksiazka_urls))

def wait_for_page_load(page, selector):
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        return True
    except Exception as e:
        st.write(f"Błąd oczekiwania na element {selector}: {str(e)}")
        return False

def get_reviews_from_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Connection': 'keep-alive',
        }
        
        st.write(f"Pobieranie opinii poprzez request z: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = bs(response.text, 'html.parser')
            review_elements = soup.select('p.expandTextNoJS.p-expanded.js-expanded')
            
            reviews = []
            for element in review_elements:
                review_text = element.get_text(strip=True)
                if review_text and len(review_text) > 50:
                    reviews.append(review_text)
            
            if reviews:
                st.write(f"Znaleziono {len(reviews)} opinii")
                return "\n\n---\n\n".join(reviews)
            else:
                st.write("Nie znaleziono opinii na stronie")
                return ""
        else:
            st.write(f"Błąd pobierania strony. Status code: {response.status_code}")
            return ""
            
    except Exception as e:
        st.write(f"Błąd podczas pobierania opinii: {str(e)}")
        return ""

def generate_descriptions(matches):
    total = len(matches)
    data = []
    debug_container = st.empty()
    status_log = st.empty()

    def update_status(message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        if level == "error":
            status_log.error(f"{timestamp} - {message}")
        elif level == "success":
            status_log.success(f"{timestamp} - {message}")
        else:
            status_log.info(f"{timestamp} - {message}")

    try:
        with sync_playwright() as p:
            update_status("Uruchamianie przeglądarki...")
            browser = p.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context()
            page = context.new_page()

            for idx, match in enumerate(matches):
                debug_info = f"Przetwarzanie {idx + 1}/{total}:\nAktualna liczba przetworzonych: {len(data)}"
                debug_container.text(debug_info)
                
                progress = (idx + 1) / total
                bookland_url = match['URL Bookland']
                taniaksiazka_url = match['URL TaniaKsiazka']
                
                update_status(f"=== Rozpoczynam przetwarzanie produktu {idx + 1}/{total} ===")
                update_status(f"Bookland URL: {bookland_url}")

                try:
                    # Get Bookland description
                    update_status("Pobieranie danych z Bookland...")
                    page.goto(bookland_url, timeout=50000, wait_until='networkidle')
                    page.wait_for_timeout(3000)  # Dodatkowe czekanie
                    
                    h1 = ''
                    bookland_description = ''
                    
                    try:
                        h1_element = page.wait_for_selector('h1', timeout=10000)
                        h1 = h1_element.inner_text() if h1_element else ''
                        update_status(f"Pobrano tytuł: {h1}")
                    except Exception as e:
                        update_status(f"Błąd podczas pobierania tytułu: {str(e)}", "error")

                    try:
                        desc_element = page.query_selector('.ProductInformation-Description')
                        bookland_description = desc_element.inner_text() if desc_element else ''
                        update_status(f"Pobrano opis (długość: {len(bookland_description)} znaków)")
                    except Exception as e:
                        update_status(f"Błąd podczas pobierania opisu: {str(e)}", "error")


                    # Get reviews from LubimyCzytac
                    reviews = ''
                    try:
                        lubimyczytac_url = taniaksiazka_url.replace('taniaksiazka.pl', 'lubimyczytac.pl/ksiazka')
                        update_status("Rozpoczynam pobieranie opinii z LubimyCzytac...")
                        reviews = get_reviews_from_url(lubimyczytac_url)
                        if reviews:
                            update_status(f"Pobrano recenzje (długość: {len(reviews)})")
                        else:
                            update_status("Nie znaleziono recenzji")
                    except Exception as e:
                        update_status(f"Błąd pobierania opinii: {str(e)}", "error")

                    # Generate new description
                    if h1 or bookland_description:
                        update_status("Generowanie nowego opisu...")
                        content = f"{h1}\n{bookland_description}"
                        
        
                        
                        messages = [
                            {"role": "system", "content": """Jesteś ekspertem w tworzeniu opisów produktów książkowych, 
                            specjalizującym się w SEO i marketingu. Tworzysz przekonujące, angażujące opisy, 
                            które skutecznie prezentują książkę potencjalnym czytelnikom."""},
                            {"role": "user", "content": f"Oto tytuł i aktualny opis książki:\n{content}\n"}
                        ]

                        if reviews:
                            messages.append({"role": "user", "content": f"Oto autentyczne opinie czytelników o tej książce:\n{reviews}"})

                        messages.append({"role": "user", "content": """Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:

1. Wykorzystywać tagi HTML (nie Markdown):
   - <h2> dla podtytułów sekcji
   - <p> dla paragrafów
   - <b> dla wyróżnienia kluczowych fraz
   - <ul>/<li> dla list

2. Zawierać następujące sekcje:
<h2>{Unikalne, kreatywne hasło związane z treścią książki - NIE UŻYWAJ standardowych fraz jak "Odkryj tajemnice", "Poznaj", "Zanurz się". Zamiast tego użyj specyficznego odwołania do treści książki, np. dla kryminału: "Mroczne uliczki Krakowa kryją zabójczą tajemnicę" lub dla książki fantasy: "Smocze królestwa wzywają śmiałków"}.</h2>   <p>{Wprowadzenie prezentujące główne zalety i unikalne cechy książki}</p>
   <p>{Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi}</p>
   <p>{Wartości i korzyści dla czytelnika}</p>
   <p>{Określenie grupy docelowej i rekomendacje}</p>
   <p>{Podsumowanie opinii czytelników z nawiązaniem do konkretów}</p>
   <h3>Przekonujący call to action</h3>

3. Wykorzystywać słownictwo odpowiednie dla gatunku książki i dostosowane do odbiorców. Nie zwracaj żadnych dodatkowych komentarzy tylko sam opis"""})

                        update_status("Wysyłanie zapytania do GPT...")
                        response = client.chat.completions.create(
                            model='gpt-4o-mini',
                            messages=messages,
                            max_tokens=4000,
                            temperature=0.7,
                            n=1
                        )

                        generated_text = response.choices[0].message.content.strip()
                        update_status("Otrzymano odpowiedź z GPT")
                        
                        if '**' in generated_text or '#' in generated_text:
                            update_status("Konwersja znaczników markdown na HTML...")
                            generated_text = generated_text.replace('**', '<b>').replace('**', '</b>')
                            generated_text = re.sub(r'^#\s+', '<h1>', generated_text, flags=re.MULTILINE)
                            generated_text = re.sub(r'^##\s+', '<h2>', generated_text, flags=re.MULTILINE)
                            generated_text = re.sub(r'^###\s+', '<h3>', generated_text, flags=re.MULTILINE)

                        if not generated_text.startswith('```html'):
                            generated_text = f"```html\n{generated_text}\n```"

                        data.append({
                            'URL Bookland': bookland_url,
                            'URL TaniaKsiazka': taniaksiazka_url,
                            'Wygenerowany opis HTML': generated_text,
                            'Opinie z Lubimy Czytać': reviews,
                            'Stary opis Bookland': bookland_description,
                            'H1': h1,
                        })
                        update_status(f"Dodano nowy opis. Aktualna liczba opisów: {len(data)}", "success")

                except Exception as e:
                    update_status(f"Błąd dla URL {bookland_url}: {str(e)}", "error")

                status_container.info(f'Przetworzono {idx + 1} z {total} produktów')
                progress_bar.progress(progress)
                
                update_status("Przerwa przed następnym produktem...")
                page.wait_for_timeout(3000)

            browser.close()
            update_status(f"Zakończono przetwarzanie. Liczba zebranych opisów: {len(data)}", "success")
        return data

    except Exception as e:
        update_status(f"Błąd krytyczny: {str(e)}", "error")
        return []

# Main logic
if bookland_urls_input and taniaksiazka_urls_input:
    bookland_urls = [url.strip() for url in bookland_urls_input.strip().split('\n') if url.strip()]
    taniaksiazka_urls = [url.strip() for url in taniaksiazka_urls_input.strip().split('\n') if url.strip()]
    
    # Tworzenie par URLi
    url_pairs = create_url_pairs(bookland_urls, taniaksiazka_urls)
    
    if url_pairs:
        if 'matches' not in st.session_state:
            st.session_state.matches = [{'URL Bookland': b, 'URL TaniaKsiazka': t} for b, t in url_pairs]
        
        matches_df = pd.DataFrame(st.session_state.matches)
        st.write("Wprowadzone pary adresów:")
        st.dataframe(matches_df)

        # Generate descriptions button
        if st.button('Generuj opisy'):
            data = generate_descriptions(st.session_state.matches)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, height=400)
                csv = df.to_csv(index=False)
                st.download_button(
                    label='Pobierz wszystko w CSV',
                    data=csv,
                    file_name='opis_ksiazek.csv',
                    mime='text/csv'
                )
            else:
                st.info('Brak danych do wyświetlenia.')