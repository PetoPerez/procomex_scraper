# Manual de usuario — Buscador de imágenes Procomex

Esta guía explica **paso a paso** cómo usar el programa que busca y descarga
imágenes de productos de ferretería. No necesitas saber programar. Solo hay que
copiar y pegar unas líneas.

---

## 1. ¿Qué hace este programa?

Tú le das una **lista de productos** (un archivo de Excel/CSV) y el programa entra
a las páginas oficiales de los fabricantes, busca cada producto y **descarga sus
imágenes** automáticamente. Al final te entrega:

- Las **imágenes** de cada producto (archivos `.jpg`).
- Un **reporte** que dice si encontró o no cada producto.

---

## 2. Instalar Docker (una sola vez)

El programa funciona con una herramienta gratuita llamada **Docker**. Solo se
instala **una vez**. Busca abajo tu sistema operativo y copia/pega los comandos en
la **Terminal**.

> ¿Cómo abrir la Terminal?
> - **Windows**: menú Inicio → escribe `PowerShell` → ábrelo.
> - **macOS**: `Cmd + Espacio` → escribe `Terminal` → Enter.
> - **Linux**: `Ctrl + Alt + T`.

### Windows

1. En PowerShell, instala Docker Desktop con:

   ```
   winget install -e --id Docker.DockerDesktop
   ```

2. Cuando termine, **reinicia la computadora**.
3. Abre **Docker Desktop** desde el menú Inicio y espera a que el ícono de la
   ballena (abajo a la derecha) deje de moverse: eso significa que ya está listo.

### macOS

1. Si no tienes Homebrew (un instalador), pégalo primero:

   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Instala Docker Desktop:

   ```
   brew install --cask docker
   ```

3. Abre **Docker** desde Aplicaciones y espera a que el ícono de la ballena
   (arriba a la derecha) deje de moverse.

### Linux (Ubuntu / Debian y similares)

1. Instala Docker con el script oficial:

   ```
   curl -fsSL https://get.docker.com | sh
   ```

2. Da permiso a tu usuario para usar Docker sin escribir `sudo` cada vez:

   ```
   sudo usermod -aG docker $USER
   ```

3. **Cierra sesión y vuelve a entrar** (o reinicia) para que el permiso tome efecto.

### Comprobar que quedó bien (cualquier sistema)

Escribe esto en la Terminal:

```
docker --version
```

Si responde con un número de versión (por ejemplo `Docker version 29.x`), ¡quedó
instalado! Si da error, revisa que Docker esté abierto/corriendo y vuelve a
intentar.

> Esto solo se hace una vez. Después ya no se vuelve a tocar.

---

## 3. Descargar el programa (una sola vez)

El código del programa vive en internet (en GitHub). Para traerlo a tu computadora
se usa otra herramienta gratuita llamada **Git**.

### Paso A — Instalar Git

Abre la **Terminal** (igual que en el punto 2) y pega el comando de tu sistema:

- **Windows**:

  ```
  winget install -e --id Git.Git
  ```

  Después **cierra y vuelve a abrir** la Terminal.

- **macOS**:

  ```
  brew install git
  ```

- **Linux (Ubuntu / Debian y similares)**:

  ```
  sudo apt update && sudo apt install -y git
  ```

Comprueba que quedó instalado:

```
git --version
```

Si responde con un número de versión, ¡listo!

### Paso B — Descargar el programa

1. Colócate en la carpeta donde quieras guardar el programa (por ejemplo, tus
   Documentos):

   ```
   cd ruta/donde/lo/quieras/guardar
   ```

2. Descarga el programa con:

   ```
   git clone https://github.com/PetoPerez/procomex_scraper.git
   ```

   Esto crea una carpeta nueva llamada **`procomex_scraper`** con todo dentro.

3. Entra a esa carpeta:

   ```
   cd procomex_scraper
   ```

> Esto solo se hace **una vez**. La carpeta queda en tu computadora.

### Paso C — Actualizar el programa más adelante

Cuando te avisen que hay una versión nueva, **no** hay que descargar todo otra vez.
Solo entra a la carpeta del programa y pide los últimos cambios:

```
cd ruta/a/procomex_scraper
git pull
```

---

## 4. Las dos carpetas importantes

Dentro de la carpeta del programa hay dos carpetas que vas a usar siempre:

| Carpeta    | ¿Para qué sirve?                                                |
|------------|----------------------------------------------------------------|
| `entrada/` | Aquí **tú pones** la lista de productos a buscar.              |
| `salida/`  | Aquí el programa **te deja** las imágenes y el reporte final. |

---

## 5. Preparar la lista de productos

1. Dentro de la carpeta `entrada/` hay un archivo llamado **`input.csv`**.
2. Ábrelo con **Excel** (o el Bloc de notas).
3. Llénalo con tus productos. La primera fila son los títulos y **no se cambia**:

   ```
   sku,marca,descripcion,prioridad
   PFR01,surtek,PINZA PARA ANILLOS DE RETENCIÓN,1
   PFR02,surtek,PINZA PARA ANILLOS DE RETENCIÓN,1
   ```

   - **sku**: el código del producto. *(obligatorio)*
   - **marca**: la marca del producto, en minúsculas. *(obligatorio)*
   - **descripcion**: el nombre del producto. *(opcional, pero ayuda a encontrarlo)*
   - **prioridad**: un número. *(opcional)*

   Marcas válidas: `truper`, `foy`, `foset`, `urrea`, `surtek`, `futura`,
   `tubin`, `fleximatic`, `solver`, `coflex`, `valmex`, `rugo`, `polimex`.

   > Para la marca **`tubin`** la búsqueda se hace por la **descripción** (no por
   > el código), así que entre mejor escrita esté la `descripcion`, mejor la
   > coincidencia. Tubin entrega **una** imagen por producto (saldrá como
   > `parcial`, no es error).
   >
   > Para **`fleximatic`**, **`solver`** y **`coflex`** las imágenes salen de un
   > **catálogo PDF** (ver punto 5.1). El `sku` debe ser el **código del catálogo**
   > (ej. `2953` en Fleximatic, `TF-100` en Coflex). Estas imágenes son del
   > catálogo: una misma foto puede repetirse entre productos parecidos y la
   > calidad es menor (saldrán como `parcial`).

