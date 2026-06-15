# Procomex Scraper

Scraper de imágenes de productos ferreteros orientado a `Shopify`.

## Objetivo

A partir de un archivo CSV en `entrada/`, descargar al menos 2 imágenes por SKU desde los catálogos oficiales de los fabricantes.

## Estructura del proyecto

- `adapters/`: implementaciones por grupo/marca.
- `core/`: lógica de CSV, descarga, validación, rate limiting y reanudación.
- `entrada/`: CSV de entrada.
- `salida/`: imágenes y `resultados.csv`.
- `tests/`: pruebas unitarias.

## Uso

1. Colocar el CSV de entrada en `entrada/`.
2. Construir la imagen (la primera vez o tras cambios de código):

```bash
docker compose build
```

3. Ejecutar el scraper:

```bash
docker compose run --rm scraper
```

> Nota: se usa `run --rm` y no `up` porque el scraper es una tarea de un solo
> disparo: corre una vez y termina. `--rm` elimina el contenedor al finalizar.

4. Los resultados y las imágenes se escriben en `salida/`.

### Reprocesar (forzar)

Por defecto el scraper **salta** los SKUs que ya estén en `salida/resultados.csv`.
Para volver a buscar todos los SKUs del input aunque ya estén registrados:

```bash
docker compose run --rm scraper --force
```

`--force` solo afecta a los SKUs presentes en el `input.csv` actual; las filas de
otros SKUs en `resultados.csv` se conservan, y no se generan duplicados.

> Para un manual paso a paso pensado para usuarios no técnicos, ver [MANUAL.md](MANUAL.md).

## Formato del CSV de entrada

Columnas obligatorias:
- `sku`
- `marca`

Columnas opcionales:
- `descripcion`
- `prioridad`

## Resultados

`salida/resultados.csv` contendrá:
- `sku`
- `marca`
- `estatus`
- `fuente`
- `imagen_1`
- `imagen_2`
- `error`

## Notas

- El motor es asincrónico y por dominio.
- La reanudación se logra escribiendo `resultados.csv` conforme avanza.
- `adapters/truper.py` y `adapters/urrea.py` están preparados como adaptadores.
- En v1, `playwright` está disponible como fallback, pero no se usa por defecto.
