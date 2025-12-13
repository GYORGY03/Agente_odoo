#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión XML-RPC con Odoo
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_odoo_connection():
    """Prueba la conexión con Odoo"""
    
    print("=" * 80)
    print("DIAGNÓSTICO DE CONEXIÓN ODOO XML-RPC")
    print("=" * 80)
    print()
    
    # 1. Verificar configuración
    print("1. VERIFICANDO CONFIGURACIÓN")
    print("-" * 80)
    
    enabled = os.getenv("ODOO_XMLRPC_ENABLED", "false").lower() == "true"
    url = os.getenv("ODOO_URL", "")
    db = os.getenv("ODOO_DB", "")
    username = os.getenv("ODOO_USERNAME", "")
    password = os.getenv("ODOO_PASSWORD", "")
    
    print(f"   ODOO_XMLRPC_ENABLED: {enabled}")
    print(f"   ODOO_URL: {url}")
    print(f"   ODOO_DB: {db}")
    print(f"   ODOO_USERNAME: {username}")
    print(f"   ODOO_PASSWORD: {'*' * len(password) if password else '(vacío)'}")
    print()
    
    if not enabled:
        print("   ❌ ODOO_XMLRPC_ENABLED está en 'false'")
        return False
    
    if not all([url, db, username, password]):
        print("   ❌ Faltan credenciales de Odoo")
        return False
    
    print("   ✅ Configuración completa")
    print()
    
    # 2. Probar conexión
    print("2. PROBANDO CONEXIÓN CON ODOO")
    print("-" * 80)
    
    try:
        from tools.odoo_xmlrpc_client import OdooXMLRPCClient
        
        print(f"   🔄 Conectando a {url}...")
        client = OdooXMLRPCClient(url, db, username, password)
        
        if client.connect():
            print(f"   ✅ Conexión exitosa!")
            print(f"   → UID: {client.uid}")
            print()
            
            # 3. Probar búsqueda de productos
            print("3. PROBANDO BÚSQUEDA DE PRODUCTOS")
            print("-" * 80)
            
            print("   🔍 Buscando productos en inventario...")
            products = client.get_products(limit=5)
            
            if products:
                print(f"   ✅ Se encontraron {len(products)} productos:")
                print()
                
                for idx, product in enumerate(products, 1):
                    print(f"   [{idx}] {product.get('name')} (ID: {product.get('id')})")
                    if product.get('default_code'):
                        print(f"       Ref: {product.get('default_code')}")
                    print(f"       Precio: ${product.get('list_price', 0):.2f}")
                    print(f"       Stock: {product.get('qty_available', 0)}")
                    print()
            else:
                print("   ⚠️  No se encontraron productos en el inventario")
                print()
            
            # 4. Probar herramientas de LangChain
            print("4. PROBANDO HERRAMIENTAS DE LANGCHAIN")
            print("-" * 80)
            
            try:
                from tools.odoo_xmlrpc_tools import create_odoo_xmlrpc_tools
                
                print("   🔧 Creando herramientas...")
                _, tools = create_odoo_xmlrpc_tools(url, db, username, password, auto_connect=False)
                
                print(f"   ✅ {len(tools)} herramientas creadas:")
                for tool in tools:
                    print(f"      - {tool.name}: {tool.description[:60]}...")
                print()
                
            except Exception as e:
                print(f"   ❌ Error creando herramientas: {e}")
                print()
            
            # Resumen
            print("=" * 80)
            print("RESUMEN")
            print("=" * 80)
            print("✅ Conexión exitosa a Odoo")
            print("✅ Cliente XML-RPC funcionando correctamente")
            print("✅ El bot está listo para usar herramientas de Odoo")
            print()
            print("Si el bot no carga las herramientas, verifica los logs de error.")
            print("=" * 80)
            
            return True
            
        else:
            print("   ❌ Error de conexión")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_odoo_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba interrumpida")
        sys.exit(1)
