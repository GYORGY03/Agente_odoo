#!/usr/bin/env python3
"""
Diagnóstico detallado de conexión a Odoo
"""

import os
import xmlrpc.client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")

print("=" * 80)
print("DIAGNÓSTICO DETALLADO DE CONEXIÓN ODOO")
print("=" * 80)
print()

print("1. CONFIGURACIÓN LEÍDA:")
print(f"   URL: {url}")
print(f"   DB: {db}")
print(f"   Usuario: {username}")
print(f"   Password: {'*' * len(password) if password else 'NO CONFIGURADO'}")
print()

# Test 1: Verificar acceso a la URL
print("2. PROBANDO ACCESO AL SERVIDOR:")
print(f"   → Intentando conectar a {url}...")
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    version = common.version()
    print(f"   ✅ Servidor alcanzable")
    print(f"   → Versión del servidor: {version.get('server_version')}")
    print(f"   → Serie: {version.get('server_serie')}")
    print(f"   → Protocol version: {version.get('protocol_version')}")
except Exception as e:
    print(f"   ❌ Error conectando al servidor: {e}")
    exit(1)

print()

# Test 2: Listar bases de datos disponibles
print("3. BASES DE DATOS DISPONIBLES:")
try:
    db_list = common.list()
    if db_list:
        print(f"   Bases de datos encontradas: {', '.join(db_list)}")
        if db in db_list:
            print(f"   ✅ La base de datos '{db}' existe")
        else:
            print(f"   ⚠️  ADVERTENCIA: La base de datos '{db}' NO está en la lista")
            print(f"   → Verifica el nombre exacto (case-sensitive)")
    else:
        print("   ⚠️  No se pudieron listar las bases de datos (puede ser normal en Odoo Online)")
except Exception as e:
    print(f"   ⚠️  No se puede listar bases de datos: {e}")
    print("   (Esto es normal en algunas configuraciones de Odoo)")

print()

# Test 3: Intentar autenticación con detalles
print("4. PROBANDO AUTENTICACIÓN:")
print(f"   → Intentando autenticar como '{username}' en base de datos '{db}'...")

try:
    uid = common.authenticate(db, username, password, {})
    
    if uid:
        print(f"   ✅ AUTENTICACIÓN EXITOSA!")
        print(f"   → User ID: {uid}")
        print()
        
        # Test 4: Verificar acceso a datos
        print("5. PROBANDO ACCESO A MODELOS:")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Verificar acceso al modelo de productos
        can_read = models.execute_kw(
            db, uid, password,
            'product.product', 'check_access_rights',
            ['read'], {'raise_exception': False}
        )
        print(f"   → Acceso de lectura a 'product.product': {'✅ Sí' if can_read else '❌ No'}")
        
        if can_read:
            # Intentar contar productos
            count = models.execute_kw(
                db, uid, password,
                'product.product', 'search_count',
                [[]]
            )
            print(f"   → Total de productos en el sistema: {count}")
            
            if count > 0:
                # Intentar leer 1 producto
                ids = models.execute_kw(
                    db, uid, password,
                    'product.product', 'search',
                    [[]], {'limit': 1}
                )
                
                if ids:
                    product = models.execute_kw(
                        db, uid, password,
                        'product.product', 'read',
                        [ids], {'fields': ['name', 'default_code']}
                    )
                    print(f"   → Producto de prueba leído: {product[0].get('name')} (ID: {ids[0]})")
            
        print()
        print("=" * 80)
        print("✅ DIAGNÓSTICO EXITOSO - La conexión funciona correctamente")
        print("=" * 80)
        
    else:
        print(f"   ❌ AUTENTICACIÓN FALLÓ - authenticate() retornó False")
        print()
        print("POSIBLES CAUSAS:")
        print("  1. Usuario o contraseña incorrectos")
        print("  2. El usuario no existe en esta base de datos")
        print("  3. El usuario está desactivado")
        print("  4. Necesitas usar una API Key en lugar de contraseña")
        print()
        print("SOLUCIONES:")
        print("  • Verifica el nombre de usuario (case-sensitive)")
        print("  • Verifica la contraseña")
        print("  • Si es Odoo Online, crea un API Key:")
        print("    1. Ve a Preferencias → Seguridad de la cuenta")
        print("    2. Crea una nueva API Key")
        print("    3. Usa esa key como password en .env")
        
except Exception as e:
    print(f"   ❌ ERROR durante autenticación: {e}")
    print()
    print("DETALLES DEL ERROR:")
    import traceback
    traceback.print_exc()
    print()
    print("POSIBLES CAUSAS:")
    print("  • Error de red o timeout")
    print("  • Servidor Odoo no responde")
    print("  • URL incorrecta")
    print("  • Base de datos no existe")
