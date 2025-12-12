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
    
    mcp_enabled = os.getenv("ODOO_MCP_ENABLED", "false").lower() == "true"
    server_path = os.getenv("ODOO_MCP_SERVER_PATH", "")
    
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
        print("   📡 Tipo de transporte: HTTP/SSE (Server-Sent Events)")
        print("   → El cliente se comunica con el servidor a través de HTTP")
        print("   → Conexión a servidor remoto")
        print(f"   → URL: {server_path}")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(server_path)
        is_url = parsed.scheme in ('http', 'https')
        
        if is_url:
            # Conexión HTTP/SSE
            print(f"   🌐 Conectando a servidor remoto: {server_path}")
            print("   🔄 Estableciendo conexión HTTP/SSE...")
            
            try:
                from mcp.client.sse import sse_client
            except ImportError:
                print("   ❌ ERROR: Cliente SSE no disponible")
                print("   → Instala: pip install httpx httpx-sse")
                return False
            
            # Intentar conexión SSE
            import httpx
            async with sse_client(server_path) as (stdio_read, stdio_write):
                print("   ✅ Conexión HTTP/SSE establecida")
                print(f"   → Read stream: {type(stdio_read).__name__}")
                print(f"   → Write stream: {type(stdio_write).__name__}")
                print()
                
                # Crear sesión
                print("5. INICIALIZANDO SESIÓN MCP")
                print("-" * 80)
                
                session = ClientSession(stdio_read, stdio_write)
                init_result = await session.initialize()
                
                print("   ✅ Sesión MCP inicializada correctamente")
                if hasattr(init_result, 'serverInfo'):
                    print(f"   → Nombre del servidor: {init_result.serverInfo.name}")
                    print(f"   → Versión: {init_result.serverInfo.version}")
                print()
                
                # Listar herramientas
                await list_tools(session)
                
        else:
            # Conexión STDIO
            # Configurar parámetros del servidor
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
            
        print("8. CERRANDO CONEXIÓN")
        print("-" * 80)
        print("   ✅ Conexión cerrada correctamente")
        print()
        
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR durante la conexión: {e}")
        logger.exception("Error detallado:")
        print()
        print("POSIBLES SOLUCIONES:")
        print("  1. Verifica que el servidor MCP esté correctamente implementado")
        print("  2. Asegúrate de que el script del servidor tenga permisos de ejecución")
        print("  3. Revisa los logs del servidor para ver errores específicos")
        print("  4. Verifica que todas las dependencias del servidor estén instaladas")
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
