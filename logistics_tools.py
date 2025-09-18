from typing import Dict, Optional
from database import Database
import logging

logger = logging.getLogger(__name__)

class LogisticsTools:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_shipment(self, tracking_id: str) -> Dict:
        """
        Tool: Get shipment information by tracking ID
        Args:
            tracking_id (str): The shipment tracking ID
        Returns:
            Dict: Shipment information or error message
        """
        try:
            # Clean up tracking ID (remove spaces, convert to uppercase)
            tracking_id = tracking_id.strip().upper()
            
            shipment = await self.db.get_shipment(tracking_id)
            
            # If not found and ends with 00, try variants (common speech recognition error)
            if not shipment and tracking_id.endswith('00') and len(tracking_id) == 8:
                base_id = tracking_id[:-2]  # Remove last two digits
                for last_digits in ['01', '02', '03', '04', '05', '06', '07', '08', '09']:
                    variant_id = base_id + last_digits
                    shipment = await self.db.get_shipment(variant_id)
                    if shipment:
                        tracking_id = variant_id  # Use the working variant
                        break
            
            if shipment:
                # Format the delivery address to extract city
                delivery_parts = shipment['delivery_address'].split(',')
                city = delivery_parts[-2].strip() if len(delivery_parts) >= 2 else "destination"
                
                return {
                    'success': True,
                    'data': {
                        'tracking_id': shipment['tracking_id'],
                        'customer_name': shipment['customer_name'],
                        'status': shipment['status'],
                        'delivery_date': shipment['delivery_date'],
                        'delivery_address': shipment['delivery_address'],
                        'pickup_address': shipment['pickup_address'],
                        'city': city
                    },
                    'message': f"Found shipment {tracking_id} for {shipment['customer_name']}"
                }
            else:
                return {
                    'success': False,
                    'error': 'shipment_not_found',
                    'message': f"Sorry, I couldn't find a shipment with tracking ID {tracking_id}. Please double-check the tracking number."
                }
        
        except Exception as e:
            logger.error(f"Error in get_shipment tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble accessing shipment information right now. Please try again or speak with a human agent."
            }
    
    async def update_shipment(self, tracking_id: str, new_date: str) -> Dict:
        """
        Tool: Update shipment delivery date
        Args:
            tracking_id (str): The shipment tracking ID
            new_date (str): New delivery date in YYYY-MM-DD format
        Returns:
            Dict: Update confirmation or error message
        """
        try:
            # Clean up tracking ID
            tracking_id = tracking_id.strip().upper()
            
            # Validate date format (basic validation)
            if not self._is_valid_date_format(new_date):
                return {
                    'success': False,
                    'error': 'invalid_date',
                    'message': "Please provide the date in a valid format, such as December 15th or 2024-12-15."
                }
            
            result = await self.db.update_shipment(tracking_id, new_date)
            
            return {
                'success': True,
                'data': {
                    'tracking_id': result['tracking_id'],
                    'customer_name': result['customer_name'],
                    'new_delivery_date': result['new_delivery_date'],
                    'status': result['status']
                },
                'message': result['confirmation_message']
            }
        
        except ValueError as e:
            return {
                'success': False,
                'error': 'shipment_not_found',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error in update_shipment tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble updating the shipment right now. Please try again or speak with a human agent."
            }
    
    async def book_shipment(
        self, 
        customer_name: str, 
        pickup_address: str, 
        delivery_address: str, 
        delivery_date: str
    ) -> Dict:
        """
        Tool: Book a new shipment
        Args:
            customer_name (str): Customer's full name
            pickup_address (str): Pickup address
            delivery_address (str): Delivery address
            delivery_date (str): Delivery date in YYYY-MM-DD format
        Returns:
            Dict: Booking confirmation with tracking ID or error message
        """
        try:
            # Validate required fields
            if not all([customer_name, pickup_address, delivery_address, delivery_date]):
                return {
                    'success': False,
                    'error': 'missing_information',
                    'message': "I need all the information to book your shipment: customer name, pickup address, delivery address, and delivery date."
                }
            
            # Validate date format
            if not self._is_valid_date_format(delivery_date):
                return {
                    'success': False,
                    'error': 'invalid_date',
                    'message': "Please provide the delivery date in a valid format."
                }
            
            result = await self.db.book_shipment(
                customer_name.strip(),
                pickup_address.strip(),
                delivery_address.strip(),
                delivery_date
            )
            
            return {
                'success': True,
                'data': {
                    'tracking_id': result['tracking_id'],
                    'customer_name': result['customer_name'],
                    'pickup_address': result['pickup_address'],
                    'delivery_address': result['delivery_address'],
                    'delivery_date': result['delivery_date'],
                    'status': result['status']
                },
                'message': result['confirmation_message']
            }
        
        except Exception as e:
            logger.error(f"Error in book_shipment tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble booking the shipment right now. Please try again or speak with a human agent."
            }
    
    async def verify_customer_identity(self, customer_name: str, tracking_id: str) -> Dict:
        """
        Tool: Verify customer identity for shipment modifications
        Args:
            customer_name (str): Customer's name
            tracking_id (str): Tracking ID to verify against
        Returns:
            Dict: Verification result
        """
        try:
            tracking_id = tracking_id.strip().upper()
            shipment = await self.db.get_shipment(tracking_id)
            
            if not shipment:
                return {
                    'success': False,
                    'error': 'shipment_not_found',
                    'message': f"I couldn't find shipment {tracking_id}"
                }
            
            # Simple name verification (case-insensitive, partial match)
            stored_name = shipment['customer_name'].lower()
            provided_name = customer_name.lower().strip()
            
            # Check if the provided name matches or is contained in the stored name
            if provided_name in stored_name or stored_name in provided_name:
                return {
                    'success': True,
                    'verified': True,
                    'customer_name': shipment['customer_name'],
                    'message': f"Identity verified for {shipment['customer_name']}"
                }
            else:
                return {
                    'success': True,
                    'verified': False,
                    'message': "The name doesn't match our records. For security, I'll need to transfer you to a human agent."
                }
        
        except Exception as e:
            logger.error(f"Error in verify_customer_identity tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble verifying your identity right now."
            }
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Validate if date string is in acceptable format"""
        try:
            # Try to parse common date formats
            from datetime import datetime
            
            # Try YYYY-MM-DD format first
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                datetime.strptime(date_str, "%m/%d/%Y")
                return True
            except ValueError:
                return False
    
    async def cancel_shipment(self, tracking_id: str) -> Dict:
        """
        Tool: Cancel a shipment
        Args:
            tracking_id (str): The shipment tracking ID to cancel
        Returns:
            Dict: Cancellation confirmation or error message
        """
        try:
            tracking_id = tracking_id.strip().upper()
            result = await self.db.cancel_shipment(tracking_id)
            
            return {
                'success': True,
                'data': {
                    'tracking_id': result['tracking_id'],
                    'customer_name': result['customer_name'],
                    'previous_status': result['previous_status'],
                    'new_status': result['new_status']
                },
                'message': result['confirmation_message']
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': 'shipment_error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error in cancel_shipment tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble cancelling the shipment right now. Please try again or speak with a human agent."
            }
    
    async def update_address(self, tracking_id: str, address_type: str, new_address: str) -> Dict:
        """
        Tool: Update pickup or delivery address
        Args:
            tracking_id (str): The shipment tracking ID
            address_type (str): 'pickup' or 'delivery'
            new_address (str): The new address
        Returns:
            Dict: Update confirmation or error message
        """
        try:
            tracking_id = tracking_id.strip().upper()
            address_type = address_type.lower().strip()
            
            if address_type not in ['pickup', 'delivery']:
                return {
                    'success': False,
                    'error': 'invalid_address_type',
                    'message': "Please specify whether you want to update the pickup or delivery address."
                }
            
            result = await self.db.update_shipment_address(tracking_id, address_type, new_address)
            
            return {
                'success': True,
                'data': {
                    'tracking_id': result['tracking_id'],
                    'customer_name': result['customer_name'],
                    'address_type': result['address_type'],
                    'old_address': result['old_address'],
                    'new_address': result['new_address']
                },
                'message': result['confirmation_message']
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': 'shipment_error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error in update_address tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble updating the address right now. Please try again or speak with a human agent."
            }
    
    async def update_delivery_time(self, tracking_id: str, new_time: str, new_date: str = None) -> Dict:
        """
        Tool: Update delivery time/date
        Args:
            tracking_id (str): The shipment tracking ID
            new_time (str): New delivery time (e.g., "2:00 PM", "morning", "afternoon")
            new_date (str, optional): New delivery date in YYYY-MM-DD format
        Returns:
            Dict: Update confirmation or error message
        """
        try:
            tracking_id = tracking_id.strip().upper()
            
            # Validate date format if provided
            if new_date and not self._is_valid_date_format(new_date):
                return {
                    'success': False,
                    'error': 'invalid_date',
                    'message': "Please provide the date in a valid format, such as December 15th or 2024-12-15."
                }
            
            result = await self.db.update_delivery_time(tracking_id, new_time, new_date)
            
            return {
                'success': True,
                'data': {
                    'tracking_id': result['tracking_id'],
                    'customer_name': result['customer_name'],
                    'old_date': result['old_date'],
                    'new_date': result['new_date'],
                    'new_time': result['new_time']
                },
                'message': result['confirmation_message']
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': 'shipment_error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error in update_delivery_time tool: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': "I'm having trouble updating the delivery time right now. Please try again or speak with a human agent."
            }