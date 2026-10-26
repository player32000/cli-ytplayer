# YouTube Playlist CLI

[English](../README.md) | [Español](README.md)

Reproductor y descargador de playlists de YouTube y YouTube Music desde la
consola, hecho en Python. Los scripts principales están en la raíz y se
mantienen en una sola versión, con nombres, variables y mensajes en inglés.

## Funciones

- Reproduce playlists en streaming, una canción a la vez, sin descargarlas de
  antemano.
- Permite avanzar, retroceder y repetir la canción actual.
- Descarga la canción actual como audio MP3 o video desde el reproductor.
- Descarga playlists completas como audio o video.
- Admite los Me gusta de YouTube Music (`lm`), los Me gusta de YouTube (`ll`) y
  playlists propias (`custom`).
- Comparte el progreso entre el reproductor y el descargador.

## Requisitos

- Python 3.10 o posterior.
- `yt-dlp` con sus componentes EJS:

  ```powershell
  python -m pip install -U "yt-dlp[default]"
  ```

- Un runtime JavaScript para el desafío de YouTube: Node.js 22 o posterior, o
  Deno 2.3 o posterior. Node.js no es obligatorio; el programa lo prefiere si
  está disponible y, de lo contrario, yt-dlp puede usar Deno.
- Una compilación de `mpv` compatible con tu procesador, necesaria para
  `player.py`.
- `ffmpeg` en el `PATH` para convertir audio a MP3.

En Windows, `player.py` busca `mpv.exe` en `mpv-portable` junto al script,
después en el `PATH` y luego en las ubicaciones estándar de instalación. El
proyecto no incluye mpv: descargá una compilación confiable y compatible con tu
procesador. Si mpv termina con el código `0xC000001D`, probá una compilación
x86-64 estándar en vez de una optimizada para CPUs más recientes (como
`64bit-v3`).

## Cookies y acceso a la cuenta

Para playlists privadas, como tus Me gusta, pasá cookies válidas exportadas en
formato Netscape con `--cookies`. El programa no detecta los archivos de cookies
automáticamente. Si omitís esa opción, yt-dlp intenta usar el navegador
seleccionado con `--browser` (Chrome por defecto).

Las cookies son credenciales de tu cuenta: **no las compartas ni las subas a
GitHub**. `.gitignore` excluye archivos de cookies, descargas, progreso, caché
de Python y la carpeta local opcional `mpv-portable`. Revisá siempre qué
archivos vas a publicar.

En los ejemplos, reemplazá `RUTA\A\cookies.txt` por la ruta de tu propio
archivo.

## Reproductor

Ejecutá desde la carpeta del proyecto:

```powershell
# Me gusta de YouTube Music
python player.py --source lm --cookies "RUTA\A\cookies.txt"

# Me gusta de YouTube
python player.py --source ll --cookies "RUTA\A\cookies.txt"

# Playlist propia
python player.py --source custom --url "https://www.youtube.com/playlist?list=ID_DE_PLAYLIST" --cookies "RUTA\A\cookies.txt"
```

En Windows, presioná las teclas directamente, sin Enter: `Enter` pasa a la
canción siguiente, `p` vuelve a la anterior, `r` activa o desactiva la repetición,
`a` descarga el audio actual, `v` descarga el video actual y `q` sale. La lectura
instantánea de teclas y el control de Quick Edit de CMD, exclusivos de Windows,
están en `windows_console.py`. En macOS y Linux, escribí el control y presioná
Enter; esos sistemas usan la entrada estándar de Python.

## Descargador de playlists

```powershell
# Me gusta de YouTube Music como MP3
python download_playlist.py --source lm --mode audio --cookies "RUTA\A\cookies.txt"

# Me gusta de YouTube como video
python download_playlist.py --source ll --mode video --cookies "RUTA\A\cookies.txt"

# Playlist propia como MP3
python download_playlist.py --source custom --url "https://www.youtube.com/playlist?list=ID_DE_PLAYLIST" --mode audio --cookies "RUTA\A\cookies.txt"
```

Los orígenes `lm` y `ll` descargan en bloque todos los elementos disponibles de
los Me gusta. Para bajar en bloque una playlist específica, usá
`--source custom --url "URL_DE_LA_PLAYLIST"`. Se recomiendan las opciones en inglés (`--source`, `--browser`, `--mode`);
también siguen funcionando sus alias anteriores en español (`--origen`,
`--navegador`, `--modo`).

Las descargas se guardan en las carpetas existentes `descargas_*`. El archivo
compartido de progreso se llama `download_archive.txt` y conserva el historial
anterior.

## Archivos del proyecto

- `player.py`: reproductor y descargador de la canción actual.
- `windows_console.py`: lectura instantánea de teclas y ajustes de consola
  exclusivos de Windows. Los otros sistemas usan la entrada estándar de Python.
- `download_playlist.py`: descarga todos los elementos de una playlist de
  Me gusta o de una playlist específica.
- [README en inglés](../README.md).

## Publicación en GitHub

Revisá los archivos que vas a agregar. No publiques cookies, archivos
descargados, archivos de progreso ni binarios de terceros. `.gitignore` ayuda
a excluir datos locales, pero no reemplaza una revisión manual.
