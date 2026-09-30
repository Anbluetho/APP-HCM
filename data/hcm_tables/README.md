# Registro de tablas HCM 2000

`registry.json` es el catálogo de tablas conocidas por el cargador. Los 11 CSV originales recibidos se conservaron bajo `imported/` sin cambiar sus bytes originales. Se cotejaron contra `HCM_K20.pdf`, capítulo 20, suministrado por el usuario. Las tablas cotejadas están marcadas `primary_source_verified`; el resumen de expresiones se mantiene `reference_only` para impedir que se confunda con una implementación matemática. La presentación PUCE fue la procedencia secundaria del paquete CSV original. Para el módulo direccional de pendientes específicas se transcribieron nueve exhibits adicionales a `reviewed/` y se agregó una referencia JSON de fG para descensos.

`status: available` indica que el archivo es legible. `verification_status` registra el cotejo de la fuente por separado. Las tablas `primary_source_verified` se pueden cargar y consultar por defecto; el resumen de fórmulas `reference_only` requiere aprobación explícita para inspección y no se ejecuta.

## Metadatos por tabla

Cada tabla documenta nombre, fuente, referencia visible de capítulo/sección o
número de tabla, descripción, unidades, variables, versión, observaciones,
categoría, tipo de fuente, estado de disponibilidad, estado de verificación,
documento fuente y ruta de archivo. Las referencias por tabla apuntan al exhibit y a la página del manual; las huellas de origen están en el registro.

- CSV: encabezados en la primera fila; los valores de celda se devuelven como
  texto y deben convertirse explícitamente después de validar tipos/unidades.
- JSON: arreglo de objetos, o un objeto con propiedad `records`; conserva tipos
  JSON nativos.
- `variables`: nombres de columnas de los archivos incorporados.
- `units`: mapa por variable, incluida la unidad declarada o el formato textual
  de rangos/clasificaciones.

El cargador impide rutas que salgan de `data/hcm_tables/`.

## Resultado del cotejo con el manual

- Los criterios LOS de Exhibits 20-2 y 20-4 se cotejaron con PDF pp. 7-8 (páginas impresas 20-3 y 20-4).
- Exhibits 20-5 y 20-6: PDF p. 10 (impresa 20-6).
- Exhibits 20-7 y 20-8: PDF p. 11 (impresa 20-7).
- Exhibits 20-9 y 20-10: PDF p. 12 (impresa 20-8); las filas VR sí aparecen en el manual, aunque la presentación secundaria las tachaba.
- Exhibit 20-11: PDF p. 14 (impresa 20-10).
- Exhibit 20-12: PDF p. 15 (impresa 20-11). En la copia revisada se normalizaron etiquetas de flujo de la fila inicial como `<=200`, y las categorías finales impresas con ≥ se conservaron como rangos; `imported/` sigue intacto.
- Exhibits 20-13 a 20-17 (factores y equivalencias para ascensos específicos): PDF pp. 19-23 (impresas 20-15 a 20-19).
- Exhibit 20-18 (equivalencia ETC para camiones a velocidad de arrastre): PDF p. 24 (impresa 20-20).
- Exhibit 20-19 (ajuste ATS direccional por zonas de no rebase): PDF p. 25 (impresa 20-21).
- Exhibit 20-20 (ajuste PTSF direccional por zonas de no rebase): PDF p. 27 (impresa 20-23).
- Exhibit 20-21 (coeficientes de la ecuación PTSF direccional): PDF p. 28 (impresa 20-24).
- Capacidad: PDF p. 7 (impresa 20-3). La copia revisada incluye 1,700 pc/h por sentido, 3,200 pc/h combinado para segmentos extendidos y el rango de 3,200–3,400 pc/h combinado para tramos cortos (p. ej., túneles/puentes).
- El CSV de fórmulas se conserva como texto de referencia; no se interpreta ni ejecuta. Las ecuaciones definitivas y su flujo de cálculo requieren una fase de implementación y validación independiente.

El registro almacena el nombre y SHA-256 del PDF de capítulo, así como las referencias de páginas impresas y PDF. El documento completo no se copia al repositorio. El marcador pendiente recuerda que el conjunto de archivos recibido no cubre necesariamente todas las tablas/procedimientos del capítulo 20.
