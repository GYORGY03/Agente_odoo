"""
Cliente XML-RPC para Odoo 17
Conexión directa a instancia de Odoo para leer/escribir datos
"""

import xmlrpc.client
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OdooXMLRPCClient:
    """Cliente XML-RPC para conectarse a Odoo 17"""
    
    def __init__(self, url: str, db: str, username: str, password: str):
        """
        Inicializa el cliente de Odoo
        
        Args:
            url: URL de la instancia de Odoo (ej: https://mycompany.odoo.com)
            db: Nombre de la base de datos
            username: Usuario de Odoo
            password: Contraseña o API Key
        """
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        
    def connect(self) -> bool:
        """Conecta y autentica con Odoo"""
        print(f"\n[ODOO CLIENT] Iniciando conexión...")
        print(f"[ODOO CLIENT] URL: {self.url}")
        print(f"[ODOO CLIENT] DB: {self.db}")
        print(f"[ODOO CLIENT] Username: {self.username}")
        
        try:
            # Endpoint común para autenticación
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            
            # Verificar versión del servidor
            print(f"[ODOO CLIENT] Obteniendo versión del servidor...")
            version_info = self.common.version()
            logger.info(f"Conectado a Odoo versión: {version_info.get('server_version')}")
            print(f"[ODOO CLIENT] Versión Odoo: {version_info.get('server_version')}")
            
            # Autenticar
            print(f"[ODOO CLIENT] Autenticando...")
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            
            if not self.uid:
                logger.error("Error de autenticación. Verifica credenciales.")
                print(f"[ODOO CLIENT] ERROR: Autenticación falló (uid=False)")
                return False
            
            logger.info(f"Autenticado exitosamente. UID: {self.uid}")
            print(f"[ODOO CLIENT] ✓ Autenticación exitosa. UID: {self.uid}")
            
            # Endpoint para llamar métodos
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"[ODOO CLIENT] ✓ Cliente models configurado")
            
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a Odoo: {e}")
            print(f"[ODOO CLIENT] ERROR: {e}")
            return False
    
    def search(self, model: str, domain: List = None, offset: int = 0, limit: int = 100) -> List[int]:
        """
        Busca registros en un modelo
        
        Args:
            model: Nombre del modelo (ej: 'product.product')
            domain: Filtros de búsqueda (ej: [['type', '=', 'product']])
            offset: Número de registros a saltar
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de IDs de registros
        """
        if domain is None:
            domain = []
            
        try:
            ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search',
                [domain],
                {'offset': offset, 'limit': limit}
            )
            return ids
        except Exception as e:
            logger.error(f"Error buscando en {model}: {e}")
            return []
    
    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """
        Lee registros por IDs
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a leer
            fields: Lista de campos a retornar (None = todos)
            
        Returns:
            Lista de diccionarios con los datos
        """
        try:
            options = {}
            if fields:
                options['fields'] = fields
                
            records = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'read',
                [ids],
                options
            )
            return records
        except Exception as e:
            logger.error(f"Error leyendo {model}: {e}")
            return []
    
    def search_read(self, model: str, domain: List = None, fields: List[str] = None, 
                    offset: int = 0, limit: int = 100) -> List[Dict]:
        """
        Busca y lee registros en una sola llamada
        
        Args:
            model: Nombre del modelo
            domain: Filtros de búsqueda
            fields: Campos a retornar
            offset: Número de registros a saltar
            limit: Número máximo de registros
            
        Returns:
            Lista de diccionarios con los datos
        """
        if domain is None:
            domain = []
            
        try:
            options = {'offset': offset, 'limit': limit}
            if fields:
                options['fields'] = fields
                
            records = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_read',
                [domain],
                options
            )
            return records
        except Exception as e:
            logger.error(f"Error en search_read {model}: {e}")
            return []
    
    def search_count(self, model: str, domain: List = None) -> int:
        """
        Cuenta registros que coinciden con el dominio
        
        Args:
            model: Nombre del modelo
            domain: Filtros de búsqueda
            
        Returns:
            Número de registros
        """
        if domain is None:
            domain = []
            
        try:
            count = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_count',
                [domain]
            )
            return count
        except Exception as e:
            logger.error(f"Error contando {model}: {e}")
            return 0
    
    def get_products(self, query: str = None, limit: int = 10) -> List[Dict]:
        """
        Obtiene productos del inventario
        
        Args:
            query: Término de búsqueda (busca en nombre, referencia, código de barras)
            limit: Número máximo de productos
            
        Returns:
            Lista de productos con sus datos
        """
        print(f"\n[ODOO CLIENT] get_products() llamado")
        print(f"[ODOO CLIENT] query: '{query}', limit: {limit}")
        print(f"[ODOO CLIENT] Autenticado: uid={self.uid}")
        
        domain = []
        
        if query:
            # Buscar en nombre, referencia interna o código de barras
            domain = [
                '|', '|',
                ['name', 'ilike', query],
                ['default_code', 'ilike', query],
                ['barcode', 'ilike', query]
            ]
            print(f"[ODOO CLIENT] Domain de búsqueda: {domain}")
        else:
            print(f"[ODOO CLIENT] Sin filtro de búsqueda (query=None)")
        
        fields = [
            'name',           # Nombre del producto
            'default_code',   # Referencia interna
            'barcode',        # Código de barras
            'type',           # Tipo (product, consu, service)
            'categ_id',       # Categoría
            'list_price',     # Precio de venta
            'standard_price', # Costo
            'qty_available',  # Cantidad disponible
            'uom_id',         # Unidad de medida
            'active',         # Activo
        ]
        
        print(f"[ODOO CLIENT] Ejecutando search_read en product.product...")
        products = self.search_read('product.product', domain, fields, limit=limit)
        print(f"[ODOO CLIENT] Productos encontrados: {len(products)}")
        
        if products:
            print(f"[ODOO CLIENT] Primer producto: {products[0].get('name')}")
        else:
            print(f"[ODOO CLIENT] No se encontraron productos")
        
        return products
    
    def get_product_by_id(self, product_id: int) -> Dict:
        """
        Obtiene un producto específico por ID
        
        Args:
            product_id: ID del producto
            
        Returns:
            Diccionario con datos del producto
        """
        fields = [
            'name', 'default_code', 'barcode', 'type', 'categ_id',
            'list_price', 'standard_price', 'qty_available', 'uom_id',
            'description', 'description_sale', 'active', 'company_id'
        ]
        
        products = self.read('product.product', [product_id], fields)
        return products[0] if products else {}
    
    def get_stock_quants(self, product_id: int = None, location_id: int = None) -> List[Dict]:
        """
        Obtiene información de stock por ubicación
        
        Args:
            product_id: ID del producto (opcional)
            location_id: ID de la ubicación (opcional)
            
        Returns:
            Lista de quants (cantidades por ubicación)
        """
        domain = []
        
        if product_id:
            domain.append(['product_id', '=', product_id])
        if location_id:
            domain.append(['location_id', '=', location_id])
            
        fields = ['product_id', 'location_id', 'quantity', 'reserved_quantity', 'lot_id']
        
        quants = self.search_read('stock.quant', domain, fields, limit=100)
        return quants
