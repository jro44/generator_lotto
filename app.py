import streamlit as st
import pypdf
import re
import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import Counter
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="LottoMaster 999",
    page_icon="🍀",
    layout="wide"
)

PLIK_PDF = "999los.pdf"

# --- INICJALIZACJA STANU (Prywatna pamięć) ---
if 'moje_losowania' not in st.session_state:
    st.session_state['moje_losowania'] = []

if 'powitanie_ok' not in st.session_state:
    st.session_state['powitanie_ok'] = False


# --- FUNKCJA POWITALNA (POP-UP) ---
@st.dialog("👋 Witaj w LottoMaster!")
def okno_powitalne():
    st.write("Autor programu wita i życzy wysokich wygranych!")
    st.write("Powodzenia!")
    if st.button("OK, wchodzę do gry!", type="primary"):
        st.session_state['powitanie_ok'] = True
        st.rerun()


# --- FUNKCJE POMOCNICZE (Email) ---
def wyslij_email_kontaktowy(tresc_wiadomosci, email_kontaktowy):
    """Wysyła email używając bezpiecznych zmiennych środowiskowych (Secrets)"""
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
        Treść wiadomości:
        {tresc_wiadomosci}
        --------------------------------------------------

        Email kontaktowy podany przez użytkownika: {email_kontaktowy}
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(nadawca, haslo)
        text = msg.as_string()
        server.sendmail(nadawca, odbiorca, text)
        server.quit()
        return True
    except Exception as e:
        return False


# --- FUNKCJA PARSUJĄCA PDF ---
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


# --- LOGIKA GENERATORA ---
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


# --- GŁÓWNA APLIKACJA ---
def main():
    # 1. Sprawdzenie czy pokazać powitanie (To musi być na początku)
    if not st.session_state['powitanie_ok']:
        okno_powitalne()

    # 2. Reszta aplikacji (ładuje się w tle)
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2550/2550269.png", width=100)
        st.title("LottoMaster 999")
        ile_prywatnie = len(st.session_state['moje_losowania'])
        st.metric("Twoje losowania w tej sesji", ile_prywatnie)

    st.title("🍀 Generator Szczęśliwych Liczb")

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
        if st.button("GENERUJ ZESTAW", type="primary", use_container_width=True):
            with st.spinner("Analiza..."):
                liczby, strategia = generuj_kupon(dane)

                teraz = datetime.now()
                nowy_wpis = {
                    "Godzina": teraz.strftime("%H:%M:%S"),
                    "Strategia": strategia,
                    "Liczby": str(liczby)
                }
                st.session_state['moje_losowania'].insert(0, nowy_wpis)

                st.success(f"Twój zestaw ({strategia}):")
                st.markdown(f"## 🎲 {str(liczby)}")
                st.balloons()
                st.success("🏆 Autor programu życzy Wysokich wygranych!")

    with col2:
        st.info("💡 **Wskazówka:** Każde losowanie jest unikalne i zapisuje się tylko w Twojej historii poniżej.")

    # --- KONTAKT ---
    st.divider()
    st.subheader("📬 Pochwal się wygraną!")
    st.write("Jeżeli wygrałeś za pomocą programu i zechciałbyś o tym poinformować - napisz do nas!")

    with st.form("formularz_kontaktowy"):
        wiadomosc = st.text_area("Twoja wiadomość:", placeholder="Trafiłem czwórkę! Dzięki!")
        email_gracza = st.text_input("Twój email (opcjonalnie):", placeholder="jan@kowalski.pl")

        wyslij_btn = st.form_submit_button("Wyślij email")

        if wyslij_btn:
            if not wiadomosc:
                st.warning("Napisz chociaż kilka słów!")
            else:
                with st.spinner("Wysyłanie wiadomości..."):
                    if wyslij_email_kontaktowy(wiadomosc, email_gracza):
                        st.success("Wiadomość została wysłana! Dziękujemy!")
                    else:
                        st.error("Nie udało się wysłać wiadomości.")

    # --- HISTORIA ---
    st.divider()
    st.subheader("📜 Twoja prywatna historia (ostatnie 20 losowań)")

    if st.session_state['moje_losowania']:
        historia_do_pokazania = st.session_state['moje_losowania'][:20]
        df_historia = pd.DataFrame(historia_do_pokazania)
        st.dataframe(df_historia, use_container_width=True, hide_index=True)
    else:
        st.write("Jeszcze nic nie wylosowałeś.")


if __name__ == "__main__":
    main()