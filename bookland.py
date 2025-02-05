import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup as bs
import time
from requests_html import AsyncHTMLSession
import asyncio
import nest_asyncio

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Książek')

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input fields
st.subheader("Adresy URL z LubimyCzytac")
lubimyczytac_urls_input = st.text_area('Wprowadź adresy URL z LubimyCzytac (po jednym w linii):')

st.subheader("Adresy URL z Bookland")
bookland_urls_input = st.text_area('Wprowadź adresy URL z Bookland (po jednym w linii):')

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
        
        # Pobieranie opinii z określonego selektora
        reviews = []
        for review in soup.select('p.expandTextNoJS.p-expanded.js-expanded'):
            text = review.get_text(strip=True)
            if len(text) > 50:  # Filtrujemy krótkie komentarze
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

def get_bookland_data(url):
    """Pobiera opis z Bookland używając requests"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = bs(response.text, 'html.parser')
        
        # Znajdź element z opisem
        description_elem = soup.find('div', class_='ProductInformation-Description')
        description = description_elem.get_text(strip=True) if description_elem else ''
        
        return {
            'description': description,
            'error': None
        }
        
    except Exception as e:
        return {
            'description': '',
            'error': f"Błąd pobierania z Bookland: {str(e)}"
        }

def generate_description(book_data):
    """Generuje nowy opis przy użyciu OpenAI"""
    try:
        messages = [
            {
                "role": "system",
                "content": """Jesteś profesjonalnym copywriterem specjalizującym się w tworzeniu opisów książek. 
                Twórz angażujące opisy w HTML z wykorzystaniem:<h2>, <p>, <b>, <ul>, <li>. 
                Uwzględnij opinie czytelników oraz opis z Bookland."""
            },
            {
                "role": "user",
                "content": f"""OPIS Z LUBIMYCZYTAC: {book_data.get('lc_description', '')}
                              OPIS Z BOOKLAND: {book_data.get('bookland_description', '')}
                              OPINIE CZYTELNIKÓW: {book_data.get('reviews', '')}"""
            },
            {
                "role": "user",
                "content": """Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:

1. Zaczyna się od mocnego nagłówka <h2> z kreatywnym hasłem nawiązującym do treści książki.
2. Zawiera sekcje:
   - <p>Wprowadzenie z głównymi zaletami książki</p>
   - <p>Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi</p>
   - <p>Wartości i korzyści dla czytelnika</p>
   - <p>Podsumowanie opinii czytelników z konkretnymi przykładami</p>
   - <h3>Przekonujący call to action</h3>

3. Wykorzystuje opinie czytelników i opis z Bookland, aby:
   - Podkreślić najczęściej wymieniane zalety książki
   - Wzmocnić wiarygodność opisu
   - Dodać emocje i autentyczność

4. Formatowanie:
   - Używaj tagów HTML: <h2>, <p>, <b>, <h3>
   - Wyróżniaj kluczowe frazy za pomocą <b>
   - Nie używaj znaczników Markdown, tylko HTML
   - Nie dodawaj komentarzy ani wyjaśnień, tylko sam opis"""
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Błąd generowania opisu: {str(e)}")
        return ""

def main():
    if lubimyczytac_urls_input and bookland_urls_input:
        # Przygotowanie list URL-i
        lubimyczytac_urls = [url.strip() for url in lubimyczytac_urls_input.split('\n') if url.strip()]
        bookland_urls = [url.strip() for url in bookland_urls_input.split('\n') if url.strip()]
        
        # Sprawdzenie czy liczba URL-i się zgadza
        if len(lubimyczytac_urls) != len(bookland_urls):
            st.error('Liczba adresów URL z obu źródeł musi być taka sama!')
            return
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Iteracja po sparowanych URL-ach
        for idx, (lc_url, bookland_url) in enumerate(zip(lubimyczytac_urls, bookland_urls)):
            try:
                # Aktualizacja statusu
                status_text.info(f'Przetwarzanie {idx+1}/{len(lubimyczytac_urls)}...')
                progress_bar.progress((idx + 1) / len(lubimyczytac_urls))
                
                # Pobieranie danych z LubimyCzytac
                lc_data = get_lubimyczytac_data(lc_url)
                if lc_data.get('error'):
                    st.error(f"Błąd dla {lc_url}: {lc_data['error']}")
                    continue
                
                # Pobieranie danych z Bookland
                bookland_data = get_bookland_data(bookland_url)
                if bookland_data.get('error'):
                    st.error(f"Błąd dla {bookland_url}: {bookland_data['error']}")
                    continue
                    
                # Generowanie opisu
                new_description = generate_description({
                    'lc_description': lc_data.get('description', ''),
                    'bookland_description': bookland_data.get('description', ''),
                    'reviews': lc_data.get('reviews', '')
                })
                
                results.append({
                    'URL LubimyCzytac': lc_url,
                    'URL Bookland': bookland_url,
                    'Opis LubimyCzytac': lc_data.get('description', ''),
                    'Opis Bookland': bookland_data.get('description', ''),
                    'Nowy opis': new_description,
                    'Opinie': lc_data.get('reviews', '')
                })
                
                time.sleep(3)  # Ograniczenie requestów
                
            except Exception as e:
                st.error(f"Błąd przetwarzania: {str(e)}")
                continue
                
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

if __name__ == '__main__':
    main()
