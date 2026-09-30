# Capacidad vial y LOS — HCM 2000

Aplicación académica en Python y Streamlit para capturar datos de proyectos de
Ingeniería Civil y preparar la implementación modular de procedimientos
validados del *Highway Capacity Manual 2000*.

## Estado del proyecto

- **Fase 1 — interfaz inicial:** recoge datos generales para una carretera de
  dos carriles, muestra validaciones básicas y entrega campos en una estructura
  agrupada. No calcula capacidad, relación v/c ni nivel de servicio.
- **Fase 2 — base de datos y tablas:** está implementado el catálogo y cargador CSV/JSON. Se importaron 11 CSV y se cotejaron sus tablas contra el capítulo 20 del manual HCM 2000 suministrado.
- **Fase 3 — motor matemático:** implementado, independiente de Streamlit,
  únicamente para el análisis operacional de segmentos bidireccionales
  extendidos de carreteras de dos carriles del capítulo 20.
- **Fase 4 — integración:** formulario, validación, verificación de tablas,
  ejecución del motor y presentación de resultados están conectados. Se
  conservan los límites del procedimiento de la Fase 3.
- **Fase 5 — presentación:** resultados en nueve secciones, LOS neutral,
  descarga CSV y paquete de datos independiente de formato preparado para un
  futuro informe PDF.
- **Alcance multicarril:** se añadió selección y cálculo de segmento general
  multicarril con tablas transcritas del PDF académico aportado. La procedencia
  de estas tablas es secundaria y queda visible; falta cotejo independiente con
  los exhibits del HCM 2000 original.
- **Pendiente específica de dos carriles:** se incorporó una ruta direccional
  separada para ascensos/descensos de al menos 3 %, respaldada por Exhibits
  20-13 a 20-21 del capítulo 20. El motor bidireccional existente se conserva.
  La ruta requiere datos medidos por sentido; no realiza conversión TPDA/K30.

El formulario diferencia los procedimientos de dos carriles y multicarril.
Otros tipos de instalaciones continúan fuera del alcance.

## Arquitectura

```text
.
├── app.py                         # Orquesta la interfaz Streamlit
├── calculations/                  # Funciones puras del procedimiento HCM
├── data/
│   ├── data_loader.py             # Carga, búsqueda, lookup y validación de tablas
│   ├── procedure_verification.py  # Verifica las tablas requeridas antes del cálculo
│   ├── data_dictionary.md         # Diccionario de entradas de la interfaz
│   ├── hcm_tables/
│   │   ├── registry.json         # Metadatos y estado de cada tabla
│   │   ├── imported/             # CSV originales recibidos sin cambios
│   │   ├── reviewed/             # Copias canónicas documentadas
│   │   └── README.md
│   ├── configuration/             # Configuración metodológica/jurisdiccional
│   └── source_docs/                # PDFs de referencia aportados
├── models/
│   ├── adapters.py                # Mapea el formulario a las entradas del motor
│   ├── calculation_result.py      # Resultado auditable del análisis
│   └── two_lane_highway.py        # Entradas del procedimiento HCM
│   ├── input_data.py              # Tipos de la estructura de entrada
│   ├── provenance.py              # Categorías del origen de datos
│   └── validation.py              # Validaciones generales del formulario
├── ui/                            # Formularios, resultados y advertencias
├── tests/
│   ├── test_data_loader.py        # Pruebas del catálogo y cargador
│   └── test_hcm_calculations.py   # Ecuaciones y ejemplos del manual
├── requirements.txt
└── README.md
```

## Capa de datos

`data/data_loader.py` ofrece `DataLoader` para:

- listar definiciones disponibles y pendientes;
- consultar metadatos por identificador;
- cargar archivos CSV o JSON;
- buscar registros con criterios exactos;
- recuperar un parámetro de un registro único;
- validar tablas y todas las tablas disponibles.

