# CLI YT Player

[English](../README.md) | [Español](README.md)

CLI YT Player es una herramienta multiplataforma de línea de comandos para
buscar, reproducir en streaming y descargar videos individuales y playlists de
YouTube y YouTube Music. Los scripts principales están en la raíz y se
mantienen en una sola versión, con nombres, variables y mensajes en inglés.

## Funciones

- Reproduce playlists en streaming, una canción a la vez, sin descargarlas de
  antemano, en modo solo audio o video con audio.
- Permite avanzar, retroceder y repetir la canción actual.
- Descarga la canción actual como audio MP3 o video desde el reproductor.
- Descarga playlists completas como audio o video.
- Admite los Me gusta de YouTube Music (`lm`), los Me gusta de YouTube (`ll`) y
  playlists propias (`custom`).
- Comparte el progreso entre el reproductor y el descargador.

## Instalación en Windows

CLI YT Player necesita Python y herramientas multimedia externas; el lanzamiento
no incluye esos programas. Instalá Python 3.10 o posterior y luego la
dependencia de Python desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
```

La reproducción necesita `mpv`. La conversión a MP3 necesita `ffmpeg` en el
`PATH`. yt-dlp también necesita Node.js 22 o posterior, o Deno 2.3 o posterior,
para acceder a YouTube. Consultá [Requisitos](#requisitos) para más detalles.

Para ejecutar `cli-ytplayer` desde cualquier carpeta en CMD:

1. Guardá esta carpeta en una ubicación permanente o descargá y extraé el
   proyecto allí (por ejemplo, `%LOCALAPPDATA%\Programs\cli-ytplayer`).
2. Agregá esa carpeta al **Path del usuario** desde **Editar las variables de
   entorno de tu cuenta** en Windows. Agregá la carpeta, no el archivo `.cmd`.
3. Cerrá y volvé a abrir CMD; después ejecutá `cli-ytplayer` o
   `cli-ytplayer --help`.

El lanzador `cli-ytplayer.cmd` abre el reproductor interactivo y pasa los
argumentos a `player.py`. Cuando termina el programa, el lanzador espera que
presiones una tecla antes de cerrar, para que puedas leer los mensajes. Esta
pausa también ocurre si lo ejecutás desde una ventana de CMD ya abierta. Las
descargas y los historiales de progreso se guardan en la carpeta actual de CMD.
Python y las herramientas externas deben instalarse por separado.

Para contribuir al código, cloná el repositorio o descargá el archivo fuente.
La versión portable para Windows se distribuye como archivo adjunto en GitHub
Releases.

Para crear el ejecutable de Windows desde el código fuente, ejecutá
`.\build-windows.ps1` en PowerShell. El resultado es
`dist\cli-ytplayer-windows-x64.zip`, con el ejecutable, el lanzador, la licencia y
la guía detallada de [instalación y uso en Windows](WINDOWS-RELEASE-README.md).
La compilación incluye Python y CLI YT Player, pero no mpv, FFmpeg ni Node.js/Deno.

## Requisitos

- **Python 3.10 o posterior** ejecuta CLI YT Player. El lanzador `cli-ytplayer.cmd`
  para Windows comprueba si está instalado y explica cómo instalarlo si falta.
- **yt-dlp** busca en YouTube, lee las playlists, reproduce contenido en
  streaming y descarga audio o video. Instalalo con sus componentes incluidos:

  ```powershell
  python -m pip install -r requirements.txt
  ```

- **Node.js 22 o posterior, o Deno 2.3 o posterior** permite que yt-dlp resuelva
  el desafío JavaScript de YouTube y encuentre los formatos disponibles. Basta
  con instalar uno de los dos.
- **mpv**, compatible con tu procesador, reproduce el audio o video en
  streaming. Es necesario para reproducir, pero no para descargar playlists.
- **FFmpeg** convierte el audio descargado a MP3 y combina streams separados
  de audio y video. Es necesario para descargar y opcional durante la
  reproducción.

Antes de conectarse a YouTube, CLI YT Player comprueba el runtime JavaScript y,
cuando corresponde, FFmpeg o mpv. Si falta algo, muestra para qué sirve y
orientación para instalarlo. El lanzador de Windows avisa si falta Python 3.10+.

En Windows, `player.py` busca `mpv.exe` en `mpv-portable` junto al script,
después en el `PATH` y luego en las ubicaciones estándar de instalación. El
proyecto no incluye mpv. Para Windows x64, podés usar las
[compilaciones de mpv para Windows en SourceForge](https://sourceforge.net/projects/mpv-player-windows/files/64bit/mpv-x86_64-20261018-git-01e2533f31.7z/download).
Para ver opciones de instalación en Windows, macOS y Linux, consultá la
[guía oficial de instalación de mpv](https://mpv.io/installation/).
Si mpv termina con el código `0xC000001D` o Windows informa una instrucción de
CPU no compatible, probá una compilación x86-64 estándar y evitá las variantes
optimizadas para procesadores más nuevos (como `64bit-v3`). Para que CLI YT Player
use una versión portable específica, extraé el archivo de modo que `mpv.exe` y
sus DLL queden directamente dentro de una carpeta `mpv-portable`, junto a
`player.py`. Por ejemplo:

```
cli-ytplayer\
  player.py
  mpv-portable\
    mpv.exe
    ...
