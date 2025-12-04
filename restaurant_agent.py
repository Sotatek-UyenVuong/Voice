import logging
import json
from dataclasses import dataclass, field
from typing import Annotated, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field

from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, RunContext
from livekit.plugins import cartesia, deepgram, openai, silero, google, elevenlabs
from livekit.plugins import soniox

import os
from dotenv import load_dotenv
load_dotenv()
# from livekit.plugins import noise_cancellation

# This example demonstrates a multi-agent system where tasks are delegated to sub-agents
# based on the user's request.
#
# The user is initially connected to a greeter, and depending on their need, the call is
# handed off to other agents that could help with the more specific tasks.
# This helps to keep each agent focused on the task at hand, and also reduces costs
# since only a subset of the tools are used at any given time.


logger = logging.getLogger("restaurant-example")
logger.setLevel(logging.INFO)

load_dotenv()

voices = {
    "greeter": "794f9389-aac1-45b6-b726-9d9369183238",
    "reservation": "156fb8d2-335b-4950-9cb3-a2d33befec77",
    "takeaway": "6f84f4b8-58a2-430c-8c79-688dad597532",
    "checkout": "39b376fc-488e-4d0c-8b37-e00b72059fdd",
}


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

# Inventory management functions
def load_inventory() -> dict:
    """Load inventory from JSON file"""
    try:
        with open(INVENTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Inventory file not found: {INVENTORY_FILE}")
        return {}

def save_inventory(inventory: dict) -> None:
    """Save inventory to JSON file"""
    try:
        with open(INVENTORY_FILE, 'w') as f:
            json.dump(inventory, f, indent=2)
        logger.info("Inventory saved successfully")
    except Exception as e:
        logger.error(f"Failed to save inventory: {e}")

def check_availability(inventory: dict, order: dict[str, int]) -> tuple[bool, str]:
    """
    Check if items are available in sufficient quantity
    Returns: (is_available, message)
    """
    for item_name, quantity in order.items():
        item_key = item_name.lower()
        if item_key not in inventory:
            return False, f"Sản phẩm '{item_name}' không có trong menu / Item '{item_name}' is not in the menu"
        
        available = inventory[item_key]["quantity"]
        if available < quantity:
            return False, (
                f"Xin lỗi, chỉ còn {available} {item_name}, không đủ {quantity} / "
                f"Sorry, only {available} {item_name} available, not enough for {quantity}"
            )
    
    return True, "Đủ hàng / Available"

def deduct_inventory(inventory: dict, order: dict[str, int]) -> dict:
    """Deduct ordered items from inventory"""
    for item_name, quantity in order.items():
        item_key = item_name.lower()
        if item_key in inventory:
            inventory[item_key]["quantity"] -= quantity
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
                f"You are a friendly Vietnamese restaurant receptionist. Thực đơn / Menu: {menu}\n"
                "Ask if they want reservation (đặt bàn) or takeaway order (gọi món mang đi), then use tools to transfer."
            ),
            llm=google.LLM(
                model="gemini-2.5-pro",
                api_key=os.getenv("GEMINI_API_KEY")
            ),
            tts=elevenlabs.TTS(
                api_key=os.getenv("ELEVENLABS_API_KEY"),
                voice_id="Xb7hH8MSUJpSbSDYk0k2",
                model="eleven_turbo_v2_5"
            ),
        )
        self.menu = menu

    @function_tool()
    async def to_reservation(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when user wants to make or update a reservation.
        This function handles transitioning to the reservation agent
        who will collect the necessary details like reservation time,
        customer name and phone number."""
        return await self._transfer_to_agent("reservation", context)

    @function_tool()
    async def to_takeaway(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the user wants to place a takeaway order.
        This includes handling orders for pickup, delivery, or when the user wants to
        proceed to checkout with their existing order."""
        return await self._transfer_to_agent("takeaway", context)


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

        return await self._transfer_to_agent("greeter", context)


class Takeaway(BaseAgent):
    def __init__(self, menu: str) -> None:
        super().__init__(
            instructions=(
                "🚨🚨🚨 IF USER SPEAKS VIETNAMESE → YOU SPEAK VIETNAMESE\n"
                "🚨🚨🚨 IF USER SPEAKS ENGLISH → YOU SPEAK ENGLISH\n"
                "🚨🚨🚨 NEVER MIX LANGUAGES\n\n"
                f"You take orders. Thực đơn / Menu: {menu}\n"
                "IMPORTANT: Ask what they want AND HOW MANY of each item.\n"
                "Example questions:\n"
                "- 'Bạn muốn mấy tô Phở?' / 'How many Pho bowls would you like?'\n"
                "- 'Bạn muốn mấy ly Cà phê?' / 'How many Coffees?'\n"
                "- 'Bạn muốn mấy phần Gỏi cuốn?' / 'How many portions of spring rolls?'\n"
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
        
        # Check if items are available in sufficient quantity
        is_available, message = check_availability(userdata.inventory, items)
        
        if not is_available:
            return f"❌ {message}"
        
        # Update order if available
        userdata.order = items
        order_summary = ", ".join([f"{qty}x {item}" for item, qty in items.items()])
        return f"✅ Đơn hàng đã cập nhật / Order updated: {order_summary}"

    @function_tool()
    async def check_stock(
        self,
        item_name: Annotated[str, Field(description="The item name to check stock for")],
        context: RunContext_T,
    ) -> str:
        """Called when the user asks about stock availability or how many items are left."""
        userdata = context.userdata
        item_key = item_name.lower()
        
        if item_key in userdata.inventory:
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
                f"You handle checkout. Thực đơn / Menu: {menu}\n"
                "Confirm the total expense (in VND) and collect customer's name and phone number.\n"
                "Example: 'Tổng cộng 75.000đ' / 'Total is 75,000 VND'\n"
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

        userdata.checked_out = True
        return await to_greeter(context)

    @function_tool()
    async def to_takeaway(self, context: RunContext_T) -> tuple[Agent, str]:
        """Called when the user wants to update their order."""
        return await self._transfer_to_agent("takeaway", context)


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    menu = "Phở: 35k, Bún bò Huế: 40k, Bánh mì: 25k, Cơm tấm: 35k, Gỏi cuốn: 30k, Cà phê sữa đá: 20k"
    
    # Load inventory from file
    inventory = load_inventory()
    logger.info(f"Loaded inventory: {inventory}")
    
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
            model="gemini-2.5-pro",
            api_key=os.getenv("GEMINI_API_KEY")
        ),
        # Soniox STT with language detection for Vietnamese and English
        stt=soniox.STT(
            api_key=os.getenv("SONIOX_API_KEY"),
        ),
        tts=elevenlabs.TTS(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id="Xb7hH8MSUJpSbSDYk0k2",
            model="eleven_turbo_v2_5"
        ),
        vad=silero.VAD.load(),
        max_tool_steps=5,
    )

    await session.start(
        agent=userdata.agents["greeter"],
        room=ctx.room,
    )

    # await agent.say("Welcome to our restaurant! How may I assist you today?")


if __name__ == "__main__":
    cli.run_app(server) 