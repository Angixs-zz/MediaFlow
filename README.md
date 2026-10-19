# MediaFlow

Interfaz web local para guardar videos o audio de YouTube cuando tengas permiso. Construida con FastAPI + yt-dlp + FFmpeg.

## Ejecutar en Ubuntu

Requisitos: Python 3.10+, FFmpeg, y recomendable un runtime JavaScript compatible con la versión actual de yt-dlp.

```bash
sudo apt install python3-venv ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Abre http://127.0.0.1:8000. Los archivos quedan en `downloads/` y puedes guardarlos desde el navegador con el botón de descarga.

## Limitaciones y seguridad

- Solo admite enlaces HTTPS de dominios YouTube permitidos.
- Se descarga solo un video por solicitud (no playlists).
- Los trabajos se guardan en memoria y se pierden al reiniciar el servidor; los archivos permanecen.
- No cuenta con autenticación, cuotas ni limpieza automática. **No lo expongas a Internet ni habilites públicamente la API** sin agregar controles.
- GitHub Pages es alojamiento estático: no puede ejecutar este backend. Se puede publicar una versión del frontend allí, pero necesita un backend separado y CORS adecuadamente configurado.
- YouTube cambia con frecuencia: mantén yt-dlp actualizado (`pip install -U yt-dlp`) y considera la necesidad de un runtime JS.
- Respeta derechos de autor y los términos de los servicios.
# MediaFlow
