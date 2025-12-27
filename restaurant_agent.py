import logging
import json
import unicodedata
from dataclasses import dataclass, field
from typing import Annotated, Optional
import requests
import asyncio
import ssl

import yaml
from dotenv import load_dotenv
from pydantic import Field
from aiohttp import web

from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.plugins import deepgram, openai, silero, google, elevenlabs, soniox
from livekit.api import AccessToken, VideoGrants, LiveKitAPI, CreateAgentDispatchRequest, CreateRoomRequest, DeleteRoomRequest
# cartesia not needed - removed to avoid import error

import os
from dotenv import load_dotenv
load_dotenv()

# ==================== TOKEN SERVER CONFIG ====================
TOKEN_SERVER_PORT = 8089
AGENT_NAME = "restaurant-bot"

logger = logging.getLogger("restaurant-bot")
logger.setLevel(logging.INFO)

# ==================== TOKEN SERVER FUNCTIONS ====================
async def handle_token_request(request: web.Request) -> web.Response:
    """
    Create room + dispatch agent + generate token (ALL IN ONE).
    
    Flow:
    1. Create room on LiveKit server
    2. Dispatch agent to room
    3. Generate JWT token for user
    """
    try:
        room_name = request.query.get('room', 'default-room')
        participant_name = request.query.get('name', 'user')
        
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        livekit_url = os.getenv("LIVEKIT_URL")
        
        if not api_key or not api_secret:
            return web.json_response(
                {"error": "Missing LIVEKIT credentials"}, 
                status=500
            )
        
        metadata = {"participant_name": participant_name}
        
        # ====== STEP 1: Create room on LiveKit server ======
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            try:
                await lk_api.room.create_room(
                    CreateRoomRequest(
                        name=room_name,
                        metadata=json.dumps(metadata),
                        empty_timeout=300,  # Auto-delete after 5 min empty
                        max_participants=10
                    )
                )
                logger.info(f"✅ Room created: {room_name}")
            except Exception as e:
                logger.warning(f"⚠️ Room may already exist: {e}")
            
            # ====== STEP 2: Dispatch agent to room ======
            try:
                logger.info(f"🤖 Dispatching agent '{AGENT_NAME}' to room {room_name}...")
                await lk_api.agent_dispatch.create_dispatch(
                    CreateAgentDispatchRequest(
                        agent_name=AGENT_NAME,
                        room=room_name,
                        metadata=json.dumps(metadata)
                    )
                )
                logger.info(f"✅ Agent '{AGENT_NAME}' dispatched to room {room_name}!")
            except Exception as dispatch_error:
                logger.error(f"❌ Agent dispatch failed: {dispatch_error}")
        
        # ====== STEP 3: Generate JWT token ======
        token = AccessToken(api_key, api_secret)
        token.with_identity(participant_name)
        token.with_name(participant_name)
        token.with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        
        jwt_token = token.to_jwt()
        
        logger.info(f"✅ Token generated | Room: {room_name} | User: {participant_name}")
        
        response = web.json_response({
            "token": jwt_token,
            "url": livekit_url,
            "room": room_name,
            "name": participant_name
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"❌ Error generating token: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_delete_room(request: web.Request) -> web.Response:
    """Delete a LiveKit room when user disconnects"""
    try:
        room_name = request.match_info.get('room_name')
        if not room_name:
            return web.json_response({"error": "Room name required"}, status=400)
        
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        livekit_url = os.getenv("LIVEKIT_URL")
        
        logger.info(f"🗑️ Deleting room: {room_name}")
        
        async with LiveKitAPI(livekit_url, api_key, api_secret) as lk_api:
            await lk_api.room.delete_room(
                DeleteRoomRequest(room=room_name)
            )
        
        logger.info(f"✅ Room deleted: {room_name}")
        
        response = web.json_response({
            "success": True,
            "message": f"Room '{room_name}' deleted",
            "room_name": room_name
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"❌ Error deleting room: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_cors(request: web.Request) -> web.Response:
    """Handle CORS preflight requests"""
    return web.Response(
        status=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    )


async def start_token_server():
    """Start the HTTP token server"""
    app = web.Application()
    app.router.add_get('/api/token', handle_token_request)
    app.router.add_delete('/api/room/{room_name}', handle_delete_room)
    app.router.add_options('/api/token', handle_cors)
    app.router.add_options('/api/room/{room_name}', handle_cors)
    
    # Check for SSL certs
    cert_file = os.path.join(os.path.dirname(__file__), '.cert/server-cert.pem')
    key_file = os.path.join(os.path.dirname(__file__), '.cert/server-key.pem')
    
    ssl_context = None
    protocol = "http"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        protocol = "https"
        logger.info("🔒 Token Server: HTTPS enabled")
    else:
        logger.info("⚠️ Token Server: Running without HTTPS")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', TOKEN_SERVER_PORT, ssl_context=ssl_context)
    await site.start()
    
    logger.info(f"🚀 Token Server running at: {protocol}://0.0.0.0:{TOKEN_SERVER_PORT}")
    logger.info(f"🔗 Token endpoint: {protocol}://localhost:{TOKEN_SERVER_PORT}/api/token?room=<room>&name=<name>")


# ==================== RESTAURANT AGENT ====================
# This example demonstrates a multi-agent system where tasks are delegated to sub-agents
# based on the user's request.
#
# The user is initially connected to a greeter, and depending on their need, the call is
# handed off to other agents that could help with the more specific tasks.


@dataclass
class UserData:
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

    reservation_time: Optional[str] = None

    order: Optional[dict[str, int]] = None  # Changed to dict: {item_name: quantity}

    customer_credit_card: Optional[str] = None
    customer_credit_card_expiry: Optional[str] = None
    customer_credit_card_cvv: Optional[str] = None

    expense: Optional[float] = None
    checked_out: Optional[bool] = None

    agents: dict[str, Agent] = field(default_factory=dict)
    prev_agent: Optional[Agent] = None
    inventory: dict = field(default_factory=dict)  # Add inventory tracking

    def summarize(self) -> str:
        data = {
            "customer_name": self.customer_name or "unknown",
            "customer_phone": self.customer_phone or "unknown",
            "reservation_time": self.reservation_time or "unknown",
            "order": self.order or "unknown",
            "credit_card": {
                "number": self.customer_credit_card or "unknown",
                "expiry": self.customer_credit_card_expiry or "unknown",
                "cvv": self.customer_credit_card_cvv or "unknown",
            }
            if self.customer_credit_card
            else None,
            "expense": self.expense or "unknown",
            "checked_out": self.checked_out or False,
        }
        # summarize in yaml performs better than json
        return yaml.dump(data)


RunContext_T = RunContext[UserData]

INVENTORY_FILE = "/home/sotatek/Documents/Uyen/demo_voice/inventory.json"

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Helper function to send Telegram notifications
def send_telegram_notification(message: str) -> bool:
    """Send notification to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram not configured. Skipping notification.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Telegram notification sent successfully")
            return True
        else:
            logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram notification: {e}")
        return False

# Inventory management functions
def load_inventory() -> dict:
    """Load inventory from JSON file"""
    try:
        logger.info(f"📂 Loading inventory from: {INVENTORY_FILE}")
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            inventory = json.load(f)
        logger.info(f"✅ Inventory loaded successfully: {list(inventory.keys())}")
        return inventory
    except FileNotFoundError:
        logger.error(f"❌ Inventory file not found: {INVENTORY_FILE}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in inventory file: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Error loading inventory: {e}")
        return {}

def save_inventory(inventory: dict) -> None:
    """Save inventory to JSON file"""
    try:
        with open(INVENTORY_FILE, 'w') as f:
            json.dump(inventory, f, indent=2)
        logger.info("Inventory saved successfully")
    except Exception as e:
        logger.error(f"Failed to save inventory: {e}")

def normalize_item_name(name: str) -> str:
    """Normalize item name: remove quotes, accents, convert to lowercase"""
    # Remove quotes
    name = name.strip().strip("'\"")
    # Convert to lowercase
    name = name.lower()
    # Remove Vietnamese accents
    nfd = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return name

def find_inventory_key(item_name: str, inventory: dict) -> Optional[str]:
    """Find matching inventory key for item name (supports partial matching)"""
    normalized_input = normalize_item_name(item_name)
    logger.info(f"🔍 Looking for '{item_name}' → normalized: '{normalized_input}'")
    
    # Try exact match
    if normalized_input in inventory:
        logger.info(f"✅ Exact match found: '{normalized_input}'")
        return normalized_input
    
    # Try partial match - check if input is in any key or vice versa
    for key in inventory.keys():
        if normalized_input in key or key in normalized_input:
            logger.info(f"✅ Partial match found: '{key}' matches '{normalized_input}'")
            return key
        # Check if they start with the same words
        if normalized_input.startswith(key) or key.startswith(normalized_input):
            logger.info(f"✅ Prefix match found: '{key}' matches '{normalized_input}'")
            return key
    
    logger.warning(f"❌ No match found for '{normalized_input}' in inventory keys: {list(inventory.keys())}")
    return None

def check_availability(inventory: dict, order: dict[str, int]) -> tuple[bool, str]:
    """
    Check if items are available in sufficient quantity
    Returns: (is_available, message)
    """
    for item_name, quantity in order.items():
        item_key = find_inventory_key(item_name, inventory)
        
        if item_key is None:
            return False, f"Sản phẩm '{item_name}' không có trong menu / Item '{item_name}' is not in the menu"
        
        available = inventory[item_key]["quantity"]
        display_name = inventory[item_key]["name"]
        
        if available < quantity:
            return False, (
                f"Xin lỗi, chỉ còn {available} {display_name}, không đủ {quantity} / "
                f"Sorry, only {available} {display_name} available, not enough for {quantity}"
            )
    
    return True, "Đủ hàng / Available"

def deduct_inventory(inventory: dict, order: dict[str, int]) -> dict:
    """Deduct ordered items from inventory"""
    for item_name, quantity in order.items():
        item_key = find_inventory_key(item_name, inventory)
        if item_key and item_key in inventory:
            inventory[item_key]["quantity"] -= quantity
            logger.info(f"✅ Deducted {quantity}x {inventory[item_key]['name']}, remaining: {inventory[item_key]['quantity']}")
    return inventory


# common functions


@function_tool()
async def update_name(
    name: Annotated[str, Field(description="The customer's name")],
    context: RunContext_T,
) -> str:
    """Called when the user provides their name.
    Confirm the spelling with the user before calling the function."""
    userdata = context.userdata
    userdata.customer_name = name
    return f"The name is updated to {name}"


@function_tool()
async def update_phone(
    phone: Annotated[str, Field(description="The customer's phone number")],
    context: RunContext_T,
) -> str:
    """Called when the user provides their phone number.
    Confirm the spelling with the user before calling the function."""
    userdata = context.userdata
    userdata.customer_phone = phone
    return f"The phone number is updated to {phone}"


@function_tool()
async def to_greeter(context: RunContext_T) -> Agent:
    """Called when user asks any unrelated questions or requests
    any other services not in your job description."""
    curr_agent: BaseAgent = context.session.current_agent
    return await curr_agent._transfer_to_agent("greeter", context)


class BaseAgent(Agent):
    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"entering task {agent_name}")

        userdata: UserData = self.session.userdata
        chat_ctx = self.chat_ctx.copy()

        # add the previous agent's chat history to the current agent
        if isinstance(userdata.prev_agent, Agent):
            truncated_chat_ctx = userdata.prev_agent.chat_ctx.copy(
                exclude_instructions=True, exclude_function_call=False
            ).truncate(max_items=6)
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in truncated_chat_ctx.items if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)

        # add an instructions including the user data as assistant message
        chat_ctx.add_message(
            role="system",  # role=system works for OpenAI's LLM and Realtime API
            content=(
                f"You are {agent_name} agent. Current user data is {userdata.summarize()}\n\n"
                "🚨 LANGUAGE RULE: Look at the user's previous messages.\n"
                "- If they contain Vietnamese words (Xin chào, tôi, muốn, đặt, etc.) → SPEAK VIETNAMESE ONLY\n"
                "- If they are in English → SPEAK ENGLISH ONLY\n"
                "- NEVER mix languages. Your ENTIRE response must be in ONE language."
            ),
        )
        await self.update_chat_ctx(chat_ctx)
        self.session.generate_reply(tool_choice="none")

    async def _transfer_to_agent(self, name: str, context: RunContext_T) -> tuple[Agent, str]:
        userdata = context.userdata
        current_agent = context.session.current_agent
        next_agent = userdata.agents[name]
        userdata.prev_agent = current_agent

        return next_agent, f"Transferring to {name}."


class Greeter(BaseAgent):
    def __init__(self, menu: str) -> None:
        # Define tools first so they can be passed to super().__init__
        @function_tool()
        async def to_reservation_tool(context: RunContext_T) -> tuple['Agent', str]:
            """Called when user wants to make or update a reservation.
            This function handles transitioning to the reservation agent
            who will collect the necessary details like reservation time,
            customer name and phone number."""
            return await self._transfer_to_agent("reservation", context)
        
        @function_tool()
        async def to_takeaway_tool(context: RunContext_T) -> tuple['Agent', str]:
            """Called when the user wants to place a takeaway order.
            This includes handling orders for pickup, delivery, or when the user wants to
            proceed to checkout with their existing order."""
            return await self._transfer_to_agent("takeaway", context)
        
        super().__init__(
            instructions=(
                "🚨🚨🚨 ABSOLUTE CRITICAL RULE - LANGUAGE MATCHING 🚨🚨🚨\n\n"
                "RULE #1: IF USER INPUT CONTAINS VIETNAMESE WORDS → RESPOND 100% IN VIETNAMESE\n"
                "RULE #2: IF USER INPUT IS IN ENGLISH → RESPOND 100% IN ENGLISH\n"
                "RULE #3: NEVER, EVER MIX LANGUAGES IN YOUR RESPONSE\n\n"
                "Examples:\n"
                "❌ WRONG: User: 'Xin chào' → You: 'Hello! How can I help you?'\n"
                "✅ CORRECT: User: 'Xin chào' → You: 'Xin chào! Tôi có thể giúp gì cho bạn?'\n\n"
                "❌ WRONG: User: 'Hello' → You: 'Xin chào! What do you need?'\n"
                "✅ CORRECT: User: 'Hello' → You: 'Hello! How can I help you today?'\n\n"
                f"You are a friendly Sota Yummy restaurant receptionist. Our Menu:\n{menu}\n"
                "Ask if they want to make a reservation or place a takeaway order, then use tools to transfer."
            ),
            tools=[to_reservation_tool, to_takeaway_tool],
            llm=google.LLM(
                model="gemini-2.5-flash",
                api_key=os.getenv("GEMINI_API_KEY")
            ),
            tts=elevenlabs.TTS(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id="Xb7hH8MSUJpSbSDYk0k2",
                model="eleven_turbo_v2_5"
            ),
        )
        self.menu = menu



class Reservation(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "🚨🚨🚨 IF USER SPEAKS VIETNAMESE → YOU SPEAK VIETNAMESE\n"
                "🚨🚨🚨 IF USER SPEAKS ENGLISH → YOU SPEAK ENGLISH\n"
                "🚨🚨🚨 NEVER MIX LANGUAGES\n\n"
                "You are a reservation agent. Ask for: time, name, phone.\n"
                "Then confirm the details."
            ),
            tools=[update_name, update_phone, to_greeter],
            tts=elevenlabs.TTS(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id="Xb7hH8MSUJpSbSDYk0k2",
                model="eleven_turbo_v2_5"
            ),
        )

    @function_tool()
    async def update_reservation_time(
        self,
        time: Annotated[str, Field(description="The reservation time")],
        context: RunContext_T,
    ) -> str:
        """Called when the user provides their reservation time.
        Confirm the time with the user before calling the function."""
        userdata = context.userdata
        userdata.reservation_time = time
        return f"The reservation time is updated to {time}"

    @function_tool()
    async def confirm_reservation(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """Called when the user confirms the reservation."""
        userdata = context.userdata
        if not userdata.customer_name or not userdata.customer_phone:
            return "Please provide your name and phone number first."

        if not userdata.reservation_time:
            return "Please provide reservation time first."

        # Send Telegram notification for reservation
        telegram_message = (
            f"📅 <b>ĐẶT BÀN MỚI</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Khách hàng:</b> {userdata.customer_name}\n"
            f"📱 <b>Số điện thoại:</b> {userdata.customer_phone}\n"
            f"🕐 <b>Thời gian:</b> {userdata.reservation_time}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Đặt bàn đã được xác nhận"
        )
        send_telegram_notification(telegram_message)

        return await self._transfer_to_agent("greeter", context)


class Takeaway(BaseAgent):
    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
                "🚨🚨🚨 IF USER SPEAKS VIETNAMESE → YOU SPEAK VIETNAMESE\n"
                "🚨🚨🚨 IF USER SPEAKS ENGLISH → YOU SPEAK ENGLISH\n"
                "🚨🚨🚨 NEVER MIX LANGUAGES\n\n"
                f"You take orders at Sota Yummy. Our Menu:\n{menu}\n"
                "IMPORTANT: Ask what they want AND HOW MANY of each item.\n"
                "Example questions:\n"
                "- 'How many Cheeseburgers would you like?'\n"
                "- 'How many Cappuccinos?'\n"
                "- 'Would you like any desserts with that?'\n"
                "Then clarify quantities and confirm the full order with quantities."
            ),
            tools=[to_greeter],
            tts=elevenlabs.TTS(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id="Xb7hH8MSUJpSbSDYk0k2",
                model="eleven_turbo_v2_5"
            ),
        )

    @function_tool()
    async def update_order(
        self,
        items: Annotated[
            dict[str, int], 
            Field(description="The items and quantities of the order as a dictionary, e.g. {'Pizza': 2, 'Coffee': 1}")
        ],
        context: RunContext_T,
    ) -> str:
        """Called when the user creates or updates their order.
        The items should be a dictionary with item names as keys and quantities as values."""
        userdata = context.userdata
        
        # Debug logging
        logger.info(f"🛒 Order requested: {items}")
        logger.info(f"📦 Current inventory: {userdata.inventory}")
        
        # Check if inventory is loaded
        if not userdata.inventory:
            logger.error("❌ Inventory is empty!")
            return "❌ Lỗi hệ thống: Không thể kiểm tra kho hàng / System error: Cannot check inventory"
        
        # Check if items are available in sufficient quantity
        is_available, message = check_availability(userdata.inventory, items)
        
        if not is_available:
            logger.warning(f"❌ Not available: {message}")
            return f"❌ {message}"
        
        # Update order if available
        userdata.order = items
        order_summary = ", ".join([f"{qty}x {item}" for item, qty in items.items()])
        logger.info(f"✅ Order updated: {order_summary}")
        return f"✅ Đơn hàng đã cập nhật / Order updated: {order_summary}"

    @function_tool()
    async def check_stock(
        self,
        item_name: Annotated[str, Field(description="The item name to check stock for")],
        context: RunContext_T,
    ) -> str:
        """Called when the user asks about stock availability or how many items are left."""
        userdata = context.userdata
        item_key = find_inventory_key(item_name, userdata.inventory)
        
        if item_key and item_key in userdata.inventory:
            quantity = userdata.inventory[item_key]["quantity"]
            name = userdata.inventory[item_key]["name"]
            return f"Còn {quantity} {name} / We have {quantity} {name} available"
        else:
            return f"Không tìm thấy '{item_name}' trong menu / '{item_name}' not found in menu"

    @function_tool()
    async def to_checkout(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """Called when the user confirms the order."""
        userdata = context.userdata
        if not userdata.order:
            return "No takeaway order found. Please make an order first."

        return await self._transfer_to_agent("checkout", context)


class Checkout(BaseAgent):
    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
                "🚨🚨🚨 IF USER SPEAKS VIETNAMESE → YOU SPEAK VIETNAMESE\n"
                "🚨🚨🚨 IF USER SPEAKS ENGLISH → YOU SPEAK ENGLISH\n"
                "🚨🚨🚨 NEVER MIX LANGUAGES\n\n"
                f"You handle checkout at Sota Yummy. Our Menu:\n{menu}\n"
                "Confirm the total expense (in USD) and collect customer's name and phone number.\n"
                "Example: 'Your total is $45.99'\n"
                "Then complete the checkout process."
            ),
            tools=[update_name, update_phone, to_greeter],
            tts=elevenlabs.TTS(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id="Xb7hH8MSUJpSbSDYk0k2",
                model="eleven_turbo_v2_5"
            ),
        )

    @function_tool()
    async def confirm_expense(
        self,
        expense: Annotated[float, Field(description="The expense of the order")],
        context: RunContext_T,
    ) -> str:
        """Called when the user confirms the expense."""
        userdata = context.userdata
        userdata.expense = expense
        return f"The expense is confirmed to be {expense}"

    @function_tool()
    async def confirm_checkout(self, context: RunContext_T) -> str | tuple[Agent, str]:
        """Called when the user confirms the checkout and completes the order."""
        userdata = context.userdata
        if not userdata.expense:
            return "Please confirm the expense first."

        if not userdata.customer_name or not userdata.customer_phone:
            return "Please provide your name and phone number first."

        # Deduct items from inventory after successful checkout
        if userdata.order:
            userdata.inventory = deduct_inventory(userdata.inventory, userdata.order)
            save_inventory(userdata.inventory)
            logger.info(f"Inventory updated after checkout: {userdata.order}")

        # Send Telegram notification with order details
        order_items = "\n".join([f"  • {qty}x {item}" for item, qty in userdata.order.items()]) if userdata.order else "Không có"
        telegram_message = (
            f"🍜 <b>ĐƠN HÀNG MỚI</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Khách hàng:</b> {userdata.customer_name}\n"
            f"📱 <b>Số điện thoại:</b> {userdata.customer_phone}\n"
            f"\n📦 <b>Đơn hàng:</b>\n{order_items}\n"
            f"\n💰 <b>Tổng tiền:</b> {userdata.expense:,.0f} VNĐ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ Đơn hàng đã được xác nhận"
        )
        send_telegram_notification(telegram_message)

        userdata.checked_out = True
        return await to_greeter(context)

    @function_tool()
    async def to_takeaway(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the user wants to update their order."""
        return await self._transfer_to_agent("takeaway", context)


server = AgentServer()


@server.rtc_session(agent_name="restaurant-bot")
async def entrypoint(ctx: JobContext):
    """
    Explicit Dispatch Mode - Agent joins only when dispatched via API
    Dispatched automatically by token server when user joins room
    """
    logger.info(f"🎯 Agent dispatched to room: {ctx.room.name}")
    
    # Connect to the room first (required for rtc_session)
    await ctx.connect(auto_subscribe="audio_only")
    
    menu = """
    ========== BREAKFAST (20 items) ==========
    Sunny Side Up Eggs: $9.99 | Fluffy Pancakes: $11.99 | Belgian Waffles: $12.99
    Avocado Toast: $13.50 | French Toast: $10.99 | Eggs Benedict: $14.99
    Veggie Omelette: $11.50 | Breakfast Burrito: $12.99 | Açaí Bowl: $13.99
    Greek Yogurt Parfait: $8.99 | Smoked Salmon Bagel: $15.99 | Butter Croissant: $6.99
    Breakfast Sandwich: $10.50 | Steel Cut Oatmeal: $7.99 | Crispy Hash Browns: $5.99
    Shakshuka: $13.99 | Nutella Crepes: $11.99 | Full English Breakfast: $18.99
    Huevos Rancheros: $12.99 | Banana Nut Bread: $6.50

    ========== MAIN DISHES (20 items) ==========
    Classic Cheeseburger: $14.99 | Margherita Pizza: $18.99 | Grilled Salmon: $26.99
    Pasta Carbonara: $16.99 | Ribeye Steak: $34.99 | Chicken Alfredo: $17.50
    Fish & Chips: $18.99 | BBQ Baby Back Ribs: $28.99 | Chicken Parmesan: $19.99
    Street Tacos: $14.99 | Lobster Tail: $22.99 | Spaghetti Bolognese: $15.99
    Grilled Lamb Chops: $32.99 | Shrimp Scampi: $24.99 | Herb Roasted Chicken: $21.99
    Grilled Pork Chops: $23.99 | Butter Chicken: $18.99 | Pad Thai: $16.99
    Beef Lasagna: $17.99 | Grilled Chicken Salad: $13.99

    ========== DRINKS (20 items) ==========
    Mint Lemonade: $5.99 | Classic Mojito: $12.99 | Fresh Orange Juice: $6.50
    Iced Caramel Latte: $5.50 | Mixed Berry Smoothie: $7.99 | Matcha Latte: $5.99
    Classic Margarita: $11.99 | Chocolate Milkshake: $8.99 | Double Espresso: $3.99
    Piña Colada: $13.99 | Hot Chocolate: $5.50 | Cappuccino: $4.99
    Green Detox Smoothie: $8.50 | Red Wine Sangria: $10.99 | Peach Iced Tea: $4.50
    Mango Lassi: $6.99 | Whiskey Sour: $13.99 | Vanilla Latte: $5.50
    Fresh Coconut Water: $5.99 | Arnold Palmer: $4.99

    ========== DESSERTS (20 items) ==========
    Chocolate Gelato: $8.99 | NY Cheesecake: $9.99 | Glazed Donuts: $6.99
    Classic Tiramisu: $10.99 | Crème Brûlée: $11.50 | Molten Lava Cake: $12.99
    Fresh Fruit Tart: $8.99 | Red Velvet Cake: $9.50 | Apple Pie: $7.99
    Vanilla Panna Cotta: $9.99 | French Macarons (6pc): $12.99 | Fudge Brownies: $6.99
    Churros: $7.50 | Banana Split: $10.99 | Key Lime Pie: $8.99
    Profiteroles: $9.50 | Carrot Cake: $8.50 | Affogato: $7.99
    Chocolate Chip Cookies: $5.99 | Mango Sticky Rice: $9.99
    """
    
    # Load inventory
    inventory = load_inventory()
    
    userdata = UserData()
    userdata.inventory = inventory
    userdata.agents.update(
        {
            "greeter": Greeter(menu),
            "reservation": Reservation(),
            "takeaway": Takeaway(menu),
            "checkout": Checkout(menu),
        }
    )
    
    session = AgentSession[UserData](
        userdata=userdata,
        # Google Gemini model - direct API
        llm=google.LLM(
            model="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY")
        ),
        # Soniox STT with language detection for Vietnamese and English
        stt=soniox.STT(
            api_key=os.getenv("SONIOX_API_KEY"),
        ),
        tts=openai.TTS(
            voice="nova",
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
        vad=silero.VAD.load(),
        max_tool_steps=1,
    )
    
    logger.info(f"✅ Agent ready in room: {ctx.room.name}")
    
    await session.start(
        agent=userdata.agents["greeter"],
        room=ctx.room,
    )


async def main():
    """Start both Token Server and Agent Server"""
    # Start Token Server first
    await start_token_server()
    logger.info("="*60)
    logger.info("🍜 Restaurant Bot - All-in-One Server")
    logger.info("="*60)
    logger.info(f"📡 Token Server: https://localhost:{TOKEN_SERVER_PORT}/api/token")
    logger.info(f"🤖 Agent Name: {AGENT_NAME}")
    logger.info("="*60)


if __name__ == "__main__":
    import sys
    
    # Check if running with cli args (dev mode)
    if len(sys.argv) > 1:
        # Start token server in background, then run agent
        import threading
        
        def run_token_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_token_server())
            loop.run_forever()
        
        # Start token server in background thread
        token_thread = threading.Thread(target=run_token_server, daemon=True)
        token_thread.start()
        
        logger.info("="*60)
        logger.info("🍜 Restaurant Bot - All-in-One Server")
        logger.info("="*60)
        logger.info(f"📡 Token Server: https://localhost:{TOKEN_SERVER_PORT}/api/token")
        logger.info(f"🤖 Agent Name: {AGENT_NAME}")
        logger.info("="*60)
        
        # Run agent with CLI
        cli.run_app(server)
    else:
        # Just run token server standalone
        asyncio.run(main()) 