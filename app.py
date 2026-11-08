#
from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

BASE_URL = "https://mofis.hermes-service.com"
MAIN_URL = "https://mofis.hermes-service.com/lc-list/tm4GwqCaAFlyVmPFlUCs"

def pobierz_linki_i_nazwy(session):
    try:
        response = session.get(MAIN_URL, timeout=10)
        if response.status_code != 200:
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
    except Exception:
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
                wiersze = soup.find_all('tr')
                
                for wiersz in wiersze:
                    tds = wiersz.find_all('td')
                    if len(tds) >= 3:
                        tura_tekst = tds[1].get_text(strip=True)
                        
                        if szukana_tura in tura_tekst:
                            status = "NIEZNANY"
                            czas = tds[2].get_text(strip=True)
                            html_wiersza = str(wiersz).lower()
                            
                            if 'misc-red' in html_wiersza:
                                status = "NIE GOTOWA 🔴"
                            elif 'misc-green' in html_wiersza:
                                status = "GOTOWA 🟢"

                            baza_danych.append({
                                'depot': nazwa_depotu,
                                'tura': tura_tekst,
                                'czas': czas,
                                'status': status
                            })
        except Exception:
            continue
    return baza_danych

HTML_TEMPLATE = """
<!doctype html>
<html lang="pl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Hermes - Tury</title>
    <style>
        body { font-family: Arial, sans-serif; background: #eef2f7; margin: 0; padding: 15px; color: #333; }
        .container { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #0056b3; margin-bottom: 20px; }
        form { display: flex; gap: 8px; margin-bottom: 20px; }
        input[type="text"] { flex: 1; padding: 14px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; outline: none; }
        button { padding: 14px 20px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        button:active { background: #004085; }
        .card { background: #fff; border-left: 6px solid #007bff; padding: 15px; margin-bottom: 12px; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
        .card.gotowa { border-left-color: #28a745; background: #f8fff9; }
        .card.niegotowa { border-left-color: #dc3545; background: #fff8f8; }
        .info { margin: 6px 0; font-size: 16px; }
        .error { color: #dc3545; text-align: center; font-weight: bold; font-size: 16px; }
        .loading { text-align: center; color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📦 Hermes Tury</h2>
        <form method="POST" onsubmit="showLoading()">
            <input type="text" name="tura" placeholder="Wpisz numer tury..." value="{{ szukana }}" required autofocus>
            <button type="submit">Szukaj</button>
        </form>

        <div id="loading" class="loading" style="display:none;">🔄 Pobieranie i sprawdzanie depotów...</div>

        {% if wyniki is not none %}
            <h3>Wyniki dla: {{ szukana }}</h3>
            {% if wyniki %}
                {% for w in wyniki %}
                    <div class="card {% if 'GOTOWA 🟢' in w.status %}gotowa{% else %}niegotowa{% endif %}">
                        <div class="info"><strong>🏢 Miejsce:</strong> {{ w.depot }}</div>
                        <div class="info"><strong>🔢 Tura:</strong> {{ w.tura }}</div>
                        <div class="info"><strong>📊 Status:</strong> {{ w.status }}</div>
                        <div class="info"><strong>⏰ Godzina:</strong> {{ w.czas }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <p class="error">❌ Nie znaleziono tury w żadnym depocie.</p>
            {% endif %}
        {% endif %}
    </div>

    <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }
    </script>
</body>
    <div style="text-align: center; margin-top: 25px; color: #777; font-size: 13px;">
        Made in Kalatar 🛠️
    </div>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    wyniki = None
    szukana = ""
    if request.method == 'POST':
        szukana = request.form.get('tura', '').strip()
        if szukana:
            session = requests.Session()
            depoty_info = pobierz_linki_i_nazwy(session)
            if depoty_info:
                wyniki = przeszukaj_depoty(session, depoty_info, szukana)
    return render_template_string(HTML_TEMPLATE, wyniki=wyniki, szukana=szukana)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