```

Conservá las DLL y los demás archivos del archivo comprimido junto a `mpv.exe`.
CLI YT Player busca primero esa carpeta y después las instalaciones de mpv del
`PATH`.

## Cookies y acceso a la cuenta

Para playlists privadas, como tus Me gusta, pasá cookies válidas exportadas en
formato Netscape con `--cookies`. El programa no detecta los archivos de cookies
automáticamente. Si omitís esa opción, yt-dlp intenta usar el navegador
seleccionado con `--browser` (Chrome por defecto).
Para una playlist pública sin cookies del navegador, usá `--browser none`.

Las cookies son credenciales de tu cuenta: **no las compartas ni las subas a
GitHub**. `.gitignore` excluye archivos de cookies, descargas, progreso, caché
de Python y la carpeta local opcional `mpv-portable`. Revisá siempre qué
archivos vas a publicar.

En los ejemplos, reemplazá `RUTA\A\cookies.txt` por la ruta de tu propio
archivo.

## Reproductor

Ejecutá `python player.py` desde la carpeta del proyecto, sin argumentos, para
abrir el asistente interactivo. La primera opción es **Búsqueda rápida en
YouTube (reproducir audio)**: ingresá un término y vas directo a los resultados,
sin elegir una fuente, formato de reproducción ni cookies. Para las demás
opciones, elegí reproducir una lista, descargarla completa como MP3 o descargarla
como video. Para reproducir, elegí solo audio o video con audio; el video se
abre en una ventana de mpv, no dentro de la terminal. Después elegí una playlist
pública y pegá su URL, buscá videos en YouTube o elegí una playlist privada o de
Me gusta. La búsqueda muestra hasta
20 resultados y usa los mismos controles de navegación de la playlist. La
descarga por lotes procesa la playlist elegida o los 20 resultados de búsqueda.
Para las playlists públicas y las búsquedas podés continuar sin cookies de la
cuenta o elegir una sesión existente del navegador o un archivo de cookies. Las
playlists privadas necesitan acceso a la cuenta: elegí un navegador donde ya
hayas iniciado sesión o la opción de archivo de cookies e ingresá su ruta.
En una terminal interactiva, los menús se actualizan en el mismo lugar. Elegí
`Volver` o escribí `b` en una pregunta de texto para regresar al menú anterior.
Podés recorrer las opciones con las flechas arriba/abajo y confirmar con Enter;
también siguen disponibles los números de opción.

Si el acceso con el navegador no funciona, iniciá el reproductor otra vez y
elegí la opción `cookies.txt`. El asistente te indica iniciar sesión en el
navegador, exportar las cookies de `youtube.com` (y `music.youtube.com` para
YouTube Music) en formato Netscape con una herramienta de confianza e ingresar
la ruta completa del archivo. Revisá antes los permisos de la herramienta de
exportación. No compartas ni subas el archivo: permite acceder a tu cuenta.
El asistente recuerda solo la ruta en la configuración local de tu usuario (no
el contenido de las cookies) y ofrece reutilizarla la próxima vez. Si el acceso
falla más adelante, es posible que la sesión haya vencido; iniciá sesión de
nuevo y exportá un archivo actualizado.
En Windows, esa configuración se guarda en `%LOCALAPPDATA%\YouTubePlaylistCLI`;
en macOS y Linux, en `~/.config/youtube-playlist-cli`.
Se conservan los nombres existentes de estas carpetas para que las rutas de
cookies guardadas sigan funcionando después de actualizar.

También podés usar directamente las opciones de consola:

```powershell
# Me gusta de YouTube Music
python player.py --source lm --cookies "RUTA\A\cookies.txt"

# Me gusta de YouTube
python player.py --source ll --cookies "RUTA\A\cookies.txt"

# Playlist propia
python player.py --source custom --url "https://www.youtube.com/playlist?list=ID_DE_PLAYLIST" --cookies "RUTA\A\cookies.txt"

# Buscar en YouTube (usá --browser none para no usar cookies del navegador)
python player.py --search "términos de búsqueda" --browser none

# Descargar una playlist completa como MP3 (usá --mode video para video)
python player.py --source custom --url "https://www.youtube.com/playlist?list=ID_DE_PLAYLIST" --download-playlist --mode audio --cookies "RUTA\A\cookies.txt"

# Descargar los primeros 20 resultados de una búsqueda como MP3
python player.py --search "términos de búsqueda" --download-playlist --browser none

