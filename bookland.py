import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from openai import OpenAI

# Inicjalizacja Streamlit UI
st.title('Generator Opisów Książek')

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Pole tekstowe do wklejania adresów URL (po jednym w linii)
urls_input = st.text_area('Wprowadź adresy URL (po jednym w linii):')

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

def get_nowaera_data(url):
    """Pobiera dane ze strony sklep.nowaera.pl:
       - Tytuł (H1)
       - Stary opis (wszystkie <p> i <li> wewnątrz div#descriptionArea)
       - Dodatkowe informacje (teksty zagnieżdżonych divów w div.extra-info__frame)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = bs(response.text, 'html.parser')
        
        # Pobieramy tytuł książki z H1
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Pobieramy stary opis z div o id "descriptionArea"
        description_div = soup.find('div', id='descriptionArea')
        description_elements = []
        if description_div:
            # Szukamy wszystkich <p> oraz <li>
            for tag in description_div.find_all(['p', 'li']):
                text = tag.get_text(strip=True)
                if text:
                    description_elements.append(text)
        description = "\n\n".join(description_elements)
        
        # Pobieramy dodatkowe informacje z div o klasie "extra-info__frame"
        extra_info_div = soup.find('div', class_='extra-info__frame')
        extra_info_elements = []
        if extra_info_div:
            # Pobieramy teksty zagnieżdżonych divów
            for tag in extra_info_div.find_all('div'):
                text = tag.get_text(strip=True)
                if text:
                    extra_info_elements.append(text)
        extra_info = "\n\n".join(extra_info_elements)
        
        return {
            'title': title,
            'description': description,
            'extra_info': extra_info,
            'error': None
        }
        
    except Exception as e:
        return {
            'title': '',
            'description': '',
            'extra_info': '',
            'error': f"Błąd pobierania: {str(e)}"
        }

def generate_description(book_data):
    """Generuje nowy opis na podstawie danych pobranych z LubimyCzytac"""
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
                    "1. Zaczyna się od mocnego nagłówka <h2> z kreatywnym hasłem nawiązującym do treści książki.\n"
                    "2. Zawiera sekcje:\n"
                    "   - <p>Wprowadzenie z głównymi zaletami książki</p>\n"
                    "   - <p>Szczegółowy opis fabuły/treści z <b>wyróżnionymi</b> słowami kluczowymi</p>\n"
                    "   - <p>Wartości i korzyści dla czytelnika</p>\n"
                    "   - <p>Podsumowanie opinii czytelników z konkretnymi przykładami</p>\n"
                    "   - <h3>Przekonujący call to action</h3>\n\n"
                    "3. Wykorzystuje opinie czytelników, aby:\n"
                    "   - Podkreślić najczęściej wymieniane zalety książki\n"
                    "   - Wzmocnić wiarygodność opisu\n"
                    "   - Dodać emocje i autentyczność\n\n"
                    "4. Formatowanie:\n"
                    "   - Używaj tagów HTML: <h2>, <p>, <b>, <h3>\n"
                    "   - Wyróżniaj kluczowe frazy za pomocą <b>\n"
                    "   - Nie używaj znaczników Markdown, tylko HTML\n"
                    "   - Nie dodawaj komentarzy ani wyjaśnień, tylko sam opis\n\n"
                    "5. Styl:\n"
                    "   - Opis ma być angażujący, ale profesjonalny\n"
                    "   - Używaj słownictwa dostosowanego do gatunku książki\n"
                    "   - Unikaj powtórzeń\n"
                    "   - Zachowaj spójność tonu\n\n"
                    "6. Przykład formatu:\n"
                    "```html\n"
                    "<h2>Przygoda na świeżym powietrzu z tatą Oli czeka na każdą rodzinę!</h2>\n"
                    "<p>„Tata Oli. Tom 3. Z tatą Oli na biwaku” to <b>pełna humoru</b> i <b>przygód</b> opowieść, która z pewnością zachwyci najmłodszych czytelników oraz ich rodziców. "
                    "Ta książka łączy w sobie <b>fantastyczne ilustracje</b> z doskonałym tekstem, który bawi do łez, a jednocześnie skłania do refleksji nad <b>relacjami rodzinnymi</b>.</p>\n"
                    "<p>W tej części tata Oli postanawia <b>oderwać dzieci</b> od ekranów i zorganizować im prawdziwy <b>biwak</b>. "
                    "Wspólnie stają przed nie lada wyzwaniem: muszą <b>rozpalić ognisko</b>, <b>łowić ryby</b> i cieszyć się <b>urokami natury</b>. "
                    "Jednak zamiast sielanki, napotykają na wiele zabawnych przeszkód, co prowadzi do sytuacji pełnych <b>śmiechu</b> i <b>niespodzianek</b>. "
                    "Tata Oli, z typową dla siebie pomysłowością, staje przed wyzwaniami, które pokazują, że nie zawsze wszystko idzie zgodnie z planem, a <b>życie na łonie natury</b> może być pełne <b>przygód</b>.</p>\n"
                    "<p>Książka ta wartościowo rozwija wyobraźnię dzieci, pokazując, że <b>spędzanie czasu z rodziną</b> na świeżym powietrzu może być nie tylko zabawne, ale również <b>edukacyjne</b>. "
                    "Dzięki humorystycznym sytuacjom z udziałem taty Oli, dzieci uczą się, że dorośli także mają swoje słabości, co czyni tę lekturę <b>uniwersalną</b>.</p>\n"
                    "<p>„Z tatą Oli na biwaku” to idealna propozycja dla <b>dzieci w wieku przedszkolnym i wczesnoszkolnym</b>, a także dla rodziców, którzy pragną spędzić czas z dziećmi w <b>zabawny</b> i <b>interaktywny</b> sposób. "
                    "To książka, która rozbawi i dostarczy wielu emocji.</p>\n"
                    "<p>Czytelnicy zachwycają się nie tylko <b>lekkością</b> i <b>humorem</b> tekstu, ale także <b>ilustracjami</b>, które wzbogacają opowieść. "
                    "Wiele osób zauważa, że tata Oli staje się wzorem dla dzieci, pokazując, iż <b>rodzicielstwo</b> to sztuka kompromisu i <b>radości</b>, nawet w trudnych sytuacjach.</p>\n"
                    "<h3>Nie czekaj! Przeżyj niezapomniane chwile z tatą Oli i jego dziećmi na biwaku, zamów swoją książkę już dziś!</h3>\n"
                    "```"
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

def generate_description_nowaera(book_data):
    """Generuje nowy opis na podstawie danych pobranych ze sklep.nowaera.pl"""
    try:
        title = book_data.get('title', '')
        description = book_data.get('description', '')
        extra_info = book_data.get('extra_info', '')
        
        messages = [
            {
                "role": "system",
                "content": "Jesteś autorem opisów w księgarni internetowej Bookland."
            },
            {
                "role": "user",
                "content": f"Tytuł książki: {title}\nInformacje: {description}\nDodatkowe informacje: {extra_info}"
            },
            {
                "role": "user",
                "content": f"""Jako autor opisów w księgarni internetowej Bookland, twoim zdaniem jest przygotowanie rzetelnego, zoptymalizowanego opisu produktu o tytule "{title}". Oto informacje na których powinieneś bazować "Informacje pobrane z descriptionArea oraz extra-info__frame". Stwórz angażujący opis w HTML z wykorzystaniem:<h2>, <p>, <b>, <ul>, <li>. Opis powinien:

