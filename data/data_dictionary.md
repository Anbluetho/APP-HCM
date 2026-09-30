# Diccionario de datos de la interfaz

Este diccionario cubre las variables de entrada que actualmente devuelve la
interfaz. Son datos ingresados por el usuario, **no una afirmación de que todos
sean requisitos de un procedimiento HCM 2000**. La correspondencia metodológica,
las unidades finales y los requisitos deben revisarse al seleccionar el
procedimiento exacto.

| Clave de la estructura | Variable | Descripción | Unidad/formato | Fuente y estado |
|---|---|---|---|---|
| `project.project_name` | Nombre del proyecto | Identificación académica del análisis. | Texto | Usuario; obligatorio en la interfaz. |
| `project.analyst` | Responsable | Persona responsable del registro. | Texto | Usuario; opcional. |
| `project.location` | Ubicación del tramo | Localización del segmento estudiado. | Texto | Usuario; obligatorio en la interfaz. |
| `project.data_origin` | Origen principal | Categoría declarada para el origen de los datos de campo. | Categoría de interfaz | Usuario; no modifica factores HCM. |
| `facility.facility_type` | Tipo de instalación | Carretera de dos carriles o carretera multicarril. | Categoría | Selecciona el procedimiento y conjunto de entradas correspondiente. |
| `geometry.segment_length_km` | Longitud del tramo | Longitud reportada para el segmento. | km | Obligatoria para dos carriles; no requerida por el formulario multicarril actual. |
| `geometry.lane_width_m` | Ancho de carril | Ancho reportado del carril. | m | Usuario; requerida en ambos procedimientos; límites dependen de la tabla. |
| `geometry.shoulder_width_m` | Ancho de berma | Ancho reportado de berma. | m | Usuario; requerida para dos carriles; multicarril usa despeje lateral total. |
| `traffic.hourly_volume_two_way_veh_per_h` | Volumen horario total | Volumen total de ambos sentidos ingresado por el usuario. | vehículos/h | Entrada de Eq. 20-3 para el segmento bidireccional; debe ser positiva. |
| `traffic.peak_hour_factor` | Factor de hora pico | PHF suministrado por el usuario. | Adimensional, (0,1] | Entrada explícita; no se asigna valor por defecto. |
| `traffic.major_direction_percent` | Distribución direccional | Porcentaje del sentido de mayor flujo. | % tabulado: 50, 60, 70, 80, 90 | Entrada para Exhibit 20-12; limitada a los repartos publicados. |
| `traffic.trucks_percent`, `traffic.recreational_vehicles_percent` | Proporciones de camiones/buses y RV | Porcentajes observados, capturados separadamente. | % (suma ≤100) | Entradas para Eq. 20-4; equivalencias se consultan en Exhibits 20-9/20-10. |
| `operation.terrain` | Terreno | Plano, ondulado, montañoso o escarpado. | Categoría | Para dos carriles, plano/nivel u ondulado tienen tablas; para multicarril, plano, ondulado y montañoso aparecen en Tabla 19 del PDF secundario. Escarpado queda sin calcular por falta de equivalencias. |
| `operation.highway_class` | Clase HCM | Clase I, II o III. | Categoría | La interfaz reconoce las tres definiciones; el cálculo actual admite I/II. Clase III requiere el criterio PFFS del HCM 2000, aún pendiente de incorporar/verificar. |
| `operation.observed_speed_km_per_h`, `operation.observed_travel_time_min` | Observaciones de operación | Velocidad/tiempo medidos que se conservan en el registro. | km/h; min | Opcionales; no se usan en la estimación de este procedimiento. |
| `procedure_additional.access_points_per_km` | Densidad de accesos | Accesos por kilómetro. | accesos/km | Entrada de Exhibit 20-6; categorías deben estar en el dominio tabulado. |
| `procedure_additional.no_passing_zones_percent` | Zonas de no rebase | Porción del tramo con no rebase. | % (0–100) | Entrada a Exhibits 20-11/20-12. |
| `procedure_additional.base_free_flow_speed_km_per_h` | BFFS | Velocidad base a flujo libre suministrada por el analista. | km/h | Dato de entrada de Eq. 20-2; sin default HCM general. |
| `procedure_additional.field_notes` | Observaciones de campo | Notas cualitativas del levantamiento. | Texto | Opcional; no es entrada numérica HCM. |
| `geometry.lanes_per_direction` | Carriles por sentido | Número de carriles disponibles por sentido en una carretera multicarril. | carriles/sentido | Documento secundario proporcionado, Tabla 16; rango disponible: 2 o 3. |
| `geometry.lateral_clearance_m` | Despeje lateral total | Separación lateral disponible en el sentido analizado. | m | Documento secundario proporcionado, Tabla 16; 0 a 3,6 m. |
| `geometry.median_type` | Tipo de mediana | Vía dividida o no dividida. | Categoría | Documento secundario proporcionado, Tabla 17. |
| `procedure_additional.driver_population_factor` | Factor de población conductora | Ajuste por familiaridad/uso habitual o recreacional. | adimensional | Dato explícito del usuario conforme al rango categórico descrito en el PDF secundario. |

