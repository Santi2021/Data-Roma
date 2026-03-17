# 📡 DataRoma Intelligence Terminal

Dashboard estilo Bloomberg para analizar los movimientos del smart money vía DataRoma.

## Instalación

```bash
pip install -r requirements.txt
```

## Correr la app

```bash
streamlit run app.py
```

## Secciones

| Sección | Descripción |
|---|---|
| 🏆 Superinvestors | Directorio completo de managers con scraping directo |
| 📋 Portfolio Viewer | Ver holdings de cualquier manager, con tabla y treemap |
| ⚡ Recent Activity | Movimientos recientes de 13F, filtrado por buys/sells |
| 🔗 Overlap Analysis | Heatmap de overlap entre managers seleccionados |
| 📊 Aggregate Intelligence | **El módulo más potente**: conviction plays, net flow por acción, tabla agregada |

## Notas

- Los datos se cachean 60 minutos (Streamlit cache).
- DataRoma puede rate-limitear si se hacen muchas requests seguidas. Si falla, esperá unos minutos.
- El módulo de Aggregate Intelligence puede tardar si se seleccionan muchos managers (1 request por manager).

## Estructura

```
datarома_app/
├── app.py           # UI principal (Streamlit)
├── scraper.py       # Scraping de DataRoma
├── analyzer.py      # Análisis, overlap, agregación
├── requirements.txt
└── README.md
```