1. Zaczyna się od nagłówka <h2> z kreatywnym hasłem nawiązującym do przedmiotu nauki, z którym związany jest podręcznik, oraz jego targetem np. dla uczniów 2 klasy szkoły podstawowej.
2. Zawiera sekcje:
   - <p>Wprowadzenie z opisem tego, czym jest dany podręcznik / ćwiczenie / zeszyt ćwiczeń itd. (w zależności od tego, czym jest dany tytuł), informacje na temat jego zawartości, docelowego targetu i tym, co uznasz za stosowne do opisania w kluczowym pierwszym akapicie.</p>
   - <p>Zalety / szczególne cechy warte podkreślenia, z <b>wyróżnionymi</b> słowami kluczowymi</p>
   - <p>Wartości i korzyści dla ucznia</p>
   - <p>Podsumowanie</p>
   - <h3>Przekonujący call to action</h3>

3. Wykorzystuje pobrane informacje, aby:
   - Podkreślić najczęściej wymieniane zalety książki
   - Wzmocnić wiarygodność opisu

4. Formatowanie:
   - Używaj tagów HTML: <h2>, <p>, <b>, <h3>
   - Wyróżniaj kluczowe frazy lub informacje godne wzmocnienia za pomocą <b>
   - Nie używaj znaczników Markdown, tylko HTML
   - Nie dodawaj komentarzy ani wyjaśnień, tylko sam opis

5. Styl:
   - Opis ma być angażujący, ale profesjonalny
   - Używaj słownictwa dostosowanego do odbiorcy
   - Unikaj powtórzeń
   - Zachowaj spójność tonu

6. Przykład formatu:
```html
<h2>zawartość</h2>
<p>zawartość</p>
<p>zawartość</p>
<p>zawartość</p>
<h3>CTA</h3>
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

def main():
    # Użytkownik wkleja adresy w pole tekstowe, a przetwarzanie odpala się dopiero po naciśnięciu przycisku "Uruchom"
    if st.button("Uruchom"):
        if urls_input:
            urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, url in enumerate(urls):
                status_text.info(f'Przetwarzanie {idx+1}/{len(urls)}...')
                progress_bar.progress((idx + 1) / len(urls))
                
                # Wybór sposobu pobierania danych w zależności od domeny
                if "lubimyczytac" in url:
                    book_data = get_lubimyczytac_data(url)
                    if book_data.get('error'):
                        st.error(f"Błąd dla {url}: {book_data['error']}")
                        continue
                    new_description = generate_description(book_data)
                    results.append({
                        'URL': url,
                        'Stary opis': book_data.get('description', ''),
                        'Opinie': book_data.get('reviews', ''),
                        'Nowy opis': new_description
                    })
                    
                elif "sklep.nowaera.pl" in url:
                    book_data = get_nowaera_data(url)
                    if book_data.get('error'):
                        st.error(f"Błąd dla {url}: {book_data['error']}")
                        continue
                    new_description = generate_description_nowaera(book_data)
                    results.append({
                        'URL': url,
                        'Tytuł': book_data.get('title', ''),
                        'Stary opis': book_data.get('description', ''),
                        'Dodatkowe informacje': book_data.get('extra_info', ''),
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

if __name__ == '__main__':
    main()
