"""
Archivo WSGI para deployment en PythonAnywhere.

Este archivo se usa cuando la app corre en un servidor web (no en local).
PythonAnywhere busca una variable llamada 'application'.
"""

import sys
import os

# Agregar la carpeta del proyecto al path
# IMPORTANTE: cambiar 'tutextil' por tu usuario de PythonAnywhere
project_home = '/home/tutextil/cuentas_corrientes'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Cambiar al directorio del proyecto
os.chdir(project_home)

# Importar la app de Flask
from app import app as application
