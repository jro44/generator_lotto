import streamlit as st
import pypdf
import re
import random
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import Counter
import pandas as pd

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="LottoMaster 999",
    page_icon="🎱",
    layout="wide"
)

PLIK_PDF = "999los.pdf"


# --- 2. STYLIZACJA (CSS) - KOLORY LOTTO & BIAŁE CZCIONKI ---
def local_css():
    st.markdown("""
    <style>
    /* Tło całej aplikacji - jasny błękit */
    .stApp {
        background-color: #F0F8FF;
        color: #000000;
    }

    /* --- PRZYCISKI (BUTTONS) --- */
    /* Zmieniamy na Granatowe tło + Biały tekst + Żółta ramka */
    div.stButton > button {
        background-color: #191970 !important; /* Ciemny granat */
        color: #FFFFFF !important; /* BIAŁY TEKST */
        border-radius: 10px;
        border: 2px solid #FFD700 !important; /* Złota ramka */
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #0000CD !important; /* Nieco jaśniejszy granat po najechaniu */
        border-color: #FFFFFF !important;
        transform: scale(1.02);
    }

    /* --- ETYKIETY PÓL (LABELS) --- */
    /* "Twoja wiadomość", "Twój email" itp. */
    .stTextArea label, .stTextInput label, .stNumberInput label {
        color: #FFFFFF !important; /* BIAŁY TEKST */
        background-color: #191970 !important; /* Granatowe tło pod napisem */
        padding: 4px 10px !important;
        border-radius: 5px !important;
        font-weight: bold !important;
        width: fit-content !important;
        margin-bottom: 5px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* Tekst wewnątrz pól wpisywania (żeby był ciemny i czytelny na białym tle pola) */
    .stTextArea textarea, .stTextInput input {
        color: #000000 !important;
    }

    /* Nagłówki - Ciemny granat */
    h1, h2, h3 {
        color: #191970 !important;
        font-family: 'Arial', sans-serif;
    }

    /* Wyśrodkowanie tekstów w oknie dialogowym */
    .center-text {
        text-align: center;
        font-size: 18px;
    }

    /* Ramki komunikatów */
    .stSuccess {
        background-color: #E6FFE6;
        border-left: 5px solid #00CC00;
    }

    .stError {
        border-left: 5px solid #FF0000;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #E1EEF6;
        border-right: 1px solid #B0C4DE;
    }
    </style>
    """, unsafe_allow_html=True)


local_css()

# --- 3. INICJALIZACJA STANU ---
if 'moje_losowania' not in st.session_state:
    st.session_state['moje_losowania'] = []

if 'powitanie_ok' not in st.session_state:
    st.session_state['powitanie_ok'] = False

# Czy email został już wysłany w tej sesji?
if 'email_wyslany' not in st.session_state:
    st.session_state['email_wyslany'] = False

# Generowanie zagadki matematycznej (anty-spam)
if 'captcha_a' not in st.session_state:
    st.session_state['captcha_a'] = random.randint(1, 10)
    st.session_state['captcha_b'] = random.randint(1, 10)


