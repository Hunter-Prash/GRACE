import os

path = "gui/components.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Make sure imports are added at the top if they aren't there
if "import os" not in content:
    content = "import os\n" + content

if "QWebEngineView" not in content:
    import_str = """try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
except ImportError:
    QWebEngineView = None
"""
    content = content.replace("from gui.theme", import_str + "\nfrom gui.theme")

new_code = """
# ──────────────────────────────────────────
# MAP WIDGETS
# ──────────────────────────────────────────
class CyberMapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        
        if QWebEngineView is None:
            lbl = QLabel("QWebEngineView not available")
            lbl.setStyleSheet(f"color: {PINK};")
            self.lay.addWidget(lbl)
            return

        self.view = QWebEngineView()
        self.view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.lay.addWidget(self.view)
        
        self.api_key = os.getenv("TOMTOM_API_KEY", "")
        self.is_loaded = False
        self.view.loadFinished.connect(self._on_load_finished)
        self._load_html()

    def _load_html(self):
        html = f\"\"\"
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='utf-8' />
            <title>TomTom Map</title>
            <style>
                body {{ margin: 0; padding: 0; background-color: #0d1117; }}
                #map {{ width: 100vw; height: 100vh; }}
                .tt-popup-content {{ color: #00d4ff; background: #0d1117; border: 1px solid #00d4ff; font-family: monospace; font-size: 10px; }}
            </style>
            <link rel='stylesheet' type='text/css' href='https://api.tomtom.com/maps-sdk-for-web/cdn/6.x/6.25.0/maps/maps.css'>
            <script src='https://api.tomtom.com/maps-sdk-for-web/cdn/6.x/6.25.0/maps/maps-web.min.js'></script>
        </head>
        <body>
            <div id='map'></div>
            <script>
                var map;
                var routeLayerId = 'route_layer';
                var markers = [];

                function initMap() {{
                    map = tt.map({{
                        key: '{self.api_key}',
                        container: 'map',
                        style: 'https://api.tomtom.com/style/1/style/21.1.0-*?map=basic_night&poi=poi_main',
                        center: [80.22, 13.08],
                        zoom: 11,
                        pitch: 45
                    }});
                }}

                function drawRoute(origin, dest) {{
                    var [oLat, oLon] = origin.split(',');
                    var [dLat, dLon] = dest.split(',');
                    
                    fetch(`https://api.tomtom.com/routing/1/calculateRoute/${{origin}}:${{dest}}/json?key={self.api_key}`)
                    .then(r => r.json())
                    .then(data => {{
                        if (map.getLayer(routeLayerId)) {{
                            map.removeLayer(routeLayerId);
                            map.removeSource(routeLayerId);
                        }}
                        
                        var geojson = {{
                            type: 'Feature',
                            geometry: {{
                                type: 'LineString',
                                coordinates: data.routes[0].legs[0].points.map(p => [p.longitude, p.latitude])
                            }}
                        }};
                        
                        map.addLayer({{
                            id: routeLayerId,
                            type: 'line',
                            source: {{ type: 'geojson', data: geojson }},
                            paint: {{
                                'line-color': '#00d4ff',
                                'line-width': 4,
                                'line-opacity': 0.8
                            }}
                        }});

                        var bounds = new tt.LngLatBounds();
                        data.routes[0].legs[0].points.forEach(p => bounds.extend([p.longitude, p.latitude]));
                        map.fitBounds(bounds, {{ padding: 50, maxZoom: 14 }});
                    }})
                    .catch(e => console.error(e));
                }}

                function showPlaces(placesArray) {{
                    markers.forEach(m => m.remove());
                    markers = [];
                    
                    if (placesArray.length === 0) return;

                    var bounds = new tt.LngLatBounds();
                    
                    placesArray.forEach(p => {{
                        var [lat, lon] = p.coords.split(',');
                        var el = document.createElement('div');
                        el.style.width = '12px';
                        el.style.height = '12px';
                        el.style.borderRadius = '50%';
                        el.style.background = '#ff2d78';
                        el.style.boxShadow = '0 0 10px #ff2d78';
                        
                        var marker = new tt.Marker({{element: el}})
                            .setLngLat([parseFloat(lon), parseFloat(lat)])
                            .setPopup(new tt.Popup({{offset: 25}}).setHTML(`<b>${{p.name}}</b>`))
                            .addTo(map);
                        
                        markers.push(marker);
                        bounds.extend([parseFloat(lon), parseFloat(lat)]);
                    }});
                    
                    map.fitBounds(bounds, {{ padding: 50, maxZoom: 14 }});
                }}

                initMap();
            </script>
        </body>
        </html>
        \"\"\"
        self.view.setHtml(html)

    def _on_load_finished(self):
        self.is_loaded = True

    def show_route(self, originCoords, destCoords):
        if not self.view or not self.is_loaded: return
        js = f"drawRoute('{originCoords}', '{destCoords}');"
        self.view.page().runJavaScript(js)

    def show_places(self, places):
        if not self.view or not self.is_loaded: return
        import json
        js = f"showPlaces({json.dumps(places)});"
        self.view.page().runJavaScript(js)


class MapToggleTab(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_glowing = False
        
    def set_glow(self, state):
        self.is_glowing = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = parse_color(PINK) if self.is_glowing else parse_color(CYAN_DIM)
        bg_color = QColor(color.red(), color.green(), color.blue(), 50 if self.is_glowing else 15)
        
        painter.fillRect(self.rect(), bg_color)
        
        pen = QPen(color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        painter.setFont(mono(9, True))
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-90)
        
        text = "MAP READY" if self.is_glowing else "OPEN MAP"
        rect = QRect(-60, -15, 120, 30)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class AnimatedMapPane(QFrame):
    sig_data_ready = pyqtSignal()
    sig_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self.setStyleSheet(f"background: {BG2}; border-left: 1px solid {BORDER};")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        
        # Header
        hdr = QLabel("SATELLITE UPLINK // MAPS")
        hdr.setFont(mono(10, True))
        hdr.setStyleSheet(f"color: {CYAN}; padding: 10px; background: rgba(0,212,255,0.05); border-bottom: 1px solid {BORDER};")
        lay.addWidget(hdr)
        
        # Map Widget
        self.map_widget = CyberMapWidget()
        lay.addWidget(self.map_widget, 1)
        
        # Close Button
        self.btn_close = CyberButton("CLOSE UPLINK", PINK)
        self.btn_close.clicked.connect(self.slide_out)
        lay.addWidget(self.btn_close)
        
        self.is_open = False
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        
    def slide_in(self):
        if self.is_open: return
        self.is_open = True
        self.anim.setStartValue(0)
        self.anim.setEndValue(380)
        self.anim.start()
        
    def slide_out(self):
        if not self.is_open: return
        self.is_open = False
        self.anim.setStartValue(380)
        self.anim.setEndValue(0)
        self.anim.start()
        self.sig_closed.emit()

    def process_map_data(self, data):
        if data.get('type') == 'route':
            self.map_widget.show_route(data['originCoords'], data['destCoords'])
        elif data.get('type') == 'places':
            self.map_widget.show_places(data['places'])
        
        self.sig_data_ready.emit()
"""

# Append it to components.py
with open(path, "a", encoding="utf-8") as f:
    f.write(new_code)

# Add pyqtSignal if missing from imports
if "pyqtSignal" not in content:
    content = content.replace("from PyQt6.QtCore import ", "from PyQt6.QtCore import pyqtSignal, ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        f.write(new_code)

print("Restored successfully.")
