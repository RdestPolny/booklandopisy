import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup as bs
import time

# Inicjalizacja Streamlit UI
st.set_page_config(page_title='Generator Opisów Książek', layout='wide')
st.title('📚 Generator Opisów Książek')
st.markdown("""Wprowadź adresy URL z LubimyCzytac, aby automatycznie wygenerować zoptymalizowane opisy książek.""")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input field
st.sidebar.header("🔗 Wprowadź adresy URL")
lubimyczytac_urls_input = st.sidebar.text_area('Wprowadź URL-e z LubimyCzytać (po jednym w linii):')

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
        
        # Pobieranie opinii użytkowników
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

def generate_description(book_data):
    """Generuje nowy opis książki przy użyciu OpenAI"""
    try:
        messages = [
            {
                "role": "system",
                "content": """Jesteś profesjonalnym copywriterem specjalizującym się w tworzeniu opisów książek. 
                Twórz angażujące, optymalizowane pod SEO opisy w HTML, które wykorzystują tagi: <h2>, <p>, <b>, <ul>, <li>.
                Opisy muszą być atrakcyjne dla czytelników, zawierać słowa kluczowe i uwzględniać opinie użytkowników."""
            },
            {
                "role": "user",
                "content": f"OPIS KSIĄŻKI: {book_data.get('description', '')}\nOPINIE CZYTELNIKÓW: {book_data.get('reviews', '')}"
            },
            {
                "role": "user",
                "content": """Stwórz opis książki w HTML, który:

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
<p>„Tata Oli. Tom 3. Z tatą Oli na biwaku” to <b>pełna humoru</b> i <b>przygód</b> opowieść, która z pewnością zachwyci najmłodszych czytelników oraz ich rodziców...</p>
<h3>Nie czekaj! Przeżyj niezapomniane chwile z tatą Oli i jego dziećmi na biwaku, zamów swoją książkę już dziś!</h3>
```"""
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

if __name__ == '__main__':
    main()
