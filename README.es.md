# NYC Mobility Data Platform
**Plataforma batch reproducible con Python, SQL, DuckDB y Parquet.**

[English README](README.md) · [Guía paso a paso](docs/GUIA_COMPLETA.md)

El proyecto resuelve un problema concreto: publicar métricas consistentes cuando
un archivo mensual cambia o una ejecución falla. Descarga snapshots de Yellow Taxi
de NYC TLC, conserva los bytes originales, valida registros y publica tablas
analíticas reconciliadas.

## Lo implementado
- Bronze inmutable por mes y SHA-256.
- Contrato de columnas, conversiones explícitas y cuarentena por motivo.
- Silver con trazabilidad al archivo y su fila física.
- Gold por fecha y zona de recojo.
- Reemplazo transaccional del mes, conciliación de filas e importes.
- Idempotencia por contenido y versión de reglas/configuración.
- CLI con JSON, auditoría, diagnósticos y exportación Parquet atómica.
- Pruebas offline, dependencias bloqueadas y CI configurado.

## Empezar
Con Python 3.11–3.13, Git y uv instalados:
```bash
git clone https://github.com/NeilBorjasRamos/nyc-mobility-data-platform.git
cd nyc-mobility-data-platform
uv sync --frozen --extra dev
uv run --frozen taxi --root data_demo demo
uv run --frozen pytest --cov -q
```
La demo contiene 20 filas sintéticas claramente identificadas.
Para procesar datos reales:
```bash
uv run --frozen taxi run --month 2024-01
uv run --frozen taxi status
uv run --frozen taxi verify
uv run --frozen taxi export
```

## Evidencia real
En enero 2024: 2,964,624 registros de origen, 2,926,173 aceptados y 38,451
en cuarentena según la política del proyecto. Silver y Gold conciliaron
USD 80,302,017.00. Las 28 pruebas pasan localmente con 93% de cobertura.
[Consultar evidencia y límites](docs/VALIDATION.md).

Los importes negativos pueden ser reembolsos legítimos; esta cuarentena define
un producto operativo y no demuestra errores oficiales. El monto bruto no es
beneficio ni ingreso neto.

## Cómo recorrerlo
1. Ejecutar la demo y consultar estado.
2. Leer [arquitectura](docs/ARCHITECTURE.md) y [contrato](docs/DATA_CONTRACT.md).
3. Procesar un mes real y repetirlo para observar skipped.
4. Ejecutar pruebas de fallos y revisar cómo se preserva el snapshot anterior.
5. Explorar [SQL de consumo](examples/analytics.sql) y el Parquet exportado.
6. Revisar [decisiones](docs/adr/), [runbook](docs/RUNBOOK.md) y [roadmap](docs/ROADMAP.md).

Es un data lake local más un warehouse analítico. Spark/Delta, Azure, dimensión
de zonas, orquestación remota y dashboard son ampliaciones pendientes.
Autor: [Neil Borjas Ramos](https://github.com/NeilBorjasRamos). Código MIT;
las condiciones de los datos corresponden a TLC.