Errores específicos informan cuando una tabla no existe, sigue pendiente, no se
puede leer, no tiene registros, faltan criterios o una búsqueda sería ambigua.
Las rutas registradas deben permanecer dentro de `data/hcm_tables/`.

### Metadatos requeridos por tabla

Cada entrada del `data/hcm_tables/registry.json` debe incluir nombre, fuente,
capítulo/sección, descripción, unidades, variables, versión, observaciones,
identificador, estado y archivo. El estado `pending` indica que todavía no hay
una tabla utilizable. Solo las entradas `available` cargan sus archivos.

Los CSV se devuelven con valores de celda como texto; las conversiones de tipos
deben hacerse de forma explícita después de revisar unidades. JSON conserva los
tipos nativos JSON.

### Estado de las tablas importadas

Los originales están en `data/hcm_tables/imported/`; las copias con correcciones de transcripción justificadas por el manual están en `reviewed/`. El registro distingue la fuente primaria, el archivo, los exhibits/páginas, el estado de verificación y las huellas SHA-256. El archivo de fórmulas es solo referencia; las funciones matemáticas todavía no se han implementado. No hay parámetros de Ecuador.

### Agregar una tabla verificada

1. Verifica en la fuente autorizada la edición, capítulo/sección, número de tabla, valores, unidades, variables y condiciones de aplicación.
2. Guarda la tabla revisada como CSV o JSON bajo `data/hcm_tables/`.
3. Agrega una entrada al `registry.json` con `status: "available"`, su ruta
   relativa y todos los metadatos documentales requeridos.
4. Actualiza `data/data_dictionary.md` si aparecen variables nuevas. Mantén los
   parámetros de Ecuador en `data/configuration/`, separados de tablas HCM.
5. Valida con `DataLoader.validate_table("id_de_tabla")` y añade un caso de
   prueba para la estructura/lookup, sin duplicar valores tabulados en el motor.

El motor futuro solicitará datos al cargador mediante `get_parameter()` o
`search_records()`; incorporar una tabla no requiere modificar ecuaciones ni
funciones matemáticas.

## Ejecución en Windows

Se recomienda Python 3.10 o superior. Desde PowerShell, en la carpeta del
proyecto:

```powershell
python -m venv env
.\env\Scripts\python.exe -m pip install -r requirements.txt
.\env\Scripts\python.exe -m streamlit run app.py
```

En VS Code selecciona `env\Scripts\python.exe` como intérprete. La carpeta
`env` contiene el entorno virtual local y no forma parte de los archivos fuente
que se envían a GitHub.

## Pruebas

Las pruebas del cargador usan registros sintéticos; las pruebas del motor
reproducen ejemplos publicados del capítulo 20. Ejecuta desde la raíz:

```powershell
.\env\Scripts\python.exe -m unittest discover -s tests -v
```

## Trazabilidad metodológica

- No incorporar factores, umbrales, tablas ni ecuaciones sin referencia
  verificable del HCM 2000 y revisión de sus condiciones de aplicación.
- Separar datos ingresados por el usuario, metodología HCM, parámetros de
  Ecuador y resultados calculados.
- Mantener unidades y metadatos de fuente junto a cada tabla, nunca dentro de
  las funciones de cálculo.

### Pendiente específica direccional

Al seleccionar **Pendiente específica**, la aplicación utiliza el motor
`calculations/specific_grade/` y el modelo `models/specific_grade.py`. Las
entradas son volumen horario observado por sentido, PHF, composición vehicular
por sentido, pendiente y longitud de pendiente (independiente de la longitud
total del tramo), clase HCM, geometría y zonas de no rebase. Se acepta 3 % o
mayor; para ascensos el análisis específico es aplicable desde 0,4 km y es
requerido desde 1,0 km; los descensos específicos requieren al menos 1,0 km.