## Entradas del motor independiente

Estas entradas pertenecen a `models/two_lane_highway.py` y se requieren cuando
se selecciona carretera de dos carriles. La aplicación también tiene el modelo
multicarril, descrito a continuación.

| Campo | Descripción | Unidad/formato | Fuente/estado |
|---|---|---|---|
| `hourly_volume_veh_per_h` | Volumen horario bidireccional | veh/h | Usuario; Capítulo 20, procedimiento dos sentidos |
| `peak_hour_factor` | Factor de hora pico | adimensional, (0,1] | PHF explícito del analista; no se asigna valor por defecto |
| `major_direction_percent` | Porcentaje del sentido de mayor flujo | %: 50, 60, 70, 80 o 90 | Usuario; categorías disponibles en Exhibit 20-12 |
| `trucks_percent`, `recreational_vehicles_percent` | Proporción de camiones/buses y RV | % independiente, suma ≤100 | Usuario; equivalencias separadas para ATS y PTSF en Exhibits 20-9/20-10 |
| `terrain` | Terreno | `level` o `rolling` | Usuario; categorías del procedimiento de segmento extendido |
| `highway_class` | Clase de carretera para criterio LOS | I o II | Usuario; Exhibit 20-2/20-4 |
| `segment_length_km` | Longitud del tramo | km, ≥3.0 en este motor | Usuario; el método se aplica típicamente a tramos de al menos 3 km |
| `lane_width_m`, `shoulder_width_m` | Anchos de carril y berma | m | Usuario; rangos de Exhibit 20-5 |
| `access_points_per_km` | Densidad de accesos | accesos/km | Usuario; categorías exactas de Exhibit 20-6 |
| `no_passing_zones_percent` | Porción del segmento con zona de no rebase | % (0–100) | Usuario; Exhibits 20-11/20-12 |
| `base_free_flow_speed_km_per_h` | BFFS para estimación de FFS | km/h | Dato/criterio del analista; HCM 2000 no proporciona default general |

## Entradas específicas multicarril

El modelo `models/multilane_highway.py` y el formulario multicarril solicitan
las siguientes variables. Las tablas se encuentran externamente en
`data/hcm_tables/reviewed/multilane_design_tables.json` y su procedencia se
marca como secundaria pendiente de cotejo con el manual original.

| Campo | Descripción | Unidad/formato | Fuente/estado |
|---|---|---|---|
| `lanes_per_direction` | Carriles por sentido | 2 o 3 | PDF académico proporcionado, Tabla 16 |
| `lane_width_m` | Ancho de carril | 3,0–3,6 m | PDF académico proporcionado, Tabla 15 |
| `lateral_clearance_m` | Despeje lateral total | 0–3,6 m | PDF académico proporcionado, Tabla 16 |
| `median_type` | Vía dividida/no dividida | Categoría | PDF académico proporcionado, Tabla 17 |
| `terrain` | Plano, ondulado o montañoso | Categoría | PDF académico proporcionado, Tabla 19; escarpado no tiene equivalencias |
| `driver_population_factor` | fP | 0,85; 0,90; 0,95; 1,00 | Selección explícita del usuario dentro de opciones descritas en el PDF |
| Volumen, PHF, DIR, % camiones/RV, accesos y BFFS | Demanda y entorno operacional | Unidades del formulario | Se combinan con factores y criterios tabulados |

