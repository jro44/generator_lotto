import streamlit as st
import pypdf
import re
import random
import os
import pandas as pd
from datetime import datetime
from collections import Counter

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="LottoMaster 999",
    page_icon="🍀",
    layout="wide"  # Szeroki układ strony, jak na blogu
)

PLIK_PDF = "999los.pdf"
PLIK_HISTORII = "historia_losowan.csv"


# --- FUNKCJE POMOCNICZE (Baza danych w pliku CSV) ---

def wczytaj_historie():
    """Wczytuje historię losowań z pliku CSV."""
    if os.path.exists(PLIK_HISTORII):
        return pd.read_csv(PLIK_HISTORII)
    else:
        # Tworzymy pustą tabelę, jeśli plik nie istnieje
        return pd.DataFrame(columns=["Data", "Godzina", "Strategia", "Wylosowane Liczby"])


def zapisz_wynik(liczby, strategia):
    """Dopisuje nowy wynik do pliku CSV."""
    df = wczytaj_historie()

    teraz = datetime.now()
    nowy_wiersz = {
        "Data": teraz.strftime("%Y-%m-%d"),
        "Godzina": teraz.strftime("%H:%M:%S"),
        "Strategia": strategia.split(" ")[1],  # Bierze tylko słowo np. GORĄCY
        "Wylosowane Liczby": str(liczby)
    }

    # Dodajemy nowy wiersz (używamy concat zamiast append)
    nowy_df = pd.DataFrame([nowy_wiersz])
    df = pd.concat([df, nowy_df], ignore_index=True)

    # Zapisujemy do pliku
    df.to_csv(PLIK_HISTORII, index=False)
    return df


# --- FUNKCJA PARSUJĄCA PDF (Twoja sprawdzona logika) ---
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


# --- UKŁAD STRONY (BLOG) ---
def main():
    # 1. SIDEBAR (Panel boczny z informacjami)
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2550/2550269.png", width=100)
        st.title("LottoMaster 999")
        st.write("Profesjonalny analizator oparty na 999 ostatnich losowaniach.")

        # Licznik (pobieramy z długości historii)
        historia = wczytaj_historie()
        liczba_uzyc = len(historia)
        st.metric(label="Wygenerowanych Kuponów", value=liczba_uzyc)

        st.info("Algorytm aktualizowany: 2026")

    # 2. GŁÓWNA TREŚĆ
    st.title("🍀 Generator Szczęśliwych Liczb")
    st.markdown("""
    Witaj na blogu LottoMaster! Nasz algorytm to hybryda matematyki i teorii chaosu.
    Nie strzelaj na oślep – zaufaj statystyce.

    **Jak to działa?**
    * Analizujemy PDF z 999 losowaniami.
    * W 80% przypadków stosujemy **Strategię Gorącą** (liczby najczęstsze).
    * W 20% przypadków stosujemy **Strategię Zimną** (szukamy zaległych liczb).
    """)

    # Sprawdzenie bazy
    if not os.path.exists(PLIK_PDF):
        st.error("Błąd: Brak pliku bazy danych!")
        return

    dane = wczytaj_dane_z_pdf(PLIK_PDF)
    if not dane:
        st.error("Błąd parsowania PDF.")
        return

    # Sekcja Generatora
    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🤖 Uruchom System")
        if st.button("GENERUJ ZESTAW", type="primary", use_container_width=True):
            with st.spinner("Obliczam prawdopodobieństwo..."):
                liczby, strategia = generuj_kupon(dane)

                # Zapisz do historii
                zapisz_wynik(liczby, strategia)

                # Wyświetl wynik
                st.success(f"Twój zestaw ({strategia}):")
                st.markdown(f"## 🎲 {str(liczby)}")
                st.balloons()

    with col2:
        st.info("💡 **Wskazówka:**\nJeśli system wylosuje strategię ZIMNĄ, warto puścić ten kupon jako dodatkowy!")

    # 3. TABELA HISTORII (Ostatnie 10)
    st.divider()
    st.subheader("📜 Ostatnie 10 wygenerowanych zestawów")
    st.write("Zobacz, co system wylosował dla innych użytkowników:")

    # Odświeżamy historię po kliknięciu
    historia_aktualna = wczytaj_historie()

    # Pokazujemy tylko 10 ostatnich (odwrócona kolejność, żeby najnowsze były u góry)
    if not historia_aktualna.empty:
        st.dataframe(
            historia_aktualna.tail(10).iloc[::-1],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("Brak historii. Bądź pierwszy!")


if __name__ == "__main__":
    main()