import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from logistics_tools import LogisticsTools
from database import Database

logger = logging.getLogger(__name__)

class SwiftLogisticsAgent:
    def __init__(self, db: Database):
        self.db = db
        self.logistics_tools = LogisticsTools(db)
        
        # Conversation states
        self.states = {
            'greeting': 'greeting',
            'intent_detection': 'intent_detection', 
            'tracking': 'tracking',
            'booking': 'booking',
            'rescheduling': 'rescheduling',
            'cancellation': 'cancellation',
            'address_update': 'address_update',
            'time_update': 'time_update',
            'identity_verification': 'identity_verification',
            'completion': 'completion',
            'transfer_human': 'transfer_human'
        }
    
    async def process_message(
        self, 
        user_message: str, 
        current_state: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user message and return AI response
        Args:
            user_message: Transcribed user speech
            current_state: Current conversation state
            context: Conversation context and collected data
        Returns:
            Dict containing response message, next state, and updated context
        """
        try:
            user_message = user_message.lower().strip()
            logger.info(f"Processing message: '{user_message}' in state: {current_state}")
            
            # Handle human transfer request at any time
            if self._wants_human_agent(user_message):
                return self._transfer_to_human()
            
            # Route to appropriate handler based on state
            if current_state == 'greeting':
                return await self._handle_greeting(user_message, context)
            elif current_state == 'intent_detection':
                return await self._handle_intent_detection(user_message, context)
            elif current_state == 'tracking':
                return await self._handle_tracking(user_message, context)
            elif current_state == 'booking':
                return await self._handle_booking(user_message, context)
            elif current_state == 'rescheduling':
                return await self._handle_rescheduling(user_message, context)
            elif current_state == 'cancellation':
                return await self._handle_cancellation(user_message, context)
            elif current_state == 'address_update':
                return await self._handle_address_update(user_message, context)
            elif current_state == 'time_update':
                return await self._handle_time_update(user_message, context)
            elif current_state == 'identity_verification':
                return await self._handle_identity_verification(user_message, context)
            else:
                # Default fallback
                return await self._handle_intent_detection(user_message, context)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'message': "I'm sorry, I'm having technical difficulties. Let me transfer you to a human agent.",
                'next_state': 'transfer_human',
                'context': context,
                'continue_conversation': False
            }
    
    async def _handle_greeting(self, user_message: str, context: Dict) -> Dict:
        """Handle initial greeting and detect user intent"""
        # Move to intent detection and process the message
        return await self._handle_intent_detection(user_message, context)
    
    async def _handle_intent_detection(self, user_message: str, context: Dict) -> Dict:
        """Detect user intent and route to appropriate flow"""
        
        # Handle request to repeat tracking ID
        if 'repeat' in user_message.lower() and 'tracking' in user_message.lower():
            last_booking = context.get('last_booking')
            if last_booking and 'tracking_id' in last_booking:
                tracking_id = last_booking['tracking_id']
                slow_tracking_id = self._format_tracking_id_for_speech(tracking_id)
                return {
                    'message': f"Of course! Your tracking ID is: {slow_tracking_id}. Please write this down. Is there anything else I can help you with?",
                    'next_state': 'intent_detection',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I don't have a recent tracking ID to repeat. Would you like to book a new shipment or track an existing one?",
                    'next_state': 'intent_detection',
                    'context': context,
                    'continue_conversation': True
                }
        #
        # Cancel shipment intent (check FIRST to avoid conflicts) and can add a layer of security to cancel the shipment
        if self._wants_to_cancel(user_message):
            logger.info(f"Detected cancellation intent")
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                logger.info(f"Found tracking ID in cancellation request: {tracking_id}")
                # Cancel immediately without identity verification
                result = await self.logistics_tools.cancel_shipment(tracking_id)
                if result['success']:
                    return {
                        'message': result['message'] + " Is there anything else I can help you with?",
                        'next_state': 'intent_detection',
                        'context': {},
                        'continue_conversation': True
                    }
                else:
                    return {
                        'message': result['message'],
                        'next_state': 'intent_detection',
                        'context': {},
                        'continue_conversation': True
                    }
            else:
                logger.info(f"No tracking ID found, asking for tracking ID")
                return {
                    'message': "I can help you cancel your shipment. First, please provide your tracking ID.",
                    'next_state': 'cancellation',
                    'context': {**context, 'action': 'cancel', 'step': 'get_tracking_id'},
                    'continue_conversation': True
                }
        
        # Track shipment intent
        elif self._wants_to_track(user_message):
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                # User provided tracking ID immediately
                context['tracking_id'] = tracking_id
                return await self._handle_tracking("", context)
            else:
                return {
                    'message': "I can help you track your shipment. Please provide your tracking ID.",
                    'next_state': 'tracking',
                    'context': context,
                    'continue_conversation': True
                }
        
        # Update address intent (CHECK BEFORE BOOKING
        elif self._wants_to_update_address(user_message):
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                context['tracking_id'] = tracking_id
                context['action'] = 'update_address'
                return {
                    'message': f"I can help you update the address for shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                    'next_state': 'identity_verification',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I can help you update your shipment address. First, please provide your tracking ID.",
                    'next_state': 'address_update',
                    'context': {**context, 'action': 'update_address', 'step': 'get_tracking_id'},
                    'continue_conversation': True
                }
        
        # Book shipment intent
        elif self._wants_to_book(user_message):
            return {
                'message': "I'd be happy to help you book a new shipment. Let me get some information from you. First, what's your full name?",
                'next_state': 'booking',
                'context': {**context, 'booking_step': 'customer_name'},
                'continue_conversation': True
            }

        # Reschedule/delay shipment intent
        elif self._wants_to_reschedule(user_message):
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                context['tracking_id'] = tracking_id
                context['reschedule_step'] = 'identity_verification'
                return {
                    'message': f"I can help you reschedule shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                    'next_state': 'identity_verification',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I can help you reschedule your shipment. First, please provide your tracking ID.",
                    'next_state': 'rescheduling',
                    'context': {**context, 'reschedule_step': 'get_tracking_id'},
                    'continue_conversation': True
                }
        
        
        # Update delivery time intent
        elif self._wants_to_update_time(user_message):
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                context['tracking_id'] = tracking_id
                context['action'] = 'update_time'
                return {
                    'message': f"I can help you change the delivery time for shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                    'next_state': 'identity_verification',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I can help you change your delivery time. First, please provide your tracking ID.",
                    'next_state': 'time_update',
                    'context': {**context, 'action': 'update_time', 'step': 'get_tracking_id'},
                    'continue_conversation': True
                }
        
        # Thank you / goodbye intent
        elif any(word in user_message for word in ['thank you', 'thanks', 'thats all', "that's all", 'goodbye', 'bye', 'done']):
            return {
                'message': "Thank you for calling Rocket Shipment! You can now hang up the call or if you want to speak to a human agent press star.",
                'next_state': 'completed',
                'context': {},
                'continue_conversation': False
            }
        
        # General greeting or unclear intent
        else:
            return {
                'message': "I can help with tracking shipments, booking new shipments, rescheduling deliveries, cancelling shipments, or updating addresses and delivery times. What would you like to do today?",
                'next_state': 'intent_detection',
                'context': context,
                'continue_conversation': True
            }
    
    async def _handle_tracking(self, user_message: str, context: Dict) -> Dict:
        """Handle shipment tracking requests"""
        tracking_id = context.get('tracking_id') or self._extract_tracking_id(user_message)
        
        if not tracking_id:
            return {
                'message': "I didn't catch your tracking ID clearly. Please speak each digit slowly and clearly. For example, if your ID is 19608609, say 'one nine six zero eight six zero nine'.",
                'next_state': 'tracking',
                'context': context,
                'continue_conversation': True
            }
        
        # Call tracking tool
        result = await self.logistics_tools.get_shipment(tracking_id)
        
        if result['success']:
            shipment = result['data']
            status_message = self._format_tracking_response(shipment)
            
            return {
                'message': status_message + " Is there anything else I can help you with today?",
                'next_state': 'intent_detection',
                'context': {'last_tracking_id': tracking_id},
                'continue_conversation': True
            }
        else:
            return {
                'message': result['message'] + " Would you like to try another tracking ID or is there something else I can help you with?",
                'next_state': 'intent_detection',
                'context': context,
                'continue_conversation': True
            }
    
    async def _handle_booking(self, user_message: str, context: Dict) -> Dict:
        """Handle new shipment booking requests"""
        booking_step = context.get('booking_step', 'customer_name')
        
        if booking_step == 'customer_name':
            if not user_message or len(user_message.strip()) < 2:
                return {
                    'message': "Sorry, I didn't get your name. Can you please speak again?",
                    'next_state': 'booking',
                    'context': context,
                    'continue_conversation': True
                }
            context['customer_name'] = user_message.title()
            return {
                'message': f"Thank you, {context['customer_name']}. What's the pickup address?",
                'next_state': 'booking',
                'context': {**context, 'booking_step': 'pickup_address'},
                'continue_conversation': True
            }
        
        elif booking_step == 'pickup_address':
            if not user_message or len(user_message.strip()) < 3:
                return {
                    'message': "Sorry, I didn't get the pickup address. Can you please speak again?",
                    'next_state': 'booking',
                    'context': context,
                    'continue_conversation': True
                }
            context['pickup_address'] = user_message
            return {
                'message': "Got it. And what's the delivery address?",
                'next_state': 'booking',
                'context': {**context, 'booking_step': 'delivery_address'},
                'continue_conversation': True
            }
        
        elif booking_step == 'delivery_address':
            if not user_message or len(user_message.strip()) < 3:
                return {
                    'message': "Sorry, I didn't get the delivery address. Can you please speak again?",
                    'next_state': 'booking',
                    'context': context,
                    'continue_conversation': True
                }
            context['delivery_address'] = user_message
            return {
                'message': "Perfect. When would you like this delivered? Please provide a date.",
                'next_state': 'booking',
                'context': {**context, 'booking_step': 'delivery_date'},
                'continue_conversation': True
            }
        
        elif booking_step == 'delivery_date':
            delivery_date = self._parse_date(user_message)
            
            if not delivery_date:
                return {
                    'message': "Sorry, I didn't get the date. Can you please speak again?",
                    'next_state': 'booking',
                    'context': context,
                    'continue_conversation': True
                }
            
            # Book the shipment
            result = await self.logistics_tools.book_shipment(
                context['customer_name'],
                context['pickup_address'],
                context['delivery_address'],
                delivery_date
            )
            
            if result['success']:
                # Format tracking ID to speak slowly and clearly
                tracking_id = result['data']['tracking_id']
                slow_tracking_id = self._format_tracking_id_for_speech(tracking_id)
                
                message = f"Great! Your shipment has been booked successfully. Your tracking ID is: {slow_tracking_id}. Please write this down. We will dispatch an agent to your pickup address tomorrow morning who will pickup the package. Expect him to come around 10 AM. Is there anything else I can help you with?"
                
                return {
                    'message': message,
                    'next_state': 'intent_detection',
                    'context': {'last_booking': result['data']},
                    'continue_conversation': True
                }
            else:
                return {
                    'message': f"{result['message']} Would you like to try again or speak with a human agent?",
                    'next_state': 'intent_detection',
                    'context': context,
                    'continue_conversation': True
                }
    
    async def _handle_rescheduling(self, user_message: str, context: Dict) -> Dict:
        """Handle shipment rescheduling requests"""
        reschedule_step = context.get('reschedule_step', 'get_tracking_id')
        
        if reschedule_step == 'get_tracking_id':
            tracking_id = self._extract_tracking_id(user_message)
            if not tracking_id:
                return {
                    'message': "I didn't catch your tracking ID. Could you please repeat it?",
                    'next_state': 'rescheduling',
                    'context': context,
                    'continue_conversation': True
                }
            
            context['tracking_id'] = tracking_id
            return {
                'message': f"I'll help you reschedule shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                'next_state': 'identity_verification',
                'context': {**context, 'reschedule_step': 'identity_verification'},
                'continue_conversation': True
            }
        
        elif reschedule_step == 'get_new_date':
            new_date = self._parse_date(user_message)
            
            if not new_date:
                return {
                    'message': "Sorry, I didn't get the date. Can you please speak again?",
                    'next_state': 'rescheduling',
                    'context': context,
                    'continue_conversation': True
                }
            
            # Update the shipment
            result = await self.logistics_tools.update_shipment(context['tracking_id'], new_date)
            
            if result['success']:
                return {
                    'message': f"{result['message']}. Is there anything else I can help you with?",
                    'next_state': 'intent_detection',
                    'context': {'last_update': result['data']},
                    'continue_conversation': True
                }
            else:
                return {
                    'message': f"{result['message']} Would you like to try again or speak with a human agent?",
                    'next_state': 'intent_detection',
                    'context': context,
                    'continue_conversation': True
                }
    
    async def _handle_identity_verification(self, user_message: str, context: Dict) -> Dict:
        """Handle customer identity verification for shipment modifications"""
        tracking_id = context.get('tracking_id')
        
        if not tracking_id:
            return {
                'message': "I seem to have lost your tracking information. Could you please provide your tracking ID again?",
                'next_state': 'rescheduling',
                'context': {},
                'continue_conversation': True
            }
        
        # Verify customer identity
        result = await self.logistics_tools.verify_customer_identity(user_message, tracking_id)
        
        if not result['success']:
            return {
                'message': result['message'] + " Let me transfer you to a human agent.",
                'next_state': 'transfer_human',
                'context': context,
                'continue_conversation': False
            }
        
        if result['verified']:
            action = context.get('action', 'reschedule')  # Default to reschedule for backward compatibility
            
            if action == 'cancel':
                return {
                    'message': f"Thank you for the verification. Are you sure you want to cancel shipment {tracking_id}? This action cannot be undone.",
                    'next_state': 'cancellation',
                    'context': {**context, 'step': 'confirm_cancellation', 'identity_verified': True},
                    'continue_conversation': True
                }
            elif action == 'update_address':
                return {
                    'message': f"Thank you for the verification. Which address would you like to update for shipment {tracking_id}? The pickup address or delivery address?",
                    'next_state': 'address_update',
                    'context': {**context, 'step': 'select_address_type', 'identity_verified': True},
                    'continue_conversation': True
                }
            elif action == 'update_time':
                return {
                    'message': f"Thank you for the verification. What new delivery time would you like for shipment {tracking_id}?",
                    'next_state': 'time_update',
                    'context': {**context, 'step': 'get_new_time', 'identity_verified': True},
                    'continue_conversation': True
                }
            else:  # Default to reschedule
                return {
                    'message': f"Thank you for the verification. What's the new delivery date you'd like for shipment {tracking_id}?",
                    'next_state': 'rescheduling',
                    'context': {**context, 'reschedule_step': 'get_new_date', 'identity_verified': True},
                    'continue_conversation': True
                }
        else:
            return {
                'message': result['message'],
                'next_state': 'transfer_human',
                'context': context,
                'continue_conversation': False
            }
    
    async def _handle_cancellation(self, user_message: str, context: Dict) -> Dict:
        """Handle shipment cancellation requests"""
        tracking_id = context.get('tracking_id')
        step = context.get('step', 'get_tracking_id')
        
        if step == 'get_tracking_id':
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                # Cancel immediately without identity verification
                result = await self.logistics_tools.cancel_shipment(tracking_id)
                if result['success']:
                    return {
                        'message': result['message'] + " Is there anything else I can help you with?",
                        'next_state': 'intent_detection',
                        'context': {},
                        'continue_conversation': True
                    }
                else:
                    return {
                        'message': result['message'],
                        'next_state': 'intent_detection',
                        'context': {},
                        'continue_conversation': True
                    }
            else:
                return {
                    'message': "I didn't catch your tracking ID. Could you please repeat it?",
                    'next_state': 'cancellation',
                    'context': context,
                    'continue_conversation': True
                }
        
        elif step == 'confirm_cancellation':
            if any(word in user_message.lower() for word in ['yes', 'confirm', 'sure', 'ok', 'proceed']):
                result = await self.logistics_tools.cancel_shipment(tracking_id)
                
                if result['success']:
                    return {
                        'message': result['message'] + " Is there anything else I can help you with?",
                        'next_state': 'completion',
                        'context': {},
                        'continue_conversation': True
                    }
                else:
                    return {
                        'message': result['message'] + " Let me transfer you to a human agent.",
                        'next_state': 'transfer_human',
                        'context': context,
                        'continue_conversation': False
                    }
            else:
                return {
                    'message': "Cancellation cancelled. Your shipment remains active. Is there anything else I can help you with?",
                    'next_state': 'completion',
                    'context': {},
                    'continue_conversation': True
                }
    
    async def _handle_address_update(self, user_message: str, context: Dict) -> Dict:
        """Handle address update requests"""
        tracking_id = context.get('tracking_id')
        step = context.get('step', 'get_tracking_id')
        
        if step == 'get_tracking_id':
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                context['tracking_id'] = tracking_id
                context['action'] = 'update_address'
                return {
                    'message': f"I can help you update the address for shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                    'next_state': 'identity_verification',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I didn't catch your tracking ID. Could you please repeat it?",
                    'next_state': 'address_update',
                    'context': context,
                    'continue_conversation': True
                }
        
        elif step == 'select_address_type':
            user_message_lower = user_message.lower()
            if any(word in user_message_lower for word in ['pickup', 'pick up', 'pick-up', 'from']):
                context['address_type'] = 'pickup'
                return {
                    'message': "What's the new pickup address?",
                    'next_state': 'address_update',
                    'context': {**context, 'step': 'get_new_address'},
                    'continue_conversation': True
                }
            elif any(word in user_message_lower for word in ['delivery', 'deliver', 'to', 'destination']):
                context['address_type'] = 'delivery'
                return {
                    'message': "What's the new delivery address?",
                    'next_state': 'address_update',
                    'context': {**context, 'step': 'get_new_address'},
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I didn't understand. Please say either 'pickup address' or 'delivery address'.",
                    'next_state': 'address_update',
                    'context': context,
                    'continue_conversation': True
                }
        
        elif step == 'get_new_address':
            address_type = context.get('address_type')
            result = await self.logistics_tools.update_address(tracking_id, address_type, user_message)
            
            if result['success']:
                return {
                    'message': result['message'] + " Is there anything else I can help you with?",
                    'next_state': 'completion',
                    'context': {},
                    'continue_conversation': True
                }
            else:
                return {
                    'message': result['message'] + " Let me transfer you to a human agent.",
                    'next_state': 'transfer_human',
                    'context': context,
                    'continue_conversation': False
                }
    
    async def _handle_time_update(self, user_message: str, context: Dict) -> Dict:
        """Handle delivery time update requests"""
        tracking_id = context.get('tracking_id')
        step = context.get('step', 'get_tracking_id')
        
        if step == 'get_tracking_id':
            tracking_id = self._extract_tracking_id(user_message)
            if tracking_id:
                context['tracking_id'] = tracking_id
                context['action'] = 'update_time'
                return {
                    'message': f"I can help you change the delivery time for shipment {tracking_id}. For security, I need to verify your identity. What's your name?",
                    'next_state': 'identity_verification',
                    'context': context,
                    'continue_conversation': True
                }
            else:
                return {
                    'message': "I didn't catch your tracking ID. Could you please repeat it?",
                    'next_state': 'time_update',
                    'context': context,
                    'continue_conversation': True
                }
        
        elif step == 'get_new_time':
            # Extract date if provided, otherwise use existing date
            new_date = self._parse_date(user_message)
            result = await self.logistics_tools.update_delivery_time(tracking_id, user_message, new_date)
            
            if result['success']:
                return {
                    'message': result['message'] + " Is there anything else I can help you with?",
                    'next_state': 'completion',
                    'context': {},
                    'continue_conversation': True
                }
            else:
                return {
                    'message': result['message'] + " Let me transfer you to a human agent.",
                    'next_state': 'transfer_human',
                    'context': context,
                    'continue_conversation': False
                }
    
    def _wants_to_track(self, message: str) -> bool:
        """Detect tracking intent"""
        tracking_keywords = ['track', 'tracking', 'status', 'where is', 'locate', 'find my']
        return any(keyword in message for keyword in tracking_keywords)
    
    def _wants_to_book(self, message: str) -> bool:
        """Detect booking intent"""
        booking_keywords = ['book', 'schedule', 'send', 'new shipment', 'create']
        # Check for "ship" only if it's not part of "shipment"
        if 'ship' in message and 'shipment' not in message:
            return True
        return any(keyword in message for keyword in booking_keywords)
    
    def _wants_to_reschedule(self, message: str) -> bool:
        """Detect rescheduling intent"""
        reschedule_keywords = ['reschedule', 'delay', 'postpone', 'change date', 'move', 'reschedule']
        return any(keyword in message for keyword in reschedule_keywords)
    
    def _wants_human_agent(self, message: str) -> bool:
        """Detect request for human agent"""
        human_keywords = ['human', 'agent', 'person', 'representative', 'operator', 'transfer']
        return any(keyword in message for keyword in human_keywords) or '*' in message
    
    def _wants_to_cancel(self, message: str) -> bool:
        """Detect cancellation intent"""
        cancel_keywords = ['cancel', 'delete', 'remove', 'stop', 'abort', 'terminate']
        return any(keyword in message for keyword in cancel_keywords)
    
    def _wants_to_update_address(self, message: str) -> bool:
        """Detect address update intent"""
        address_keywords = ['change address', 'update address', 'modify address', 'new address', 
                           'different address', 'wrong address', 'pickup', 'delivery location',
                           'update my address', 'change my address', 'modify my address',
                           'update my shipment', 'modify my shipment', 'change my shipment']
        return any(keyword in message for keyword in address_keywords)
    
    def _wants_to_update_time(self, message: str) -> bool:
        """Detect time/date update intent"""
        time_keywords = ['change time', 'update time', 'different time', 'new time', 
                        'morning', 'afternoon', 'evening', 'am', 'pm', 'earlier', 'later']
        return any(keyword in message for keyword in time_keywords)
    
    def _extract_tracking_id(self, message: str) -> Optional[str]:
        """Extract tracking ID from user message"""
        # Look for 7-8 digit numbers (sometimes speech recognition misses a digit)
        pattern = r'\b(\d{7,8})\b'
        match = re.search(pattern, message)
        if match:
            tracking_id = match.group(1)
            # If 7 digits, pad with leading zero to make 8 digits
            if len(tracking_id) == 7:
                tracking_id = '0' + tracking_id
            
            # Handle common speech recognition errors (last digit dropped)
            # If ends with 00, try variants ending in 01-09
            if tracking_id.endswith('00') and len(tracking_id) == 8:
                # Try the original first, then variants
                return tracking_id
            
            return tracking_id
        return None
    
    def _format_tracking_id_for_speech(self, tracking_id: str) -> str:
        """Format tracking ID to speak slowly and clearly"""
        # Add pauses between digits for clarity
        # Example: 12345678 becomes "1-2-3-4-5-6-7-8"
        formatted = ""
        for i, digit in enumerate(tracking_id):
            if i > 0:
                formatted += "-"
            formatted += digit
        return formatted
    
    def _parse_date(self, date_string: str) -> Optional[str]:
        """Parse date from natural language to YYYY-MM-DD format"""
        try:
            from dateutil import parser
            from datetime import datetime
            import re
            
            # Clean up the date string
            date_string = date_string.lower().strip()
            
            # Handle common speech patterns
            date_string = re.sub(r'\b(\d+)(st|nd|rd|th)\b', r'\1', date_string)  # Remove ordinals
            date_string = re.sub(r'\btoday\b', datetime.now().strftime("%Y-%m-%d"), date_string)
            date_string = re.sub(r'\btomorrow\b', (datetime.now()).strftime("%Y-%m-%d"), date_string)
            
            # Parse with dateutil - default to 2025 for future dates
            parsed_date = parser.parse(date_string, fuzzy=True, default=datetime(2025, 12, 1))
            return parsed_date.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error(f"Date parsing error with dateutil: {str(e)}")
            # Fallback to simple regex patterns
            import re
            
            # Try MM/DD/YYYY or MM-DD-YYYY
            pattern = r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
            match = re.search(pattern, date_string)
            if match:
                month, day, year = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # Try common month names
            month_map = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12'
            }
            
            for month_name, month_num in month_map.items():
                if month_name in date_string.lower():
                    # Look for day number
                    day_match = re.search(r'(\d{1,2})', date_string)
                    if day_match:
                        day = day_match.group(1).zfill(2)
                        year = '2025'  # Default year for future bookings
                        return f"{year}-{month_num}-{day}"
            
            logger.warning(f"Could not parse date: {date_string}")
            return None
    
    def _format_tracking_response(self, shipment: Dict) -> str:
        """Format tracking information into a natural response"""
        status = shipment['status'].replace('_', ' ').title()
        delivery_date = shipment['delivery_date']
        city = shipment.get('city', 'your destination')
        
        response = f"I found your shipment {shipment['tracking_id']} for {shipment['customer_name']}. "
        response += f"The current status is {status}. "
        response += f"It's scheduled for delivery on {delivery_date} to {city}."
        
        return response
    
    def _transfer_to_human(self) -> Dict:
        """Handle transfer to human agent"""
        return {
            'message': "I'll transfer you to one of our human agents who can better assist you. Please hold.",
            'next_state': 'transfer_human',
            'context': {},
            'continue_conversation': False
        }