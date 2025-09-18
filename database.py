import asyncpg
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, List
import logging
import uuid

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
                statement_cache_size=0  # Disable prepared statement cache to avoid conflicts
            )
            await self.create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            # Create shipments table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS shipments (
                    tracking_id VARCHAR(20) PRIMARY KEY,
                    customer_name VARCHAR(255) NOT NULL,
                    pickup_address TEXT NOT NULL,
                    delivery_address TEXT NOT NULL,
                    delivery_date DATE NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create call_logs table for tracking interactions
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS call_logs (
                    id SERIAL PRIMARY KEY,
                    call_sid VARCHAR(255) UNIQUE NOT NULL,
                    from_number VARCHAR(20),
                    action VARCHAR(50),
                    tracking_id VARCHAR(20),
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info("Database tables created successfully")
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def get_shipment(self, tracking_id: str) -> Optional[Dict]:
        """Get shipment information by tracking ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM shipments WHERE tracking_id = $1",
                    tracking_id
                )
                
                if row:
                    return {
                        'tracking_id': row['tracking_id'],
                        'customer_name': row['customer_name'],
                        'pickup_address': row['pickup_address'],
                        'delivery_address': row['delivery_address'],
                        'delivery_date': row['delivery_date'].isoformat(),
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat(),
                        'updated_at': row['updated_at'].isoformat()
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting shipment {tracking_id}: {str(e)}")
            raise
    
    async def book_shipment(
        self, 
        customer_name: str, 
        pickup_address: str, 
        delivery_address: str, 
        delivery_date: str
    ) -> Dict:
        """Book a new shipment"""
        try:
            # Generate simple numeric tracking ID (8 digits)
            import random
            tracking_id = str(random.randint(10000000, 99999999))
            
            # Convert delivery_date string to date object
            delivery_date_obj = datetime.strptime(delivery_date, "%Y-%m-%d").date()
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO shipments 
                    (tracking_id, customer_name, pickup_address, delivery_address, delivery_date, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    tracking_id,
                    customer_name,
                    pickup_address,
                    delivery_address,
                    delivery_date_obj,
                    'booked'
                )
                
                return {
                    'tracking_id': tracking_id,
                    'customer_name': customer_name,
                    'pickup_address': pickup_address,
                    'delivery_address': delivery_address,
                    'delivery_date': delivery_date,
                    'status': 'booked',
                    'confirmation_message': f'Your shipment has been booked successfully with tracking ID {tracking_id}'
                }
        except Exception as e:
            logger.error(f"Error booking shipment: {str(e)}")
            raise
    
    async def update_shipment(self, tracking_id: str, new_date: str) -> Dict:
        """Update shipment delivery date"""
        try:
            # Convert new_date string to date object
            new_date_obj = datetime.strptime(new_date, "%Y-%m-%d").date()
            
            async with self.pool.acquire() as conn:
                # Check if shipment exists
                existing = await conn.fetchrow(
                    "SELECT tracking_id, customer_name FROM shipments WHERE tracking_id = $1",
                    tracking_id
                )
                
                if not existing:
                    raise ValueError(f"Shipment with tracking ID {tracking_id} not found")
                
                # Update the shipment
                await conn.execute(
                    """
                    UPDATE shipments 
                    SET delivery_date = $1, status = 'rescheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_id = $2
                    """,
                    new_date_obj,
                    tracking_id
                )
                
                return {
                    'tracking_id': tracking_id,
                    'customer_name': existing['customer_name'],
                    'new_delivery_date': new_date,
                    'status': 'rescheduled',
                    'confirmation_message': f'Your shipment {tracking_id} has been rescheduled for delivery on {new_date}'
                }
        except Exception as e:
            logger.error(f"Error updating shipment {tracking_id}: {str(e)}")
            raise
    
    async def log_call_interaction(
        self, 
        call_sid: str, 
        from_number: str, 
        action: str, 
        tracking_id: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log call interaction for analytics"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO call_logs (call_sid, from_number, action, tracking_id, details)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (call_sid) DO UPDATE SET
                        action = EXCLUDED.action,
                        tracking_id = EXCLUDED.tracking_id,
                        details = EXCLUDED.details
                    """,
                    call_sid,
                    from_number,
                    action,
                    tracking_id,
                    details
                )
        except Exception as e:
            logger.error(f"Error logging call interaction: {str(e)}")
    
    async def get_shipments_by_customer(self, customer_name: str) -> List[Dict]:
        """Get all shipments for a customer (used for identity verification)"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM shipments WHERE LOWER(customer_name) = LOWER($1) ORDER BY created_at DESC",
                    customer_name
                )
                
                shipments = []
                for row in rows:
                    shipments.append({
                        'tracking_id': row['tracking_id'],
                        'customer_name': row['customer_name'],
                        'pickup_address': row['pickup_address'],
                        'delivery_address': row['delivery_address'],
                        'delivery_date': row['delivery_date'].isoformat(),
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat()
                    })
                
                return shipments
        except Exception as e:
            logger.error(f"Error getting shipments for customer {customer_name}: {str(e)}")
            raise
    
    async def cancel_shipment(self, tracking_id: str) -> Dict:
        """Cancel a shipment"""
        try:
            async with self.pool.acquire() as conn:
                # Check if shipment exists
                existing = await conn.fetchrow(
                    "SELECT tracking_id, customer_name, status FROM shipments WHERE tracking_id = $1",
                    tracking_id
                )
                
                if not existing:
                    raise ValueError(f"Shipment with tracking ID {tracking_id} not found")
                
                if existing['status'] == 'cancelled':
                    raise ValueError(f"Shipment {tracking_id} is already cancelled")
                
                # Cancel the shipment
                await conn.execute(
                    """
                    UPDATE shipments 
                    SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_id = $1
                    """,
                    tracking_id
                )
                
                return {
                    'tracking_id': tracking_id,
                    'customer_name': existing['customer_name'],
                    'previous_status': existing['status'],
                    'new_status': 'cancelled',
                    'confirmation_message': f'Your shipment {tracking_id} has been successfully cancelled'
                }
        except Exception as e:
            logger.error(f"Error cancelling shipment {tracking_id}: {str(e)}")
            raise
    
    async def update_shipment_address(
        self, 
        tracking_id: str, 
        address_type: str, 
        new_address: str
    ) -> Dict:
        """Update pickup or delivery address"""
        try:
            if address_type not in ['pickup', 'delivery']:
                raise ValueError("Address type must be 'pickup' or 'delivery'")
            
            field_name = f"{address_type}_address"
            
            async with self.pool.acquire() as conn:
                # Check if shipment exists
                existing = await conn.fetchrow(
                    f"SELECT tracking_id, customer_name, {field_name} FROM shipments WHERE tracking_id = $1",
                    tracking_id
                )
                
                if not existing:
                    raise ValueError(f"Shipment with tracking ID {tracking_id} not found")
                
                # Update the address
                await conn.execute(
                    f"""
                    UPDATE shipments 
                    SET {field_name} = $1, status = 'modified', updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_id = $2
                    """,
                    new_address,
                    tracking_id
                )
                
                return {
                    'tracking_id': tracking_id,
                    'customer_name': existing['customer_name'],
                    'address_type': address_type,
                    'old_address': existing[field_name],
                    'new_address': new_address,
                    'confirmation_message': f'Your {address_type} address for shipment {tracking_id} has been updated to {new_address}'
                }
        except Exception as e:
            logger.error(f"Error updating {address_type} address for {tracking_id}: {str(e)}")
            raise
    
    async def update_delivery_time(self, tracking_id: str, new_time: str, new_date: str = None) -> Dict:
        """Update delivery date/time"""
        try:
            async with self.pool.acquire() as conn:
                # Check if shipment exists
                existing = await conn.fetchrow(
                    "SELECT tracking_id, customer_name, delivery_date FROM shipments WHERE tracking_id = $1",
                    tracking_id
                )
                
                if not existing:
                    raise ValueError(f"Shipment with tracking ID {tracking_id} not found")
                
                # Use provided date or keep existing date
                if new_date:
                    new_date_obj = datetime.strptime(new_date, "%Y-%m-%d").date()
                else:
                    new_date_obj = existing['delivery_date']
                    new_date = existing['delivery_date'].isoformat()
                
                # Update the delivery date
                await conn.execute(
                    """
                    UPDATE shipments 
                    SET delivery_date = $1, status = 'rescheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE tracking_id = $2
                    """,
                    new_date_obj,
                    tracking_id
                )
                
                return {
                    'tracking_id': tracking_id,
                    'customer_name': existing['customer_name'],
                    'old_date': existing['delivery_date'].isoformat(),
                    'new_date': new_date,
                    'new_time': new_time,
                    'confirmation_message': f'Your delivery for shipment {tracking_id} has been rescheduled to {new_date} at {new_time}'
                }
        except Exception as e:
            logger.error(f"Error updating delivery time for {tracking_id}: {str(e)}")
            raise