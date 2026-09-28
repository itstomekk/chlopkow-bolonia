/* Hand tool: pan with the left button. Also the safe default tool. */
Editor.registerTool({ id: 'pan', label: 'Rączka', title: 'Przesuwanie mapy lewym przyciskiem', pans: true, cursor: 'grab',
  panel(el) { el.innerHTML = '<h3>Rączka</h3><p>Przeciągnij, żeby przesunąć. Kółko = zoom. Wpisz x,y / lat,lon / sektor w polu Pozycja.</p>'; } });