# --- 4. OKNO POWITALNE (Wyśrodkowane) ---
@st.dialog("👋 Witaj w LottoMaster!")
def okno_powitalne():
    st.markdown("""
        <div class="center-text">
            <b>Pamiętaj że cyfry są wybierane losowo na podstawie algorytmu aplikacji!!</b><br>
            <br>Aplikacja nie daje gwarancji wygranej! Pozdrawiam A.K!<br>
            <br>Przygotuj się na wielkie emocje.<br>
            Powodzenia!
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("OK, wchodzę do gry!", type="primary", use_container_width=True):
            st.session_state['powitanie_ok'] = True
            st.rerun()


# --- 5. EMAILE ---
def wyslij_email_kontaktowy(tresc_wiadomosci, email_kontaktowy):
    try:
        nadawca = st.secrets["EMAIL_USER"]
        haslo = st.secrets["EMAIL_PASSWORD"]
        odbiorca = "pracapolmar@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = nadawca
        msg['To'] = odbiorca
        msg['Subject'] = "🔔 Wygrana Lotto - Wiadomość od użytkownika"

        body = f"""
        Użytkownik generatora przesłał wiadomość o wygranej!
        --------------------------------------------------
        {tresc_wiadomosci}
        --------------------------------------------------
        Email kontaktowy: {email_kontaktowy}
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(nadawca, haslo)
        text = msg.as_string()
        server.sendmail(nadawca, odbiorca, text)
        server.quit()
        return True
    except Exception:
        return False


# --- 6. PARSER PDF ---
@st.cache_data
def wczytaj_dane_z_pdf(sciezka):
    if not os.path.exists(sciezka): return None
    wszystkie_losowania = []
    try:
        reader = pypdf.PdfReader(sciezka)
        for strona in reader.pages:
            tekst = strona.extract_text() or ""
            raw_tokens = tekst.split()
            clean_tokens = []
            for token in raw_tokens:
                nums = re.findall(r'\d+', token)
                for num_str in nums:
                    temp = num_str
                    while temp:
                        if len(temp) >= 4 and int(temp[:4]) >= 6000:
                            clean_tokens.append(int(temp[:4]));
                            temp = temp[4:]
                        elif len(temp) >= 2 and 1 <= int(temp[:2]) <= 49:
                            clean_tokens.append(int(temp[:2]));
                            temp = temp[2:]
                        elif len(temp) >= 1 and 1 <= int(temp[:1]) <= 9:
                            clean_tokens.append(int(temp[:1]));
                            temp = temp[1:]
                        else:
                            break
            page_ids = [t for t in clean_tokens if t >= 6000]
            if not page_ids: continue
            try:
                first_id_index = clean_tokens.index(page_ids[0])
            except:
                continue
            candidate_nums = clean_tokens[:first_id_index]
            valid_nums = [n for n in candidate_nums if 1 <= n <= 49]
            expected = len(page_ids) * 6
            if len(valid_nums) >= expected:
                final_nums = valid_nums[-expected:]
                for i in range(len(page_ids)):
                    wszystkie_losowania.append({'Liczby': final_nums[i * 6: (i + 1) * 6]})
    except:
        return None
    return wszystkie_losowania


# --- 7. GENERATOR ---
def generuj_kupon(dane):
    ostatnie_3 = dane[:3]
    zakazane = set()
    for los in ostatnie_3: zakazane.update(los['Liczby'])
    wszystkie_flat = [n for los in dane for n in los['Liczby']]
    licznik = Counter(wszystkie_flat)

    if random.random() < 0.20:
        typ = "❄️ ZIMNY"
        pula = [n for n in range(1, 50) if n not in zakazane]
        pula_sorted = sorted(pula, key=lambda x: licznik.get(x, 0))
        kupon = set(random.sample(pula_sorted[:15], 6))
    else:
        typ = "🔥 GORĄCY"
        populacja = list(licznik.keys())
        wagi = list(licznik.values())
        kupon = set()
        while len(kupon) < 6:
            kupon.add(random.choices(populacja, weights=wagi, k=1)[0])
    return sorted(list(kupon)), typ


# --- 8. PLIK TXT ---
def przygotuj_plik_txt(historia):
    tekst = "--- TWOJE WYNIKI LOTTOMASTER 999 ---\n"
    tekst += f"Data pobrania: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    tekst += "-------------------------------------\n\n"
    for i, wpis in enumerate(historia):
        tekst += f"Losowanie #{i + 1} | Godz: {wpis['Godzina']}\n"
        tekst += f"Strategia: {wpis['Strategia']}\n"
        tekst += f"LICZBY: {wpis['Liczby']}\n"
        tekst += "-------------------------------------\n"
    return tekst


# --- 9. GŁÓWNA APLIKACJA ---
def main():
    if not st.session_state['powitanie_ok']:
        okno_powitalne()

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2550/2550269.png", width=100)
        st.markdown("<h2 style='text-align: center; color: #000;'>LottoMaster 999</h2>", unsafe_allow_html=True)
        st.metric("Twoje losowania w sesji", len(st.session_state['moje_losowania']))
        st.info("System oparty na analizie 999 ostatnich losowań.")

    st.markdown("<h1 style='text-align: center; color: #191970;'>🍀 Generator Szczęśliwych Liczb</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Analiza statystyczna + Teoria Chaosu</p>", unsafe_allow_html=True)

    if not os.path.exists(PLIK_PDF):
        st.error("Błąd: Brak pliku PDF!")
        return
    dane = wczytaj_dane_z_pdf(PLIK_PDF)
    if not dane:
        st.error("Błąd parsowania PDF.")
        return

    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("GENERUJ ZESTAW 🎲", type="primary", use_container_width=True):
            with st.spinner("Maszyna losująca w ruchu..."):
                liczby, strategia = generuj_kupon(dane)

                teraz = datetime.now()
                nowy_wpis = {
                    "Godzina": teraz.strftime("%H:%M:%S"),
                    "Strategia": strategia,
                    "Liczby": str(liczby)
                }
                st.session_state['moje_losowania'].insert(0, nowy_wpis)

                st.success(f"Twój zestaw ({strategia}):")
                st.markdown(f"<h2 style='text-align: center; color: #000;'>{' - '.join(map(str, liczby))}</h2>",
                            unsafe_allow_html=True)
                st.balloons()
                st.markdown(
                    "<div style='text-align: center; background-color: #FFD700; padding: 10px; border-radius: 5px; color: black;'><b>🏆 Autor programu życzy Wysokich wygranych! 🏆</b></div>",
                    unsafe_allow_html=True)

    with col2:
        st.warning("💡 **Strategia:**\nSystem automatycznie dobiera liczby 'Gorące' (częste) lub 'Zimne' (zaległe).")

    # --- 10. KONTAKT Z ANTY-SPAMEM I BLOKADĄ ---
    st.divider()
    st.markdown("<h3 style='text-align: center;'>📬 Pochwal się wygraną!</h3>", unsafe_allow_html=True)
    st.write("Wygrałeś? Daj nam znać!")

    # LOGIKA BLOKADY
    if st.session_state['email_wyslany']:
        st.success("✅ Dziękujemy! Twoja wiadomość została już wysłana w tej sesji.")
        st.info("Aby wysłać kolejną wiadomość, musisz odświeżyć stronę lub wejść ponownie.")
    else:
        with st.form("formularz_kontaktowy"):
            wiadomosc = st.text_area("Twoja wiadomość:", placeholder="Wygrałem...")
            email_gracza = st.text_input("Twój email (opcjonalnie):")

            st.markdown("---")
            st.write("**Zabezpieczenie przed botami:**")

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                a = st.session_state['captcha_a']
                b = st.session_state['captcha_b']
                # Pytanie matematyczne też będzie miało białą etykietę dzięki naszym stylom
                st.markdown(f"#### Ile to jest **{a} + {b}**?")
            with col_c2:
                odpowiedz_uzytkownika = st.number_input("Wpisz wynik:", min_value=0, max_value=100, step=1)

            wyslij_btn = st.form_submit_button("Wyślij email")

            if wyslij_btn:
                poprawny_wynik = st.session_state['captcha_a'] + st.session_state['captcha_b']

                if odpowiedz_uzytkownika != poprawny_wynik:
                    # BŁĄD -> Nowe liczby -> Przeładowanie
                    st.session_state['captcha_a'] = random.randint(1, 10)
                    st.session_state['captcha_b'] = random.randint(1, 10)
                    st.error(f"❌ Błąd! Wynik jest niepoprawny. Równanie zostało zmienione dla bezpieczeństwa.")
                    time.sleep(2)
                    st.rerun()

                elif not wiadomosc:
                    st.warning("⚠️ Wpisz treść wiadomości.")

                else:
                    # SUKCES -> Wysyłka -> Blokada
                    with st.spinner("Wysyłanie wiadomości..."):
                        if wyslij_email_kontaktowy(wiadomosc, email_gracza):
                            st.session_state['email_wyslany'] = True
                            st.rerun()
                        else:
                            st.error("❌ Błąd wysyłania (sprawdź konfigurację serwera).")

    # --- 11. HISTORIA I ZAPIS ---
    st.divider()
    st.subheader("📜 Twoja prywatna historia")

    historia_do_pokazania = []
    if st.session_state['moje_losowania']:
        historia_do_pokazania = st.session_state['moje_losowania'][:20]

        plik_txt = przygotuj_plik_txt(historia_do_pokazania)

        col_down1, col_down2 = st.columns([1, 4])
        with col_down1:
            st.download_button(
                label="💾 Zapisz wyniki (TXT)",
                data=plik_txt,
                file_name="GenWynLotto.txt",
                mime="text/plain"
            )

        df_historia = pd.DataFrame(historia_do_pokazania)
        st.dataframe(df_historia, use_container_width=True, hide_index=True)
    else:
        st.write("Jeszcze nic nie wylosowałeś.")


if __name__ == "__main__":
    main()