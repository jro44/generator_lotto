import streamlit as st
import pypdf
import re
import random
import os
from collections import Counter

# --- KONFIGURACJA ---
PLIK_PDF = "999los.pdf"


# --- FUNKCJE LOGICZNE ---

@st.cache_data  # To sprawia, że PDF jest czytany tylko raz, a nie przy każdym kliknięciu
def wczytaj_dane_z_pdf(sciezka):
    if not os.path.exists(sciezka):
        return None

    wszystkie_losowania = []

    try:
        reader = pypdf.PdfReader(sciezka)
        for strona in reader.pages:
            tekst = strona.extract_text()
            if not tekst: continue

            # Tokenizacja
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

            # Logika parowania ID z liczbami
            page_ids = [t for t in clean_tokens if t >= 6000]
            if not page_ids: continue

            # Znajdujemy indeks pierwszego ID
            try:
                first_id_index = clean_tokens.index(page_ids[0])
            except:
                continue

            # Wszystko przed pierwszym ID to potencjalne liczby
            candidate_nums = clean_tokens[:first_id_index]
            valid_nums = [n for n in candidate_nums if 1 <= n <= 49]

            num_draws = len(page_ids)
            expected = num_draws * 6

            if len(valid_nums) >= expected:
                final_nums = valid_nums[-expected:]
                # Zapisujemy w strukturze, żeby zachować kolejność losowań
                for i in range(num_draws):
                    # Zakładamy, że ID idą malejąco (7306, 7305...), a liczby są w blokach
                    # Ponieważ PDFy bywają różne, bierzemy po prostu paczki po 6
                    los = {
                        'ID': page_ids[i],
                        'Liczby': final_nums[i * 6: (i + 1) * 6]
                    }
                    wszystkie_losowania.append(los)

    except Exception as e:
        st.error(f"Błąd odczytu PDF: {e}")
        return None

    # Sortujemy losowania od najnowszego (najwyższe ID)
    wszystkie_losowania.sort(key=lambda x: x['ID'], reverse=True)
    return wszystkie_losowania


def generuj_kupon(dane):
    if not dane:
        return None, "Brak danych"

    # 1. Wyodrębnienie ostatnich 3 losowań (zakazane dla strategii zimnej)
    ostatnie_3 = dane[:3]
    zakazane_liczby = set()
    for los in ostatnie_3:
        zakazane_liczby.update(los['Liczby'])

    # 2. Statystyka ogólna (dla strategii gorącej)
    wszystkie_liczby_flat = [n for los in dane for n in los['Liczby']]
    licznik = Counter(wszystkie_liczby_flat)

    # --- DECYZJA LOGICZNA ---
    # Losujemy liczbę od 0.0 do 1.0
    # Jeśli wypadnie mniej niż 0.2 (20%), idziemy w strategię ZIMNĄ.
    # W przeciwnym razie (80%), idziemy w strategię GORĄCĄ.

    los_strategii = random.random()
    kupon = set()
    typ_strategii = ""

    if los_strategii < 0.20:
        # === STRATEGIA ZIMNA (CHAOS) ===
        typ_strategii = "❄️ ZIMNY STRZAŁ (Unikamy ostatnich liczb)"

        # Pula: Liczby 1-49, ale BEZ tych, które padły w ostatnich 3 losowaniach
        pula_dozwolona = [n for n in range(1, 50) if n not in zakazane_liczby]

        # Z tej puli wybieramy te, które historycznie padały NAJRZADZIEJ
        # Sortujemy pulę wg częstości występowania (rosnąco)
        pula_posortowana = sorted(pula_dozwolona, key=lambda x: licznik.get(x, 0))

        # Bierzemy 15 najrzadszych z dozwolonych i losujemy z nich 6
        pula_najzimniejsza = pula_posortowana[:15]
        kupon = set(random.sample(pula_najzimniejsza, 6))

    else:
        # === STRATEGIA GORĄCA (STATYSTYKA) ===
        typ_strategii = "🔥 GORĄCY TYP (Wysokie prawdopodobieństwo)"

        # Przygotowanie wag do losowania
        populacja = list(licznik.keys())
        wagi = list(licznik.values())

        # Losujemy 6 liczb (ważone częstością)
        while len(kupon) < 6:
            kandydat = random.choices(populacja, weights=wagi, k=1)[0]
            kupon.add(kandydat)

    return sorted(list(kupon)), typ_strategii


# --- INTERFEJS STRONY ---
def main():
    st.set_page_config(page_title="Generator Lotto 999", page_icon="🎰")

    st.title("🎰 Inteligentny Generator")
    st.markdown("""
    System analizuje **998 losowań** z bazy PDF.
    - **80% szans:** System dobierze liczby statystycznie najczęstsze.
    - **20% szans:** System zagra "pod prąd" (ominie ostatnie wyniki i wybierze liczby zaległe).
    """)

    # Wczytanie danych
    if not os.path.exists(PLIK_PDF):
        st.error(f"⚠️ Nie znaleziono pliku {PLIK_PDF}. Wgraj go do repozytorium.")
        return

    dane = wczytaj_dane_z_pdf(PLIK_PDF)

    if dane:
        st.success(f"✅ Baza danych aktywna: {len(dane)} losowań.")

        st.write("---")

        # Wielki przycisk
        if st.button("🎲 GENERUJ ZESTAW", use_container_width=True, type="primary"):
            with st.spinner("Maszyna losująca ruszyła..."):
                liczby, opis = generuj_kupon(dane)

                # Wyświetlanie wyniku
                st.subheader("Twój Zestaw:")
                cols = st.columns(6)
                for i, num in enumerate(liczby):
                    cols[i].metric(label=f"Liczba {i + 1}", value=num)

                if "ZIMNY" in opis:
                    st.warning(opis)
                else:
                    st.info(opis)
    else:
        st.error("Nie udało się przetworzyć pliku PDF.")


if __name__ == "__main__":
    main()