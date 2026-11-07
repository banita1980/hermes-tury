import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://mofis.hermes-service.com"
MAIN_URL = "https://mofis.hermes-service.com/lc-list/tm4GwqCaAFlyVmPFlUCs"

def pobierz_linki_i_nazwy(session):
    try:
        response = session.get(MAIN_URL, timeout=10)
        if response.status_code != 200:
            print(f"Błąd pobierania strony głównej. Kod: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        depoty_info = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/lc/' in href and not href.endswith('/lc-list/tm4GwqCaAFlyVmPFlUCs'):
                pelny_link = urljoin(BASE_URL, href)
                nazwa_depotu = a_tag.get_text(strip=True)
                if not nazwa_depotu:
                    nazwa_depotu = href.split('/')[-1]

                if not any(d['url'] == pelny_link for d in depoty_info):
                    depoty_info.append({'url': pelny_link, 'nazwa': nazwa_depotu})

        return depoty_info
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania linków: {e}")
        return []

def przeszukaj_depoty(session, depoty_info, szukana_tura):
    baza_danych = []
    
    for depot in depoty_info:
        url = depot['url']
        nazwa_depotu = depot['nazwa']
        
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Szukamy WYŁĄCZNIE wierszy tabeli (tr), gdzie każda tura ma swój osobny wiersz
                wiersze = soup.find_all('tr')
                
                for wiersz in wiersze:
                    tekst_wiersza = wiersz.get_text()
                    
                    if szukana_tura in tekst_wiersza:
                        status = "NIEZNANY"
                        html_wiersza = str(wiersz).lower()
                        
                        # Sprawdzamy najpierw CZERWONY, bo jeśli jest czerwony, nie może być zielony
                        if 'misc-red' in html_wiersza:
                            status = "NIE GOTOWA (Czerwone okienko) 🔴"
                        elif 'misc-green' in html_wiersza:
                            status = "GOTOWA (Zielone okienko) 🟢"

                        baza_danych.append({
                            'depot': nazwa_depotu,
                            'tekst': tekst_wiersza.strip().replace('\n', ' '),
                            'status': status
                        })
                        
        except Exception as e:
            print(f"Błąd przy odczycie {nazwa_depotu}: {e}")
            
    return baza_danych

if __name__ == "__main__":
    session = requests.Session()
    print("=== PROGRAM DO SPRAWDZANIA TUR HERMES GOTOWY ===")

    while True:
        szukana_tura = input("\n[?] Wpisz numer tury do wyszukania (lub 'exit'): ").strip()
        
        if szukana_tura.lower() == 'exit':
            break
        
        if not szukana_tura:
            continue

        print("\n🔄 Pobieranie aktualnych list i skanowanie depotów...")
        depoty_info = pobierz_linki_i_nazwy(session)
        
        if depoty_info:
            wyniki = przeszukaj_depoty(session, depoty_info, szukana_tura)

            if wyniki:
                print(f"\n--- Wyniki dla tury: {szukana_tura} ---")
                
                unikalne_wyniki = {}
                for w in wyniki:
                    if w['depot'] not in unikalne_wyniki:
                        unikalne_wyniki[w['depot']] = w

                for depot_nazwa, w in unikalne_wyniki.items():
                    print(f"🏢 Depot: {depot_nazwa}")
                    print(f"📊 Status: {w['status']}")
                    print(f"📄 Fragment: {w['tekst'][:100]}...")
                    print("-" * 40)
            else:
                print(f"❌ Brak wyników dla tury '{szukana_tura}' w najnowszych danych.")
        else:
            print("❌ Nie udało się pobrać linków ze strony głównej.")
