import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import requests
from bs4 import BeautifulSoup as bs
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
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def create_url_pairs(bookland_urls, taniaksiazka_urls):
    """Łączy URLe w pary na podstawie ich indeksów."""
    if len(bookland_urls) != len(taniaksiazka_urls):
        st.error("Liczba adresów z obu źródeł musi być taka sama!")
        return []
    
    return list(zip(bookland_urls, taniaksiazka_urls))

def get_bookland_description(url):
    """ Pobiera opis książki z Bookland przy użyciu requests + BeautifulSoup """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            soup = bs(response.text, "html.parser")
            title_element = soup.select_one("h1")
            desc_element = soup.select_one(".ProductInformation-Description")
            
            title = title_element.get_text(strip=True) if title_element else "Brak tytułu"
            description = desc_element.get_text(strip=True) if desc_element else "Brak opisu"

            return title, description
        else:
            return "Błąd pobierania", "Nie udało się pobrać strony"
    except Exception as e:
        return "Błąd pobierania", str(e)

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

    for idx, match in enumerate(matches):
        debug_info = f"Przetwarzanie {idx + 1}/{total}:\nAktualna liczba przetworzonych: {len(data)}"
        debug_container.text(debug_info)
        
        progress = (idx + 1) / total
        bookland_url = match['URL Bookland']
        taniaksiazka_url = match['URL TaniaKsiazka']

        update_status(f"=== Rozpoczynam przetwarzanie produktu {idx + 1}/{total} ===")
        update_status(f"📖 Bookland URL: {bookland_url}")

        try:
            # Pobranie danych z Bookland
            title, bookland_description = get_bookland_description(bookland_url)

            update_status(f"📗 Pobrano tytuł: {title}")
            update_status(f"📝 Opis (długość: {len(bookland_description)} znaków)")

            # Generowanie nowego opisu
            if title or bookland_description:
                update_status("✨ Generowanie nowego opisu...")
                content = f"{title}\n{bookland_description}"

                messages = [
                    {"role": "system", "content": """Jesteś ekspertem w tworzeniu opisów produktów książkowych, 
                    specjalizującym się w SEO i marketingu. Tworzysz przekonujące, angażujące opisy, 
                    które skutecznie prezentują książkę potencjalnym czytelnikom."""},
                    {"role": "user", "content": f"Oto tytuł i aktualny opis książki:\n{content}\n"}
                ]

                messages.append({"role": "user", "content": """Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:

1. Wykorzystywać tagi HTML (nie Markdown):
   - <h2> dla podtytułów sekcji
   - <p> dla paragrafów
   - <b> dla wyróżnienia kluczowych fraz
   - <ul>/<li> dla list

2. Zawierać następujące sekcje:
<h2>{Unikalne, kreatywne hasło związane z treścią książki - NIE UŻYWAJ standardowych fraz jak "Odkryj tajemnice", "Poznaj", "Zanurz się". Zamiast tego użyj specyficznego odwołania do treści książki, np. dla kryminału: "Mroczne uliczki Krakowa kryją zabójczą tajemnicę" lub dla książki fantasy: "Smocze królestwa wzywają śmiałków"}.</h2>
   <p>{Wprowadzenie prezentujące główne zalety i unikalne cechy książki}</p>
   <p>{Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi}</p>
   <p>{Wartości i korzyści dla czytelnika}</p>
   <p>{Określenie grupy docelowej i rekomendacje}</p>
   <p>{Podsumowanie opinii czytelników z nawiązaniem do konkretów}</p>
   <h3>Przekonujący call to action</h3>

3. Wykorzystywać słownictwo odpowiednie dla gatunku książki i dostosowane do odbiorców. Nie zwracaj żadnych dodatkowych komentarzy tylko sam opis"""})

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.7,
                    n=1
                )

                generated_text = response.choices[0].message.content.strip()
                update_status("✅ Otrzymano odpowiedź z GPT")

                data.append({
                    "URL Bookland": bookland_url,
                    "URL TaniaKsiazka": taniaksiazka_url,
                    "Wygenerowany opis HTML": generated_text,
                    "Stary opis Bookland": bookland_description,
                    "Tytuł": title,
                })

                update_status(f"🎉 Dodano nowy opis. Aktualna liczba opisów: {len(data)}", "success")

        except Exception as e:
            update_status(f"❌ Błąd dla URL {bookland_url}: {str(e)}", "error")

        status_container.info(f'📘 Przetworzono {idx + 1} z {total} produktów')
        progress_bar.progress(progress)

    return data


# Main logic
if bookland_urls_input and taniaksiazka_urls_input:
    bookland_urls = [url.strip() for url in bookland_urls_input.strip().split("\n") if url.strip()]
    taniaksiazka_urls = [url.strip() for url in taniaksiazka_urls_input.strip().split("\n") if url.strip()]
    
    url_pairs = create_url_pairs(bookland_urls, taniaksiazka_urls)
    
    if url_pairs:
        st.session_state.matches = [{"URL Bookland": b, "URL TaniaKsiazka": t} for b, t in url_pairs]

        if st.button("Generuj opisy"):
            data = generate_descriptions(st.session_state.matches)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, height=400)
                csv = df.to_csv(index=False)
                st.download_button(label="📥 Pobierz wszystko w CSV", data=csv, file_name="opis_ksiazek.csv", mime="text/csv")
