"""
MCP Client for Odoo
Cliente para conectar con un servidor MCP de Odoo (soporta STDIO y HTTP/SSE)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from urllib.parse import urlparse

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
except ImportError:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    sse_client = None

logger = logging.getLogger(__name__)


class OdooMCPClient:
    """Cliente MCP para interactuar con servidor Odoo"""
    
    def __init__(self, server_path_or_url: str):
        """
        Inicializa el cliente MCP de Odoo
        
        Args:
            server_path_or_url: Ruta al script del servidor MCP (STDIO) o URL del servidor (HTTP/SSE)
        """
        if ClientSession is None:
            raise ImportError(
                "MCP SDK no está instalado. Instala con: pip install mcp"
            )
        
        self.server_path_or_url = server_path_or_url
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._stdio = None
        self._write = None
        self._is_http = self._check_if_http(server_path_or_url)
        
    def _check_if_http(self, path: str) -> bool:
        """Verifica si es una URL HTTP/HTTPS"""
        try:
            parsed = urlparse(path)
            return parsed.scheme in ('http', 'https')
        except:
            return False
        
    async def connect(self):
        """Conecta al servidor MCP de Odoo"""
        try:
            if self._is_http:
                logger.info(f"Conectando al servidor MCP de Odoo via HTTP/SSE: {self.server_path_or_url}")
                await self._connect_http()
            else:
                logger.info(f"Conectando al servidor MCP de Odoo via STDIO: {self.server_path_or_url}")
                await self._connect_stdio()
            
            # Listar herramientas disponibles
            tools_list = await self.session.list_tools()
            self.available_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_list.tools
            ]
            
            logger.info(f"Conectado exitosamente. Herramientas disponibles: {len(self.available_tools)}")
            for tool in self.available_tools:
                logger.info(f"  - {tool['name']}: {tool['description']}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error conectando al servidor MCP: {e}")
            raise
    
    async def _connect_stdio(self):
        """Conecta usando STDIO (proceso local)"""
        # Configurar parámetros del servidor
        server_params = StdioServerParameters(
            command="python3",
            args=[self.server_path_or_url],
            env=None
        )
        
        # Crear cliente stdio
        stdio_transport = await stdio_client(server_params)
        self._stdio, self._write = stdio_transport
        
        # Crear sesión
        self.session = ClientSession(self._stdio, self._write)
        await self.session.initialize()
    
    async def _connect_http(self):
        """Conecta usando HTTP/SSE (servidor remoto)"""
        if sse_client is None:
            raise ImportError("SSE client no disponible. Verifica la instalación de mcp")
        
        # Crear cliente SSE
        async with sse_client(self.server_path_or_url) as (read, write):
            self._stdio = read
            self._write = write
            
            # Crear sesión
            self.session = ClientSession(read, write)
            await self.session.initialize()
    
    async def disconnect(self):
        """Desconecta del servidor MCP"""
        if self.session:
            try:
                logger.info("Desconectando del servidor MCP de Odoo")
                # Cerrar la sesión y transporte
                if hasattr(self, '_stdio'):
                    await self._stdio.aclose()
                if hasattr(self, '_write'):
                    await self._write.aclose()
                self.session = None
                logger.info("Desconectado exitosamente")
            except Exception as e:
                logger.error(f"Error al desconectar: {e}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Retorna lista de herramientas disponibles"""
        return self.available_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Llama a una herramienta del servidor MCP
        
        Args:
            tool_name: Nombre de la herramienta
            arguments: Argumentos para la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        if not self.session:
            raise RuntimeError("Cliente no conectado. Llama a connect() primero.")
        
        try:
            logger.info(f"Llamando herramienta: {tool_name} con argumentos: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            logger.info(f"Resultado obtenido de {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error llamando herramienta {tool_name}: {e}")
            raise
    
    async def search_partners(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Busca partners/contactos en Odoo
        
        Args:
            query: Término de búsqueda
            limit: Límite de resultados
            
        Returns:
            Lista de partners encontrados
        """
        result = await self.call_tool("search_partners", {
            "query": query,
            "limit": limit
        })
        return result
    
    async def get_partner_info(self, partner_id: int) -> Dict:
        """
        Obtiene información detallada de un partner
        
        Args:
            partner_id: ID del partner
            
        Returns:
            Información del partner
        """
        result = await self.call_tool("get_partner_info", {
            "partner_id": partner_id
        })
        return result
    
    async def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Busca productos en Odoo
        
        Args:
            query: Término de búsqueda
            limit: Límite de resultados
            
        Returns:
            Lista de productos encontrados
        """
        result = await self.call_tool("search_products", {
            "query": query,
            "limit": limit
        })
        return result
    
    async def get_sales_orders(self, partner_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """
        Obtiene órdenes de venta
        
        Args:
            partner_id: ID del partner (opcional)
            limit: Límite de resultados
            
        Returns:
            Lista de órdenes de venta
        """
        args = {"limit": limit}
        if partner_id:
            args["partner_id"] = partner_id
            
        result = await self.call_tool("get_sales_orders", args)
        return result
    
    @asynccontextmanager
    async def session_context(self):
        """Context manager para manejar la sesión automáticamente"""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()


# Función auxiliar para usar el cliente de forma sincrónica
def create_odoo_tools_sync(server_script_path: str) -> List[Dict[str, Any]]:
    """
    Crea herramientas de Odoo de forma sincrónica
    
    Args:
        server_script_path: Ruta al script del servidor MCP
        
    Returns:
        Lista de herramientas disponibles
    """
    async def _get_tools():
        client = OdooMCPClient(server_script_path)
        async with client.session_context():
            return client.get_available_tools()
    
    return asyncio.run(_get_tools())
