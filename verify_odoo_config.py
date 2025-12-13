#!/usr/bin/env python3
"""
Script para verificar la configuración de Odoo y sugerir soluciones.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("=" * 60)
print("VERIFICACIÓN DE CONFIGURACIÓN DE ODOO")
print("=" * 60)

# Variables requeridas
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USERNAME = os.getenv('ODOO_USERNAME')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

print("\n📋 Variables de entorno configuradas:")
print(f"   ODOO_URL: {ODOO_URL}")
print(f"   ODOO_DB: {ODOO_DB}")
print(f"   ODOO_USERNAME: {ODOO_USERNAME}")
print(f"   ODOO_PASSWORD: {'*' * len(ODOO_PASSWORD) if ODOO_PASSWORD else 'NO CONFIGURADO'}")

print("\n" + "=" * 60)
print("⚠️  PROBLEMA DETECTADO")
print("=" * 60)

print("""
El username actual es: {}

En Odoo, el campo 'username' debe ser el EMAIL/LOGIN del usuario, 
no el nombre de usuario.

Por ejemplo:
   ❌ INCORRECTO: 'admin' o 'Administrator'
   ✅ CORRECTO: 'admin@example.com' o 'tu.email@dominio.com'
""".format(ODOO_USERNAME))

print("=" * 60)
print("🔧 SOLUCIONES POSIBLES")
print("=" * 60)

print("""
1. VERIFICAR EL LOGIN EN ODOO:
   - Abre tu instancia de Odoo en el navegador
   - Ve a Configuración → Usuarios
   - Encuentra tu usuario y verifica el campo "Login" o "Email"
   - Ese es el valor que necesitas en ODOO_USERNAME

2. ACTUALIZAR EL .env:
   Edita el archivo .env y cambia ODOO_USERNAME por el email correcto:
   
   ODOO_USERNAME=tu_email@dominio.com

3. SI USAS ODOO 14+:
   Puedes generar una API Key:
   - Ve a tu perfil de usuario en Odoo
   - Busca la sección "API Keys" 
   - Genera una nueva API Key
   - Usa esa API Key en lugar de la contraseña

4. PROBAR DIFERENTES COMBINACIONES:
   Usuarios comunes en Odoo:
   - admin@yourcompany.com
   - admin@example.com
   - administrator@yourcompany.com
   - tu_nombre@kapi-vara.tech (si es tu dominio)
""")

print("=" * 60)
print("📝 PRÓXIMOS PASOS")
print("=" * 60)
print("""
1. Verifica el login correcto en tu instancia de Odoo
2. Actualiza el archivo .env con el email correcto
3. Ejecuta nuevamente: python test_odoo_connection.py
""")
