import streamlit as st
import pypdf
import re
import random
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import Counter

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="LottoMaster 999",
    page_icon="🍀",
    layout="wide"
)

PLIK_PDF = "999los.pdf"
PLIK_HISTORII = "historia_losowan.csv"


# --- FUNKCJE POMOCNICZE (Baza danych i Email) ---

def wczytaj_historie():
    if os.path.exists(PLIK_HISTORII):
        return pd.read_csv(PLIK_HISTORII)
    else:
        return pd.DataFrame(columns=["Data", "Godzina", "Strategia", "Wylosowane Liczby"])


def zapisz_wynik(liczby, strategia):
    df = wczytaj_historie()
    teraz = datetime.now()
    nowy_wiersz = {
        "Data": teraz.strftime("%Y-%m-%d"),
        "Godzina": teraz.strftime("%H:%M:%S"),
        "Strategia": strategia.split(" ")[1],
        "Wylosowane Liczby": str(liczby)
    }
    nowy_df = pd.DataFrame([nowy_wiersz])
    df = pd.concat([df, nowy_df], ignore_index=True)
    df.to_csv(PLIK_HISTORII, index=False)
    return df


def wyslij_email_kontaktowy(tresc_wiadomosci, email_kontaktowy):
    """Wysyła email używając bezpiecznych zmiennych środowiskowych (Secrets)"""
    # Pobieramy dane logowania z ukrytych ustawień Streamlit (Secrets)
    nadawca = st.secrets["EMAIL_USER"]
    haslo = st.secrets["EMAIL_PASSWORD"]
    odbiorca = "pracapolmar@gmail.com"

    msg = MIMEMultipart()
    msg['From'] = nadawca
    msg['To'] = odbiorca
    msg['Subject'] = "🔔 Wygrana Lotto - Wiadomość od użytkownika"

    # Treść maila
    body = f"""
    Użytkownik generatora przesłał wiadomość o wygranej!

    --------------------------------------------------
    Treść wiadomości:
    {tresc_wiadomosci}
    --------------------------------------------------

    Email kontaktowy podany przez użytkownika: {email_kontaktowy}
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Łączenie z serwerem Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(nadawca, haslo)
        text = msg.as_string()
        server.sendmail(nadawca, odbiorca, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Błąd wysyłania: {e}")
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
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2550/2550269.png", width=100)
        st.title("LottoMaster 999")
        historia = wczytaj_historie()
        st.metric("Wygenerowano", len(historia))

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
                zapisz_wynik(liczby, strategia)
                st.success(f"Twój zestaw ({strategia}):")
                st.markdown(f"## 🎲 {str(liczby)}")
                st.balloons()

                # --- NOWOŚĆ: RAMKA Z ŻYCZENIAMI ---
                st.success("🏆 Autor programu życzy Wysokich wygranych!")

    with col2:
        st.info("💡 **Wskazówka:** Strategia ZIMNA omija ostatnie wyniki.")

    # --- NOWOŚĆ: SEKCJA KONTAKTOWA ---
    st.divider()
    st.subheader("📬 Pochwal się wygraną!")
    st.write("Jeżeli wygrałeś za pomocą programu i zechciałbyś o tym poinformować - napisz do nas!")

    with st.form("formularz_kontaktowy"):
        # Pola formularza
        wiadomosc = st.text_area("Twoja wiadomość:", placeholder="Wygrałem trójkę w systemie gorącym...")
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
                        st.error("Nie udało się wysłać wiadomości. Spróbuj później.")

    # Tabela historii
    st.divider()
    st.subheader("📜 Ostatnie losowania")
    historia_aktualna = wczytaj_historie()
    if not historia_aktualna.empty:
        st.dataframe(historia_aktualna.tail(10).iloc[::-1], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()