La función auxiliar PHF acepta V y el conteo de vehículos del intervalo de 15
minutos pico y aplica la relación registrada en el CSV de fórmulas de referencia.
El analizador principal, sin embargo, recibe PHF explícito: la fuente primaria
para su definición del capítulo 12 no está incluida en el paquete documental.

## Convenciones

- `geometry`, `traffic`, `operation` y `procedure_additional` son grupos del
  contrato de entrada definido en `models/input_data.py`.
- Los nombres en español son etiquetas de interfaz; las claves en código son
  identificadores estables para el motor futuro.
- Los CSV se cargan como texto; toda conversión posterior debe ser explícita y
  coherente con las unidades verificadas en los metadatos de la tabla.

## Variables de las tablas importadas

Estos nombres describen columnas copiadas de los CSV del usuario. Las columnas se documentan por archivo. Las tablas cotejadas con el capítulo 20 tienen `primary_source_verified`; la hoja de fórmulas sigue `reference_only` y no se ejecuta. Las tablas multicarril del JSON tienen estado secundario y se documentan por separado.

| Variable/columna | Descripción en el CSV | Unidad/formato según encabezado o presentación | Estado |
|---|---|---|---|
| `highway_class` | Clase de carretera indicada en criterios LOS. | Categoría textual. | Cotejado con Exhibit 20-2 / 20-4; criterios por clase. |
| `LOS` | Letra del nivel de servicio. | Categoría A-F. | Cotejado con Exhibits 20-2 / 20-4. |
| `PTSF_percent` | Umbral/intervalo PTSF. | Porcentaje o rango textual. | Cotejado con Exhibits 20-2 / 20-4. |
| `ATS_kmh` | Umbral/intervalo ATS. | km/h o rango textual. | Cotejado con Exhibit 20-2. |
| `lane_width_m_range`, `shoulder_width_m_range` | Rangos de ancho de carril y berma. | m; expresados como texto de rango. | Cotejado con Exhibit 20-5. |
| `fLS_reduction_kmh`, `fA_reduction_kmh`, `fnp_reduction_kmh` | Reducciones de velocidad rotuladas en los archivos. | km/h. | Cotejado con Exhibits 20-5, 20-6 y 20-11; columna conserva valores tabulados. |
| `access_points_per_km` | Densidad de puntos de acceso. | puntos/km. | Cotejado con Exhibit 20-6. |
| `two_way_flow_pcph_range`, `directional_flow_pcph_range`, `vp_pcph` | Rangos o valores de flujo en los CSV. | pc/h; algunos rangos se conservan como texto. | Cotejado con Exhibits 20-7 a 20-12; rangos y etiquetas según el exhibit citado en el registro. |
| `terrain` | Tipo de terreno de las filas. | Etiqueta textual. | Etiquetas Level/Rolling del manual; traducidas en CSV como Plano/Ondulado o Nivel/Ondulado según tabla. |
| `fG` | Factor rotulado fG. | Adimensional. | Cotejado con Exhibits 20-7 / 20-8. |
| `vehicle_type`, `equivalent` | Clase de vehículo y equivalente tabulado. | Categoría y adimensional. | Cotejado con Exhibits 20-9 / 20-10; incluye VR según manual. |
| `directional_split`, `no_passing_zones_pct` | Distribución direccional y porcentaje de zonas de no rebase. | Porcentajes/etiquetas textuales. | Cotejado con Exhibit 20-12. |
| `fd_np_increment_ptsf_pct` | Incremento PTSF. | % PTSF. | Cotejado con Exhibit 20-12; etiquetas de rango normalizadas en reviewed/. |
| `capacity_type`, `capacity`, `unit` | Tipo, cifra y unidad de capacidad del resumen. | Categoría, texto y unidad declarada. | Cotejado con capacidad del capítulo 20; reviewed/ incluye condición de tramos cortos. |
| `formula_id`, `expression`, `description`, `unit` | Resumen textual de fórmulas del PDF. | Texto. | Texto cotejado como referencia de ecuaciones; no es ejecutable ni habilita el motor de cálculo. |

La fuente primaria `HCM_K20.pdf` fue cotejada: las referencias a capítulo, exhibit y página del manual aparecen en `data/hcm_tables/registry.json`. Los valores de Ecuador siguen pendientes y separados de las tablas HCM.
