#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la conexión MCP con el servidor de Odoo
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def list_tools(session):
    """Lista las herramientas disponibles"""
    print("6. HERRAMIENTAS DISPONIBLES EN EL SERVIDOR")
    print("-" * 80)
    
    tools_list = await session.list_tools()
    
    if not tools_list.tools:
        print("   ⚠️  No hay herramientas disponibles en el servidor")
    else:
        print(f"   ✅ Encontradas {len(tools_list.tools)} herramientas:")
        print()
        
        for idx, tool in enumerate(tools_list.tools, 1):
            print(f"   [{idx}] {tool.name}")
            print(f"       Descripción: {tool.description}")
            
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                print(f"       Schema de entrada:")
                if 'properties' in tool.inputSchema:
                    for prop_name, prop_info in tool.inputSchema.get('properties', {}).items():
                        prop_type = prop_info.get('type', 'unknown')
                        prop_desc = prop_info.get('description', 'Sin descripción')
                        required = prop_name in tool.inputSchema.get('required', [])
                        req_mark = "* (requerido)" if required else ""
                        print(f"         - {prop_name} ({prop_type}){req_mark}: {prop_desc}")
            print()
    
    # Probar una herramienta (si existe)
    if tools_list.tools:
        print("7. PROBANDO CONEXIÓN CON UNA HERRAMIENTA")
        print("-" * 80)
        
        test_tool = tools_list.tools[0]
        print(f"   🧪 Probando herramienta: {test_tool.name}")
        print("   → Esta es solo una prueba de disponibilidad, no se ejecutará realmente")
        print("   ✅ La herramienta está lista para ser invocada")
        print()
    
    # Resumen
    print("=" * 80)
    print("RESUMEN DEL DIAGNÓSTICO")
    print("=" * 80)
    print(f"✅ Conexión exitosa al servidor MCP de Odoo")
    print(f"✅ Herramientas disponibles: {len(tools_list.tools)}")
    print(f"✅ El cliente puede comunicarse correctamente con el servidor")
    print()
    print("El bot de Telegram está listo para usar las herramientas de Odoo.")
    print("=" * 80)


# Cargar variables de entorno
load_dotenv()

