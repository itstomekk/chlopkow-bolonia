# Kanon stylu postaci 🎨

Zasady Tomka (2026-10-27) dla każdej nowej lub przerabianej postaci. Obraz wzorcowy: `canon_ref.png` (budowany przez `build_canon_ref.py`), dokładany jako dodatkowy `--ref` przy generowaniu.

- **Wzorzec linii i stylu: IWONA, HALINA i AREK.** Grubość obrysu, duże bloki pikseli, płaskie cieniowanie 2-3 stopnie.
- **Głowa i ręce: rozmiar pomiędzy nimi** (około jedna trzecia wysokości ciała na głowę, wyraźne, grube dłonie i stopy).
- **Grube, zwarte postacie.** Nie cienkie ani drobno pikselowe (zły przykład: stary Marcin, Wiesio, Wesołych Świąt z drobnym wzorem kraty).
- **Wysokie postacie (Wiesio, Kostek) mają za małą głowę.** Przy przeróbce powiększyć głowę, nie zmniejszać ciała.
- Układ chodu: szablon BERCIK 4x2 (`gen/bercik/bercik_walkcycle_raw.png`), wysokość 75 px, build `gen/build_cast_walk.py`.
- Zdjęcia osób: tylko tam, gdzie Tomek wyraźnie zezwolił (patrz `AGENTS.md`), nigdy do gita.

## Twarde liczby (zmierzone 2026-10-27 na arkuszach, które Tomek zaakceptował)

Dobre wzorce: AREK, IWONA, HALINA, KOSTEK, WIESIO, BERCIK. Wspólne:
- Treść postaci ma **75 px natywnie**, skalowanie **2x NEAREST** (150 px w komórce 130x170, stopa 6 px od dołu). Bez wygładzania.
- **Paleta maks. 40 kolorów** na arkusz, twardy kanał alfa (bez półprzezroczystości). Nowy arkusz z tysiącami kolorów (stary Marcin, 6000) = źle, to znak drobnego, "niepikselowego" rysunku.
- Obrys ciemny, **2-4 piksele natywne** (po skalowaniu 4-8 px), ciągły, bez rozmytych krawędzi.
- Głowa około 1/3 wysokości ciała, dłonie i stopy wyraźne; szerokość górnej ćwiartki ciała 50-66 px (głowa z włosami), czyli głowa nie węższa niż ~50 px.
- Cieniowanie płaskie, 2-3 stopnie, światło z lewej góry. Brak drobnych wzorów (kratka, paski tylko duże bloki).

Kontrola po zbudowaniu: `python gen/style_canon/check_canon.py <id>` sprawdza wysokość, paletę i alfę.
