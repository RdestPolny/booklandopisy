import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup as bs
import time
import json
import re

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Książek')

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input fields
col1, col2 = st.columns(2)
with col1:
    bookland_urls_input = st.text_area('Wprowadź adresy URL z Bookland (po jednym w linii):')
with col2:
    lubimyczytac_urls_input = st.text_area('Wprowadź adresy URL z LubimyCzytac (po jednym w linii):')

def extract_bookland_data(html_content):
    """Parsuje dane z Bookland z kodu HTML"""
    soup = bs(html_content, 'html.parser')
    
    # Metoda 1: Szukanie danych w tagach script
    script_data = soup.find('script', type='application/ld+json')
    if script_data:
        try:
            product_info = json.loads(script_data.string)
            return {
                'title': product_info.get('name', ''),
                'description': product_info.get('description', ''),
                'error': None
            }
        except json.JSONDecodeError:
            pass
    
    # Metoda 2: Alternatywne parsowanie HTML
    title = soup.find('h1')
    description = soup.select_one('.product-description, .description, .product-info')
    
    return {
        'title': title.get_text(strip=True) if title else '',
        'description': description.get_text(strip=True) if description else '',
        'error': None
    }

def get_bookland_description(url):
    """Pobiera opis z Bookland z obsługą dynamicznego ładowania"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Sprawdź czy treść jest dynamicznie ładowana
        if '<div id="root">' in response.text:  # Typowy znacznik dla aplikacji React
            # Pobierz dane poprzez API (jeśli dostępne)
            product_id = re.search(r'product/(\d+)', url)
            if product_id:
                api_url = f"https://www.bookland.com/api/products/{product_id.group(1)}"
                api_response = requests.get(api_url, headers=headers)
                if api_response.status_code == 200:
                    return api_response.json().get('description', '')
        
        return extract_bookland_data(response.text)
        
    except Exception as e:
        return {'error': f"Błąd pobierania: {str(e)}"}

def get_lubimyczytac_reviews(url):
    """Pobiera opinie z LubimyCzytac"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return ""
            
        soup = bs(response.text, 'html.parser')
        reviews = []
        
        # Nowy selektor dla opinii
        for review in soup.select('div.review-content'):
            text = review.get_text(strip=True)
            if len(text) > 50:  # Filtrujemy krótkie komentarze
                reviews.append(text)
        
        return "\n\n---\n\n".join(reviews) if reviews else ""
        
    except Exception as e:
        st.error(f"Błąd pobierania opinii: {str(e)}")
        return ""

def generate_description(book_data, reviews):
    """Generuje nowy opis przy użyciu OpenAI"""
    try:
        messages = [
            {
                "role": "system",
                "content": """Jesteś profesjonalnym copywriterem specjalizującym się w tworzeniu opisów książek. 
                Twórz angażujące opisy w HTML z wykorzystaniem:<h2>, <p>, <b>, <ul>, <li>. 
                Uwzględnij opinie czytelników."""
            },
            {
                "role": "user",
                "content": f"TYTUŁ: {book_data.get('title', '')}\nOPIS: {book_data.get('description', '')}\nOPINIE: {reviews}"
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Błąd generowania opisu: {str(e)}")
        return ""

def main():
    if bookland_urls_input and lubimyczytac_urls_input:
        bookland_urls = [url.strip() for url in bookland_urls_input.split('\n') if url.strip()]
        lubimyczytac_urls = [url.strip() for url in lubimyczytac_urls_input.split('\n') if url.strip()]
        
        if len(bookland_urls) != len(lubimyczytac_urls):
            st.error("Liczba adresów z obu źródeł musi być taka sama!")
            return
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (bookland_url, lubimyczytac_url) in enumerate(zip(bookland_urls, lubimyczytac_urls)):
            try:
                # Aktualizacja statusu
                status_text.info(f'Przetwarzanie {idx+1}/{len(bookland_urls)}...')
                progress_bar.progress((idx + 1) / len(bookland_urls))
                
                # Pobieranie danych
                book_data = get_bookland_description(bookland_url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {bookland_url}: {book_data['error']}")
                    continue
                    
                reviews = get_lubimyczytac_reviews(lubimyczytac_url)
                
                # Generowanie opisu
                new_description = generate_description(book_data, reviews)
                
                results.append({
                    'URL Bookland': bookland_url,
                    'URL LubimyCzytac': lubimyczytac_url,
                    'Tytuł': book_data.get('title', ''),
                    'Stary opis': book_data.get('description', ''),
                    'Nowy opis': new_description,
                    'Opinie': reviews
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