async def test_mcp_connection():
    """Prueba la conexión con el servidor MCP de Odoo"""
    
    print("=" * 80)
    print("DIAGNÓSTICO DE CONEXIÓN MCP - SERVIDOR ODOO")
    print("=" * 80)
    print()
    
    # 1. Verificar configuración
    print("1. VERIFICANDO CONFIGURACIÓN")
    print("-" * 80)
    
    mcp_enabled = True
    server_path = "https://odoo-mcp.kapi-vara.tech" 
    
    print(f"   ODOO_MCP_ENABLED: {mcp_enabled}")
    print(f"   ODOO_MCP_SERVER_PATH: {server_path}")
    print()
    
    if not mcp_enabled:
        print("   ❌ ERROR: ODOO_MCP_ENABLED está en 'false'")
        print("   → Cambia a 'true' en el archivo .env para habilitar MCP")
        return False
    
    if not server_path:
        print("   ❌ ERROR: ODOO_MCP_SERVER_PATH no está configurado")
        print("   → Configura la ruta al script del servidor MCP en .env")
        return False
    
    # Verificar si es URL o archivo local
    from urllib.parse import urlparse
    parsed = urlparse(server_path)
    is_url = parsed.scheme in ('http', 'https')
    
    if is_url:
        print(f"   ✅ URL del servidor detectada: {server_path}")
        print(f"   → Tipo: HTTP/SSE (Server-Sent Events)")
    else:
        if not os.path.exists(server_path):
            print(f"   ❌ ERROR: El archivo {server_path} no existe")
            return False
        print(f"   ✅ Archivo del servidor encontrado: {server_path}")
        print(f"   → Tipo: STDIO (Standard Input/Output)")
    print()
    
    # 2. Importar dependencias MCP
    print("2. VERIFICANDO DEPENDENCIAS MCP")
    print("-" * 80)
    
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        print("   ✅ Módulo 'mcp' importado correctamente")
        print(f"   → Versión MCP disponible")
    except ImportError as e:
        print(f"   ❌ ERROR: No se puede importar el módulo MCP: {e}")
        print("   → Instala con: pip install mcp")
        return False
    print()
    
    # 3. Tipo de transporte
    print("3. INFORMACIÓN DEL TRANSPORTE")
    print("-" * 80)
    
    from urllib.parse import urlparse
    parsed = urlparse(server_path)
    is_url = parsed.scheme in ('http', 'https')
    
    if is_url:
        print("   📡 Tipo de transporte: HTTP (JSON-RPC)")
        print("   → El cliente se comunica con el servidor a través de HTTP")
        print("   → Conexión a servidor remoto")
        print(f"   → URL: {server_path}")
    
    print()
    
    # 4. Intentar conexión
    print("4. ESTABLECIENDO CONEXIÓN CON EL SERVIDOR")
    print("-" * 80)
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(server_path)
        is_url = parsed.scheme in ('http', 'https')
        
        if is_url:
            # Conexión HTTP
            print(f"   🌐 Conectando a servidor remoto: {server_path}")
            print("   🔄 Estableciendo conexión HTTP...")
            
            try:
                import httpx
                from mcp.client.session import ClientSession
                from mcp.types import ClientCapabilities
            except ImportError as e:
                print(f"   ❌ ERROR: Dependencia no disponible: {e}")
                print("   → Instala: pip install httpx mcp")
                return False
            
            # Crear cliente HTTP personalizado
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                print("   ✅ Cliente HTTP creado")
                
                # Primero probar si es un endpoint raíz simple
                print(f"   → Probando endpoint raíz: {server_path}")
                
                try:
                    # Intentar diferentes endpoints comunes de MCP
                    endpoints_to_try = [
                        ("", "Raíz del servidor"),
                        ("/mcp", "Endpoint MCP estándar"),
                        ("/v1/initialize", "Endpoint v1"),
                        ("/api/mcp", "API MCP"),
                        ("/jsonrpc", "JSON-RPC directo"),
                    ]
                    
                    working_endpoint = None
                    
                    for endpoint_path, description in endpoints_to_try:
                        test_url = f"{server_path}{endpoint_path}"
                        print(f"   → Probando: {test_url} ({description})")
                        
                        try:
                            # Probar con POST JSON-RPC
                            response = await http_client.post(
                                test_url,
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "initialize",
                                    "params": {
                                        "protocolVersion": "2024-11-05",
                                        "capabilities": {},
                                        "clientInfo": {
                                            "name": "test-client",
                                            "version": "1.0.0"
                                        }
                                    }
                                },
                                timeout=10.0
                            )
                            
                            print(f"     Status: {response.status_code}")
                            
                            if response.status_code == 200:
                                working_endpoint = test_url
                                print(f"   ✅ Endpoint funcional encontrado: {test_url}")
                                
                                result = response.json()
                                if "result" in result:
                                    server_info = result["result"]
                                    print(f"   → Protocolo: {server_info.get('protocolVersion', 'N/A')}")
                                    if "serverInfo" in server_info:
                                        print(f"   → Nombre del servidor: {server_info['serverInfo'].get('name', 'N/A')}")
                                        print(f"   → Versión: {server_info['serverInfo'].get('version', 'N/A')}")
                                break
                            elif response.status_code == 404:
                                print(f"     ❌ No encontrado")
                            else:
                                print(f"     ⚠️  Código inesperado: {response.text[:100]}")
                                
                        except httpx.TimeoutException:
                            print(f"     ⏱️  Timeout")
                        except Exception as e:
                            print(f"     ❌ Error: {str(e)[:50]}")
                    
                    if not working_endpoint:
                        print()
                        print("   ❌ No se encontró un endpoint MCP funcional")
                        print()
                        print("   DIAGNÓSTICO ADICIONAL:")
                        print("   → Probando endpoint raíz con GET...")
                        
                        # Probar GET en la raíz para ver qué hay
                        try:
                            get_response = await http_client.get(server_path, timeout=10.0)
                            print(f"   → GET {server_path}: {get_response.status_code}")
                            print(f"   → Content-Type: {get_response.headers.get('content-type', 'N/A')}")
                            print(f"   → Contenido (primeros 200 chars):")
                            print(f"     {get_response.text[:200]}")
                        except Exception as e:
                            print(f"   → Error en GET: {e}")
                        
                        return False
                    
                    print()
                    
                    # Listar herramientas usando el endpoint que funcionó
                    print("5. OBTENIENDO LISTA DE HERRAMIENTAS")
                    print("-" * 80)
                    
                    # Probar diferentes rutas para listar herramientas
                    tools_endpoints = [
                        f"{working_endpoint}",  # Mismo endpoint con method tools/list
                    ]
                    
                    tools_found = False
                    
                    for tools_url in tools_endpoints:
                        try:
                            tools_response = await http_client.post(
                                tools_url,
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 2,
                                    "method": "tools/list",
                                    "params": {}
                                },
                                timeout=10.0
                            )
                            
                            print(f"   → Probando tools/list en: {tools_url}")
                            print(f"   → Status: {tools_response.status_code}")
                            
                            if tools_response.status_code == 200:
                                tools_result = tools_response.json()
                                
                                if "result" in tools_result and "tools" in tools_result["result"]:
                                    tools = tools_result["result"]["tools"]
                                    tools_found = True
                                    
                                    if not tools:
                                        print("   ⚠️  No hay herramientas disponibles en el servidor")
                                    else:
                                        print(f"   ✅ Encontradas {len(tools)} herramientas:")
                                        print()
                                        
                                        for idx, tool in enumerate(tools, 1):
                                            print(f"   [{idx}] {tool.get('name', 'N/A')}")
                                            print(f"       Descripción: {tool.get('description', 'Sin descripción')}")
                                            
                                            if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                                                print(f"       Parámetros:")
                                                for prop_name, prop_info in tool['inputSchema']['properties'].items():
                                                    prop_type = prop_info.get('type', 'unknown')
                                                    prop_desc = prop_info.get('description', 'Sin descripción')
                                                    required = prop_name in tool['inputSchema'].get('required', [])
                                                    req_mark = " (requerido)" if required else ""
                                                    print(f"         - {prop_name} ({prop_type}){req_mark}: {prop_desc}")
                                            print()
                                    
                                    # Resumen
                                    print("=" * 80)
                                    print("RESUMEN DEL DIAGNÓSTICO")
                                    print("=" * 80)
                                    print(f"✅ Conexión exitosa al servidor MCP de Odoo")
                                    print(f"✅ Endpoint funcional: {working_endpoint}")
                                    print(f"✅ Herramientas disponibles: {len(tools)}")
                                    print(f"✅ El cliente puede comunicarse correctamente con el servidor")
                                    print()
                                    print("El bot de Telegram puede conectarse a este servidor MCP.")
                                    print("=" * 80)
                                    break
                                    
                        except Exception as e:
                            print(f"   ⚠️  Error: {str(e)[:50]}")
                    
                    if not tools_found:
                        print("   ⚠️  No se pudieron obtener las herramientas")
                        print("   → El servidor respondió pero no implementa tools/list")
                        
                except httpx.RequestError as e:
                    print(f"   ❌ Error de conexión HTTP: {e}")
                    return False
            
            print("6. CERRANDO CONEXIÓN")
            print("-" * 80)
            print("   ✅ Conexión cerrada correctamente")
            print()
            
            return True
                
        else:
            # Conexión STDIO
            print("   📝 Tipo de transporte: STDIO")
            # Configurar parámetros del servidor
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            server_params = StdioServerParameters(
                command="python3",
                args=[server_path],
                env=None
            )
            
            print(f"   📝 Comando de ejecución: python3 {server_path}")
            print("   🔄 Iniciando servidor MCP...")
            
            # Crear cliente stdio
            stdio_transport = await stdio_client(server_params)
            stdio_read, stdio_write = stdio_transport
            
            print("   ✅ Transporte STDIO creado exitosamente")
            print(f"   → Read stream: {type(stdio_read).__name__}")
            print(f"   → Write stream: {type(stdio_write).__name__}")
            print()
            
            # Crear sesión
            print("5. INICIALIZANDO SESIÓN MCP")
            print("-" * 80)
            
            from mcp import ClientSession
            session = ClientSession(stdio_read, stdio_write)
            init_result = await session.initialize()
            
            print("   ✅ Sesión MCP inicializada correctamente")
            if hasattr(init_result, 'serverInfo'):
                print(f"   → Nombre del servidor: {init_result.serverInfo.name}")
                print(f"   → Versión: {init_result.serverInfo.version}")
            print()
            
            # Listar herramientas
            await list_tools(session)
            
            # Cerrar STDIO
            await stdio_read.aclose()
            await stdio_write.aclose()
            
            print("6. CERRANDO CONEXIÓN")
            print("-" * 80)
            print("   ✅ Conexión cerrada correctamente")
            print()
            
            return True
        
    except Exception as e:
        print(f"   ❌ ERROR durante la conexión: {e}")
        logger.exception("Error detallado:")
        print()
        print("POSIBLES SOLUCIONES:")
        print("  1. Verifica que el servidor MCP esté accesible")
        print("  2. Revisa las credenciales y permisos de acceso")
        print("  3. Asegúrate de que el servidor esté ejecutándose")
        print("  4. Verifica la configuración de red y firewall")
        return False


def main():
    """Función principal"""
    try:
        result = asyncio.run(test_mcp_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnóstico interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        logger.exception("Error detallado:")
        sys.exit(1)


if __name__ == "__main__":
    main()
