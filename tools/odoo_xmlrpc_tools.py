"""
Herramientas de LangChain para Odoo usando XML-RPC
"""

import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from .odoo_xmlrpc_client import OdooXMLRPCClient

logger = logging.getLogger(__name__)


class SearchProductsInput(BaseModel):
    """Input para búsqueda de productos"""
    query: Optional[str] = Field(default=None, description="Término de búsqueda para productos (nombre, referencia, código de barras)")
    limit: int = Field(default=10, description="Límite de resultados")


class GetProductByIdInput(BaseModel):
    """Input para obtener producto por ID"""
    product_id: int = Field(description="ID del producto en Odoo")


class SearchProductsTool(BaseTool):
    """Herramienta para buscar productos en Odoo"""
    name: str = "odoo_search_products"
    description: str = """Busca productos en el inventario de Odoo. 
    Puedes buscar por nombre del producto, referencia interna o código de barras.
    Retorna información como: nombre, precio, cantidad disponible, categoría, etc."""
    args_schema: Type[BaseModel] = SearchProductsInput
    
    odoo_client: OdooXMLRPCClient = Field(exclude=True)
    
    def _run(self, query: Optional[str] = None, limit: int = 10) -> str:
        """Ejecuta la búsqueda de productos"""
        try:
            products = self.odoo_client.get_products(query, limit)
            
            if not products:
                return f"No se encontraron productos{' con el término: ' + query if query else ''}."
            
            # Formatear resultados
            result = f"Se encontraron {len(products)} productos:\n\n"
            
            for idx, product in enumerate(products, 1):
                result += f"{idx}. {product.get('name')} (ID: {product.get('id')})\n"
                
                if product.get('default_code'):
                    result += f"   Referencia: {product.get('default_code')}\n"
                if product.get('barcode'):
                    result += f"   Código de barras: {product.get('barcode')}\n"
                    
                result += f"   Precio: ${product.get('list_price', 0):.2f}\n"
                result += f"   Costo: ${product.get('standard_price', 0):.2f}\n"
                result += f"   Stock disponible: {product.get('qty_available', 0)}\n"
                
                if product.get('categ_id'):
                    result += f"   Categoría: {product['categ_id'][1]}\n"
                if product.get('uom_id'):
                    result += f"   Unidad: {product['uom_id'][1]}\n"
                    
                result += "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error buscando productos: {e}")
            return f"Error al buscar productos: {str(e)}"


class GetProductByIdTool(BaseTool):
    """Herramienta para obtener información detallada de un producto"""
    name: str = "odoo_get_product_info"
    description: str = """Obtiene información detallada de un producto específico de Odoo por su ID.
    Retorna toda la información del producto incluyendo descripciones, precios, stock, etc."""
    args_schema: Type[BaseModel] = GetProductByIdInput
    
    odoo_client: OdooXMLRPCClient = Field(exclude=True)
    
    def _run(self, product_id: int) -> str:
        """Obtiene info del producto"""
        try:
            product = self.odoo_client.get_product_by_id(product_id)
            
            if not product:
                return f"No se encontró el producto con ID {product_id}."
            
            # Formatear resultado
            result = f"📦 PRODUCTO: {product.get('name')} (ID: {product.get('id')})\n\n"
            
            result += "INFORMACIÓN BÁSICA:\n"
            if product.get('default_code'):
                result += f"  • Referencia: {product.get('default_code')}\n"
            if product.get('barcode'):
                result += f"  • Código de barras: {product.get('barcode')}\n"
            result += f"  • Tipo: {product.get('type')}\n"
            result += f"  • Activo: {'Sí' if product.get('active') else 'No'}\n"
            
            if product.get('categ_id'):
                result += f"  • Categoría: {product['categ_id'][1]}\n"
            
            result += "\nPRECIOS:\n"
            result += f"  • Precio de venta: ${product.get('list_price', 0):.2f}\n"
            result += f"  • Costo: ${product.get('standard_price', 0):.2f}\n"
            
            result += "\nINVENTARIO:\n"
            result += f"  • Cantidad disponible: {product.get('qty_available', 0)}\n"
            if product.get('uom_id'):
                result += f"  • Unidad de medida: {product['uom_id'][1]}\n"
            
            if product.get('description'):
                result += f"\nDESCRIPCIÓN:\n{product.get('description')}\n"
            
            if product.get('description_sale'):
                result += f"\nDESCRIPCIÓN DE VENTA:\n{product.get('description_sale')}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo producto {product_id}: {e}")
            return f"Error al obtener información del producto: {str(e)}"


def create_odoo_xmlrpc_tools(url: str, db: str, username: str, password: str, auto_connect: bool = True):
    """
    Crea herramientas de LangChain conectadas a Odoo vía XML-RPC
    
    Args:
        url: URL de la instancia de Odoo
        db: Nombre de la base de datos
        username: Usuario
        password: Contraseña o API Key
        auto_connect: Si conectar automáticamente
        
    Returns:
        Tupla de (cliente, lista de herramientas)
    """
    client = OdooXMLRPCClient(url, db, username, password)
    
    if auto_connect:
        if not client.connect():
            raise ConnectionError("No se pudo conectar a Odoo. Verifica las credenciales.")
    
    tools = [
        SearchProductsTool(odoo_client=client),
        GetProductByIdTool(odoo_client=client),
    ]
    
    return client, tools
