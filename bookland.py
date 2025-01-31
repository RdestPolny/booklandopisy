import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup as bs
import time

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Książek')

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Input field
lubimyczytac_urls_input = st.text_area('Wprowadź adresy URL z LubimyCzytac (po jednym w linii):')

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
        for review in soup.select('div.review-content'):
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
                "content": f"OPIS KSIĄŻKI: {book_data.get('description', '')}\nOPINIE CZYTELNIKÓW: {book_data.get('reviews', '')}"
            },
            {
                "role": "user",
                "content": """Stwórz optymalizowany pod SEO opis książki w HTML. Opis powinien:

1. Wykorzystywać tagi HTML (nie Markdown):
   - <h2> dla podtytułów sekcji
   - <p> dla paragrafów
   - <b> dla wyróżnienia kluczowych fraz
   - <ul>/<li> dla list

2. Zawierać następujące sekcje:
<h2>{Unikalne, kreatywne hasło związane z treścią książki}</h2>
   <p>{Wprowadzenie prezentujące główne zalety i unikalne cechy książki}</p>
   <p>{Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi}</p>
   <p>{Wartości i korzyści dla czytelnika}</p>
   <p>{Określenie grupy docelowej i rekomendacje}</p>
   <p>{Podsumowanie opinii czytelników z nawiązaniem do konkretów}</p>
   <h3>Przekonujący call to action</h3>

3. Wykorzystywać słownictwo odpowiednie dla gatunku książki i dostosowane do odbiorców. Nie zwracaj żadnych dodatkowych komentarzy tylko sam opis"""
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
    if lubimyczytac_urls_input:
        lubimyczytac_urls = [url.strip() for url in lubimyczytac_urls_input.split('\n') if url.strip()]
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(lubimyczytac_urls):
            try:
                # Aktualizacja statusu
                status_text.info(f'Przetwarzanie {idx+1}/{len(lubimyczytac_urls)}...')
                progress_bar.progress((idx + 1) / len(lubimyczytac_urls))
                
                # Pobieranie danych
                book_data = get_lubimyczytac_data(url)
                if book_data.get('error'):
                    st.error(f"Błąd dla {url}: {book_data['error']}")
                    continue
                    
                # Generowanie opisu
                new_description = generate_description(book_data)
                
                results.append({
                    'URL': url,
                    'Stary opis': book_data.get('description', ''),
                    'Nowy opis': new_description,
                    'Opinie': book_data.get('reviews', '')
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
