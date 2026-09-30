# Pruebas

`test_data_loader.py` verifica la carga CSV/JSON, búsqueda, recuperación de
parámetro, estados pendientes y errores de registro/archivo con fixtures
sintéticos en carpetas temporales. Los datos de prueba no son valores HCM.

Ejecutar desde la raíz del proyecto:

```powershell
.\env\Scripts\python.exe -m unittest discover -s tests -v
```
