# Guía de implementación y aprendizaje
Esta guía describe la versión 0.2.0 que se entrega en el repositorio.
Para conceptos y decisiones detalladas, consultar arquitectura, contrato y ADRs.

## Fase 1 — Instalar y validar el entorno
Requisitos: Git, Python 3.11–3.13 y uv 0.13.4 o una versión compatible posterior. Trabajar desde la raíz del repositorio.
```bash
uv sync --frozen --extra dev
uv run --frozen pytest -q
uv run --frozen taxi --help
```
uv crea .venv y usa las dependencias resueltas en uv.lock.
No es necesario activar el entorno para ejecutar uv run.

Alternativa pip en macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```
Windows Git Bash: crear con py -3.12 -m venv .venv y activar con
source .venv/Scripts/activate. PowerShell: .venv\Scripts\Activate.ps1.
La alternativa pip fija dependencias directas; uv.lock también bloquea transitivas.
Usar uv para reproducir el entorno de CI.
Cierre: poder ejecutar la CLI y pasar las pruebas sin descargar datos TLC.

## Fase 2 — Entender el producto y la fuente
Leer el diccionario Yellow Taxi de TLC y docs/DATA_CONTRACT.md.
Consumidor: analista operativo. Grano Gold: mes + fecha + zona de recojo.
No confundir total_amount con beneficio. Los timestamps se conservan como hora
local sin zona. Anotar las implicaciones de datos faltantes y reembolsos.
Cierre: explicar cada métrica, su unidad y qué datos quedan fuera del producto.

## Fase 3 — Ejecutar una demo controlada
```bash
uv run --frozen taxi --root data_demo demo
uv run --frozen taxi --root data_demo status
uv run --frozen taxi --root data_demo verify
uv run --frozen taxi --root data_demo export
```
Esperado: raw=20, valid=19, rejected=1; una fila con importe negativo.
No usar el mismo root de datos reales porque la demo representa enero 2024.
Repetir demo: debe devolver skipped si no cambiaron bytes ni política.
Cierre: observar Bronze, warehouse, reportes y export en una carpeta aislada.

## Fase 4 — Procesar un mes real
```bash
uv run --frozen taxi run --month 2024-01
uv run --frozen taxi status
uv run --frozen taxi verify
```
Revisar HTTP timeout, reintentos, archivo .part, SHA y carpeta Bronze.
El manifest señala el snapshot publicado. El origen puede corregirse en el futuro;
el SHA explica exactamente qué bytes produjeron el resultado.
Se reacquiere la fuente en cada run para detectar revisiones. No hay ETag todavía.
Cierre: ejecutar dos veces y demostrar que la segunda no duplica Silver.

## Fase 5 — Estudiar contratos y fallos
Leer transform.py y ejecutar las pruebas de schema faltante, schema aditivo y
Quality gate. Las columnas extra se observan pero no se añaden automáticamente
a Silver. Un cambio semántico requiere incrementar MODEL_VERSION en config.py.
El fingerprint también incorpora max_reject_ratio; no depende de memoria/threads.

El 10% de rechazo es una política inicial, no una regla oficial. Se bloquean
archivos vacíos y archivos con 100% rechazados incluso si se configura umbral 1.
Un lote bloqueado deja diagnóstico agregado y bytes Bronze, pero no reemplaza
la cuarentena publicada del snapshot anterior.
Cierre: explicar un rechazo con datos, sin subir el umbral automáticamente.

## Fase 6 — Publicar y conciliar
Leer warehouse.py y sql/publish.sql. Observar BEGIN/COMMIT/ROLLBACK en pipeline.py.
Reemplazo por mes: Silver, cuarentena, Gold, manifest y auditoría de éxito comparten
transacción. La auditoría de fallo se agrega después del rollback.
Ejecutar la prueba de fallo inducido en reconcile: la publicación anterior permanece.
Revisar prueba de dos meses: corregir enero no modifica febrero.
Cierre: distinguir atomicidad del warehouse de la exportación externa.

## Fase 7 — Consumir las métricas
```bash
uv run --frozen taxi export
```
Consultar Gold con DuckDB o usar el snapshot Parquet en una herramienta de BI.
No promediar avg_ticket entre grupos: sumar montos y dividir entre viajes.
El export reemplaza un temporal en el mismo directorio; conserva el anterior si
falla antes de renombrar. No afirmar que export y warehouse comparten transacción.
Cierre: responder top zonas, evolución diaria y ticket ponderado con SQL.

## Fase 8 — Calidad de código y empaquetado
```bash
uv run --frozen ruff check src tests examples scripts
uv run --frozen ruff format --check src tests examples scripts
uv run --frozen pytest --cov --cov-fail-under=80 -q
uv build
```
CI ejecuta la misma validación en tres versiones de Python e instala el wheel
en otro entorno para comprobar que incluye los recursos SQL.
La evidencia local no equivale a un workflow remoto exitoso; revisar Actions.
Cierre: poder explicar qué invariantes cubren las pruebas y cuáles siguen pendientes.

## Fase 9 — Reproducir la evidencia visual
Después de publicar enero 2024:
```bash
uv run --frozen --extra analysis python scripts/generate_evidence.py
```
Genera docs/real_run.json y la figura del README usando únicamente agregados
calculados de la base real. Si no existen datos, falla; no inventa resultados.
Revisar cambios antes de hacer commit.
Cierre: tabla, figura y consulta deben coincidir.

## Fase 10 — Compartir el repositorio
Crear un repositorio sin archivos iniciales y usar:
```bash
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "feat: publish reproducible mobility data platform"
git remote add origin https://github.com/NeilBorjasRamos/nyc-mobility-data-platform.git
git push -u origin main
```
No ejecutar git init otra vez si ya hay repositorio. Si se usa otro nombre o
propietario, actualizar URLs y badge del README y project.urls de pyproject.toml.
Comprobar que data, .venv, bases y cobertura no se agregaron. Subir únicamente
evidencia agregada, documentación y código.

Para reclutadores: abrir README, explicar problema en 30 segundos, mostrar
arquitectura y demo, demostrar rollback, cerrar con límites y roadmap.
No atribuir tiempos de ahorro, costes reducidos ni servicios desplegados sin medirlos.

## Plan de cuatro semanas
| Semana | Trabajo | Evidencia de cierre |
|---|---|---|
| 1 | Entorno, diccionario, demo e ingesta real | Mes y SHA reproducibles |
| 2 | Calidad, modelo Gold y reconciliación | Rechazos explicados y totales iguales |
| 3 | Fallos, CI, wheel y recuperación | Pruebas verdes y runbook ejecutado |
| 4 | Dimensión de zonas o mejora HTTP; presentación | PR pequeño con aceptación verificable |

El código inicial está listo; este plan reserva tiempo para dominarlo y extenderlo.
Preguntas de dominio: ¿por qué reemplazar el mes?, ¿por qué no deduplicar por
valores?, ¿qué cubre la transacción?, ¿qué provoca reprocess?, ¿cómo restaurar
un backup?, ¿qué requisito justificaría Spark? Las respuestas están en los ADRs
y el runbook.
