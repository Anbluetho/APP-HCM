# Motor HCM 2000 — alcance y módulos

## Procedimiento implementado

Análisis operacional de un **segmento bidireccional extendido de carretera de dos carriles**, Capítulo 20 del HCM 2000. Calcula fLS/fA y FFS; ejecuta las dos rutas separadas de factores para velocidad media y PTSF; revisa los límites de capacidad y, si opera bajo capacidad, calcula ATS, PTSF, LOS y otras medidas del worksheet.

No incluye segmentos direccionales, rampas, pendientes específicas, carriles de rebase, análisis de diseño, ni planeamiento. Para segmentos menores que 3.0 km, el cálculo se detiene porque este módulo aplica el procedimiento de segmento bidireccional extendido; no sustituye el análisis de tramos cortos.

## Archivos

| Archivo | Entrada | Salida / responsabilidad | Fuente |
|---|---|---|---|
| `phf.py` | Volumen horario V y volumen de los 15 min pico V15 | PHF | Relación PHF del CSV de referencia suministrado. No se usa como PHF por defecto. |
| `heavy_vehicles.py` | % camiones/RV y equivalencias | fHV | Capítulo 20, Eq. 20-4; equivalencias Exhibits 20-9/20-10 |
| `flow.py` | V, PHF, fG, fHV | Flujo equivalente vp | Capítulo 20, Eq. 20-3 |
| `capacity.py` | vp de velocidad y PTSF, reparto, capacidades | v/c y condición de sobresaturación | Capacidad y criterios LOS F del capítulo 20 |
| `performance.py` | FFS, vp, fnp, PTSF y entradas de viaje | ATS, BPTSF, PTSF, vehículos-km y tiempo de viaje | Eq. 20-5, 20-6, 20-7 y worksheet/ejemplo del capítulo 20 |
| `los.py` | Clase, ATS, PTSF, filas de criterios | LOS A–F | Exhibits 20-2 y 20-4, obtenidos mediante el catálogo |
| `design_hour_volume.py` | TPDA, K3 y categoría direccional Exhibit 20-12 | VHD total y por sentido | Conversión local de demanda antes del HCM; VHD = TPDA×K3 y el reparto usa la única categoría seleccionada |
| `two_lane_highway.py` | `TwoLaneHighwayInputs` con VHD | `CalculationResult` trazable | Orquesta las funciones y carga parámetros verificados con `DataLoader` |
| `exceptions.py` | — | Errores de entrada, datos y cálculo | Mensajes explícitos; no sustituye valores faltantes |

Las estructuras de entrada y salida se definen en `models/two_lane_highway.py` y `models/calculation_result.py`. El motor no usa Streamlit.

## Entradas y límites de datos

La interfaz convierte TPDA y K3 a VHD mediante `calculate_design_hour_volume`; el reparto por sentido proviene exclusivamente de la categoría direccional de Exhibit 20-12. K3 es un dato de entrada del analista, no una tabla o factor HCM. `TwoLaneHighwayInputs` recibe ese VHD, PHF, la categoría de Exhibit 20-12, porcentajes separados de camiones y RV, terreno `level` o `rolling`, clase HCM I/II, longitud, anchos, densidad de accesos, zonas de no rebase y BFFS. Para pendiente específica, una selección mayor/menor identifica cuál parte de esa misma categoría corresponde a la dirección analizada. BFFS es criterio/dato del analista; HCM 2000 no da un valor por defecto general. Solo se aceptan categorías tabuladas 50/50 a 90/10, sin interpolar ni redondear el reparto.

Las tablas se leen por `DataLoader` desde `data/hcm_tables/`. El registro bloquea valores que no estén verificados. Se usa interpolación lineal en las Exhibits 20-11/20-12 entre celdas, contrastada con los Ejemplos 1 y 2. Para fA solo se admiten las categorías tabuladas (0, 6, 12, 18 y ≥24 accesos/km), sin extrapolar. El reparto principal se limita a los valores publicados en Exhibit 20-12 (50/50 a 90/10, en pasos de diez puntos). Entradas fuera del dominio producen un error; no se redondean o suponen silenciosamente.

## Ejecución y pruebas

Desde la raíz del proyecto:

```powershell
.\env\Scripts\python.exe -m unittest discover -s tests -v
```

Para usarlo en Python, construya `TwoLaneHighwayInputs` y llame `analyze_two_way_segment(inputs)`. La suite incluye verificaciones de cada función, validaciones y los dos ejemplos de cálculo publicados en el manual. Este motor aún no se conecta con `app.py`: el formulario actual no recopila todas las entradas específicas requeridas.