La demanda direccional de ATS y PTSF se calcula por ramas distintas y cada una
converge iterativamente a su propia banda tabulada. Se usan los Exhibits 20-13
a 20-21 y, para la condición de camiones a velocidad de arrastre, el Exhibit
20-18 y la ecuación 20-14. El equipo debe ingresar la proporción de camiones a
arrastre, su velocidad de arrastre y, cuando el sentido descendente es el
opuesto al analizado, la BFFS de ese sentido; si faltan, la aplicación detiene
el cálculo con el campo requerido.

La capacidad direccional (1.700 pc/h por sentido) se recupera del registro
documentado de capacidad de dos carriles. El cálculo direccional no usa la
capacidad bidireccional de 3.200 pc/h ni K30. Los archivos CSV de los Exhibits
20-13 a 20-21 se encuentran en `data/hcm_tables/reviewed/`; su procedencia,
unidades, página fuente y revisión se registran en `registry.json`. El Exhibit
20-18 no es un factor genérico: solo se consulta cuando se declara la condición
de arrastre.

`SpecificGradeAnalyzer` no sustituye ni cambia `TwoLaneHighwayAnalyzer`. La
ruta general terreno nivel/ondulado continúa llamando al motor original; los
resultados de pendiente específica se muestran en una vista separada.

## Motor de cálculo HCM 2000

El procedimiento de dos carriles cubre el análisis operacional de segmento
bidireccional extendido. Usa tablas cotejadas del capítulo 20 y calcula ATS,
PTSF, LOS y medidas adicionales del worksheet. El módulo multicarril agregado
se documenta por separado abajo y usa una transcripción secundaria aún
pendiente de cotejo. Ninguno usa parámetros de Ecuador.

El formulario ahora recoge las entradas requeridas para el motor. Los valores
PHF, clase y terreno no tienen valores predeterminados; deben ser suministrados
por el usuario. Este ejemplo también permite ejecutar el cálculo directamente,
sin interfaz:

```python
from calculations.two_lane_highway import analyze_two_way_segment
from models.two_lane_highway import TwoLaneHighwayInputs

inputs = TwoLaneHighwayInputs(
    hourly_volume_veh_per_h=1600, peak_hour_factor=0.95,
    major_direction_percent=50, trucks_percent=14,
    recreational_vehicles_percent=4, terrain="rolling", highway_class="I",
    segment_length_km=10, lane_width_m=3.4, shoulder_width_m=1.2,
    access_points_per_km=12, no_passing_zones_percent=50,
    base_free_flow_speed_km_per_h=100,
)
result = analyze_two_way_segment(inputs)
print(result.final_results)
```

Las pruebas comparan los resultados con los Ejemplos 1 y 2 del capítulo 20.
La interpolación lineal de Exhibits 20-11 y 20-12 se contrasta con esos
ejemplos. PHF se entrega al análisis integrado como entrada; su función
auxiliar está separada porque la fuente primaria de su definición en capítulo
12 no está en los documentos cotejados. Las ecuaciones no disponibles y las
entradas fuera del dominio tabulado detienen el cálculo con error claro.

### Segmento general multicarril

La aplicación ofrece también el procedimiento de segmento general multicarril
resumido en `data/source_docs/C05-C07-Capacidad_2.pdf`. Sus Tablas 14-19 se
transcribieron a `data/hcm_tables/reviewed/multilane_design_tables.json`; los
metadatos declaran su origen secundario y la necesidad de cotejo contra el HCM
original. El informe de cálculo conserva esa advertencia.

El formulario solicita carriles por sentido, ancho de carril, despeje lateral,
tipo de mediana, demanda horaria, PHF, distribución direccional, composición
vehicular, terreno, densidad de accesos, BFFS y fP. La velocidad operacional
entre puntos tabulados se interpola linealmente, usando el quiebre y criterios
del documento. El cálculo se limita a dos o tres carriles por sentido, FFS de
70 a 100 km/h y los dominios de las tablas transcritas. “Escarpado” está en el
selector, pero informa que no puede calcularse hasta incorporar la tabla de
equivalencias faltante. El procedimiento de dos carriles conserva capítulo 20
y permite terreno plano/nivel u ondulado.

