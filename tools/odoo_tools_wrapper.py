"""
Wrapper para convertir las herramientas MCP de Odoo en herramientas de LangChain
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .mcp_odoo_client import OdooMCPClient

logger = logging.getLogger(__name__)


class SearchPartnersInput(BaseModel):
    """Input para búsqueda de partners"""
    query: str = Field(description="Término de búsqueda para partners/contactos")
    limit: int = Field(default=10, description="Límite de resultados")


class GetPartnerInfoInput(BaseModel):
    """Input para obtener info de partner"""
    partner_id: int = Field(description="ID del partner en Odoo")


class SearchProductsInput(BaseModel):
    """Input para búsqueda de productos"""
    query: str = Field(description="Término de búsqueda para productos")
    limit: int = Field(default=10, description="Límite de resultados")


class GetSalesOrdersInput(BaseModel):
    """Input para obtener órdenes de venta"""
    partner_id: Optional[int] = Field(default=None, description="ID del partner (opcional)")
    limit: int = Field(default=10, description="Límite de resultados")


class OdooSearchPartnersTool(BaseTool):
    """Herramienta para buscar partners en Odoo"""
    name: str = "odoo_search_partners"
    description: str = "Busca partners/contactos/clientes en Odoo por nombre, email o empresa"
    args_schema: Type[BaseModel] = SearchPartnersInput
    
    odoo_client: OdooMCPClient = Field(exclude=True)
    
    def _run(self, query: str, limit: int = 10) -> str:
        """Ejecuta la búsqueda de partners"""
        try:
            result = asyncio.run(self.odoo_client.search_partners(query, limit))
            return str(result)
        except Exception as e:
            logger.error(f"Error buscando partners: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, query: str, limit: int = 10) -> str:
        """Versión async de la búsqueda"""
        try:
            result = await self.odoo_client.search_partners(query, limit)
            return str(result)
        except Exception as e:
            logger.error(f"Error buscando partners: {e}")
            return f"Error: {str(e)}"


class OdooGetPartnerInfoTool(BaseTool):
    """Herramienta para obtener información de un partner"""
    name: str = "odoo_get_partner_info"
    description: str = "Obtiene información detallada de un partner/contacto/cliente en Odoo por su ID"
    args_schema: Type[BaseModel] = GetPartnerInfoInput
    
    odoo_client: OdooMCPClient = Field(exclude=True)
    
    def _run(self, partner_id: int) -> str:
        """Obtiene info del partner"""
        try:
            result = asyncio.run(self.odoo_client.get_partner_info(partner_id))
            return str(result)
        except Exception as e:
            logger.error(f"Error obteniendo info de partner: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, partner_id: int) -> str:
        """Versión async"""
        try:
            result = await self.odoo_client.get_partner_info(partner_id)
            return str(result)
        except Exception as e:
            logger.error(f"Error obteniendo info de partner: {e}")
            return f"Error: {str(e)}"


class OdooSearchProductsTool(BaseTool):
    """Herramienta para buscar productos en Odoo"""
    name: str = "odoo_search_products"
    description: str = "Busca productos en Odoo por nombre, referencia o código"
    args_schema: Type[BaseModel] = SearchProductsInput
    
    odoo_client: OdooMCPClient = Field(exclude=True)
    
    def _run(self, query: str, limit: int = 10) -> str:
        """Ejecuta la búsqueda de productos"""
        try:
            result = asyncio.run(self.odoo_client.search_products(query, limit))
            return str(result)
        except Exception as e:
            logger.error(f"Error buscando productos: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, query: str, limit: int = 10) -> str:
        """Versión async"""
        try:
            result = await self.odoo_client.search_products(query, limit)
            return str(result)
        except Exception as e:
            logger.error(f"Error buscando productos: {e}")
            return f"Error: {str(e)}"


class OdooGetSalesOrdersTool(BaseTool):
    """Herramienta para obtener órdenes de venta"""
    name: str = "odoo_get_sales_orders"
    description: str = "Obtiene órdenes de venta de Odoo, opcionalmente filtradas por partner/cliente"
    args_schema: Type[BaseModel] = GetSalesOrdersInput
    
    odoo_client: OdooMCPClient = Field(exclude=True)
    
    def _run(self, partner_id: Optional[int] = None, limit: int = 10) -> str:
        """Obtiene órdenes de venta"""
        try:
            result = asyncio.run(self.odoo_client.get_sales_orders(partner_id, limit))
            return str(result)
        except Exception as e:
            logger.error(f"Error obteniendo órdenes de venta: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, partner_id: Optional[int] = None, limit: int = 10) -> str:
        """Versión async"""
        try:
            result = await self.odoo_client.get_sales_orders(partner_id, limit)
            return str(result)
        except Exception as e:
            logger.error(f"Error obteniendo órdenes de venta: {e}")
            return f"Error: {str(e)}"


def create_odoo_langchain_tools(server_script_path: str, auto_connect: bool = True):
    """
    Crea herramientas de LangChain conectadas a servidor MCP de Odoo
    
    Args:
        server_script_path: Ruta al script del servidor MCP de Odoo
        auto_connect: Si conectar automáticamente al servidor
        
    Returns:
        Tupla de (cliente, lista de herramientas)
    """
    client = OdooMCPClient(server_script_path)
    
    if auto_connect:
        asyncio.run(client.connect())
    
    tools = [
        OdooSearchPartnersTool(odoo_client=client),
        OdooGetPartnerInfoTool(odoo_client=client),
        OdooSearchProductsTool(odoo_client=client),
        OdooGetSalesOrdersTool(odoo_client=client)
    ]
    
    return client, tools
