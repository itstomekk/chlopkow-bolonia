/* Map geometry: a 1:1 port of osm/geo.py (equirectangular projection of BBOX at A art px per metre).
   Values come from GET /api/geo so the editor always matches the Python generator. */
(function () {
  const G = {
    init(info) { Object.assign(G, info); G.minlat = info.bbox[0]; G.minlon = info.bbox[1]; G.maxlat = info.bbox[2]; G.maxlon = info.bbox[3]; },
    // lat/lon -> art pixels (floats), same formula as geo.P
    P(lat, lon) { return [(lon - G.minlon) * G.mx * G.a, (G.maxlat - lat) * G.my * G.a]; },
    // art pixels -> [lat, lon], same formula as geo.to_latlon
    toLL(x, y) { return [G.maxlat - y / (G.my * G.a), G.minlon + x / (G.mx * G.a)]; },
    polyPx(poly) { return poly.map(([la, lo]) => G.P(la, lo)); },
    SECTOR: 500,
    sector(x, y) {
      if (x < 0 || y < 0 || x >= G.w || y >= G.h) return '–';
      return String.fromCharCode(65 + Math.floor(x / G.SECTOR)) + (Math.floor(y / G.SECTOR) + 1);
    },
  };
  window.GEO = G;
})();