### 5.1 Marcas que usan catálogo PDF (`fleximatic`, `solver`, `coflex`)

Algunas marcas no tienen página web; sus imágenes se sacan de su **catálogo PDF**:

1. Consigue el PDF del catálogo de la marca.
2. Cópialo dentro de la carpeta **`entrada/`**.
3. **El nombre del archivo debe contener el nombre de la marca** para que el
   programa sepa de cuál es. Ejemplos válidos:
   - `Fleximatic_catalogo.pdf`  (contiene "flex")
   - `Catalogo Solver 2025.pdf` (contiene "solver")
   - `Coflex_CAT_MX2025.pdf`    (contiene "coflex")
4. En `input.csv`, pon esos productos con su `marca` y con el **código del
   catálogo** en la columna `sku`. Ejemplo:

   ```
   sku,marca,descripcion,prioridad
   2953,fleximatic,Cespol flexible tipo P,1
   ```

> La primera vez tarda un poco (lee el PDF completo); luego va más rápido.

4. **Guarda** el archivo. En Excel, al guardar elige el formato
   **"CSV (delimitado por comas)"**.

> Consejo: pon un producto por renglón. Puedes poner cuantos quieras.

---

## 6. Ejecutar el programa

1. Abre la aplicación **Terminal** (en Windows: "Símbolo del sistema" o
   "PowerShell"; en Mac: "Terminal").
2. Entra a la carpeta del programa (la que descargaste en el punto 3). Escribe
   `cd ` (con un espacio), arrastra la
   carpeta del programa desde el explorador de archivos hasta la ventana de la
   Terminal y presiona **Enter**. Se verá parecido a esto (la ruta será la de
   **tu** computadora, no esta):

   ```
   cd ruta/a/procomex_scraper
   ```

3. **Solo la primera vez** (o cuando te avisen que hubo cambios), prepara el
   programa con:

   ```
   docker compose build
   ```

   Espera a que termine (puede tardar unos minutos la primera vez).

4. Para buscar las imágenes, escribe:

   ```
   docker compose run --rm scraper
   ```

5. Verás varios renglones apareciendo: es el programa trabajando. Cuando vuelve a
   aparecer la línea para escribir, **ya terminó**.

---

## 7. Ver los resultados

Abre la carpeta `salida/`. Vas a encontrar:

- **Las imágenes**, nombradas con el código del producto. Por ejemplo:
  - `PFR01_1.jpg` (primera imagen del producto PFR01)
  - `PFR01_2.jpg` (segunda imagen del producto PFR01)
- **El reporte `resultados.csv`** (ábrelo con Excel). La columna **`estatus`** te dice cómo salió cada producto:

  | estatus        | Significa                                          |
  |----------------|----------------------------------------------------|
  | `ok`           | Encontró las 2 imágenes. ✅                         |
  | `parcial`      | Encontró solo 1 imagen.                            |
  | `no_encontrado`| No encontró imágenes. Revisa la columna `error`.  |

---

## 8. Volver a buscar un producto (forzar)

El programa es inteligente: si un producto **ya lo buscó antes**, no lo vuelve a
buscar para no perder tiempo. Si ejecutas y aparece el mensaje
**"No hay SKUs pendientes"**, significa que todos los productos de tu lista ya
estaban hechos.

¿Necesitas que busque **todo otra vez** (por ejemplo, porque corregiste la lista o
quieres imágenes actualizadas)? Usa este comando en su lugar:

```
docker compose run --rm scraper --force
```

La palabra **`--force`** al final le dice: *"búscalos todos de nuevo, aunque ya los
tengas"*.

---

## 9. Problemas comunes

| Problema                                  | Solución                                                                 |
|-------------------------------------------|--------------------------------------------------------------------------|
| "No hay SKUs pendientes"                  | Ya estaban hechos. Usa `--force` para repetirlos (ver punto 8).          |
| Sale un error que menciona `docker`       | Asegúrate de que **Docker Desktop esté abierto** y corriendo.           |
| `git: command not found`                  | Falta instalar Git (ver punto 3, Paso A).                               |
| `estatus` dice `no_encontrado`            | Revisa que el `sku` y la `marca` estén bien escritos en `input.csv`.    |
| No aparecen imágenes nuevas               | Confirma que guardaste `input.csv` como CSV y que estás en la carpeta correcta. |

---

## 10. Resumen rápido (chuleta)

**Instalación (una sola vez):**

```
1. Instala Docker      (ver punto 2)
2. Instala Git         (ver punto 3, Paso A)
3. Descarga el código: git clone https://github.com/PetoPerez/procomex_scraper.git
```

**Uso de cada día:**

```
1. Entra a la carpeta:  cd ruta/a/procomex_scraper
2. (opcional) Actualiza: git pull
3. Edita la lista:       entrada/input.csv  (y guárdala)
4. Ejecuta:              docker compose run --rm scraper
   (o para repetir todo:   docker compose run --rm scraper --force)
5. Recoge resultados:    carpeta salida/
```