# Reproducir una playlist con video en una ventana de mpv
python player.py --source custom --url "https://www.youtube.com/playlist?list=ID_DE_PLAYLIST" --mode video --cookies "RUTA\A\cookies.txt"
```

Por consola, el modo predeterminado es `--mode audio`; usá `--mode video` para
mostrar el video con audio en una ventana de mpv o para elegir el formato de
video al usar `--download-playlist`.
Los textos usan colores si la terminal los admite; agregá `--no-color` para
desactivarlos. El reproductor muestra el tiempo transcurrido y la duración de la
canción. La barra ASCII de nivel RMS en vivo aparece por defecto; presioná `h`
para mostrar las ayudas y `m` para ocultarla o mostrarla. Usá `--no-meter` para
iniciarla oculta.
El nivel se obtiene de los filtros de audio FFmpeg de mpv y se expresa en dBFS;
los niveles bajos aparecen en verde, los medios en amarillo y los altos en rojo.
La barra usa caracteres de bloque cuando son compatibles (si no, usa ASCII) y
se actualiza en su propia línea hasta 40 veces por segundo sin volver a dibujar
la playlist; el resto de la pantalla se refresca una vez por segundo para evitar
parpadeos. No representa el volumen de los parlantes.

Usá las flechas arriba/abajo para seleccionar una canción y presioná `Enter`
para reproducirla. La vista muestra como máximo seis canciones y se desplaza al
moverte por la playlist; `*` marca la canción en reproducción y `>` la
seleccionada. Las ayudas están ocultas al inicio; presioná `h` para mostrarlas u
ocultarlas. Presioná `n` para pasar a la siguiente, `p` para volver a la anterior,
`r` para activar o desactivar la repetición, `s` para activar o desactivar el modo
aleatorio, `a` para descargar el audio actual, `v` para descargar el video actual
y `q` para salir. El modo aleatorio reproduce todas las canciones una vez en
orden aleatorio antes de comenzar otro ciclo aleatorio. Los controles funcionan
durante la reproducción y mientras se carga una canción. Windows usa las
funciones de `windows_console.py`; macOS y Linux usan la entrada de terminal de
Python.
Las descargas de canciones individuales se ejecutan en segundo plano: podés
encolar varias mientras sigue la reproducción, y el reproductor las procesa de
a una para evitar conflictos. La descarga de toda la lista es una operación
separada al inicio y muestra el progreso de yt-dlp.

Los controles también funcionan mientras se prepara una canción, así podés
saltear una que tarda en cargar sin esperar a que termine de resolverse el audio.
En una terminal interactiva, la vista se actualiza en el mismo lugar en vez de
agregar una nueva lista por cada canción.

Si mpv termina inesperadamente, el reproductor muestra sus mensajes de
diagnóstico ocultando las URL y los valores de credenciales. Para imprimir la
URL completa y temporal del medio cuando ocurra un error, ejecutá el reproductor
con `--show-stream-url-on-error`. No compartas esa URL: puede contener
parámetros temporales de acceso.

Las canciones que YouTube informa como no disponibles se omiten automáticamente.

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

Las descargas se guardan en las carpetas existentes `descargas_*`. El progreso
de audio y video se registra por separado en `download_archive_audio.txt` y
`download_archive_video.txt`, así descargar un formato no impide bajar el otro.
La primera vez, cada archivo se inicializa desde `download_archive.txt` si ese
archivo anterior existe.

## Archivos del proyecto

- `player.py`: reproductor y descargador de la canción actual.
- `interactive_setup.py`: menú inicial para elegir playlist y acceso a la cuenta.
- `console_input.py`: lectura instantánea de teclado compartida entre menús y
  controles de reproducción.
- `download_manager.py`: cola de descargas individuales y ejecución de
  descargas por lotes.
- `terminal_style.py`: detección de compatibilidad ANSI y estilos de texto.
- `player_settings.py`: guarda localmente la ruta del archivo, no las cookies.
- `playlist_navigation.py`: selección, historial de reproducción y navegación
  aleatoria.
- `playlist_view.py`: vista compacta con selección y desplazamiento por las
  canciones cercanas de la playlist.
- `windows_console.py`: ajustes de modo de consola de Windows para actualizar
  la pantalla y controlar la selección.
- `download_playlist.py`: configuración de fuentes y opciones compartidas de
  yt-dlp, además del descargador de playlists por lotes.
- [`LICENSE`](../LICENSE): licencia MIT del proyecto.
- [README en inglés](../README.md).

## Licencia

Este proyecto usa la [licencia MIT](../LICENSE). Permite usar, modificar y
redistribuir el código, incluso en proyectos comerciales, siempre que se
conserven los avisos de copyright y licencia. El software se ofrece sin garantía.

## Publicación en GitHub

Revisá los archivos que vas a agregar. No publiques cookies, archivos
descargados, archivos de progreso ni binarios de terceros. `.gitignore` ayuda
a excluir datos locales, pero no reemplaza una revisión manual.
