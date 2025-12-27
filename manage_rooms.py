#!/usr/bin/env python3
"""
Room Management Utility
Quản lý rooms và cleanup để tránh conflict khi tạo room cùng tên
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from livekit import api

load_dotenv()

class RoomManager:
    def __init__(self):
        self.livekit_url = os.getenv("LIVEKIT_URL")
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if not all([self.livekit_url, self.api_key, self.api_secret]):
            raise ValueError("Missing LiveKit credentials in .env file")
    
    async def list_rooms(self):
        """List all active rooms"""
        lkapi = api.LiveKitAPI(
            self.livekit_url,
            self.api_key,
            self.api_secret,
        )
        
        try:
            rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
            
            if not rooms.rooms:
                print("📋 No active rooms")
                return []
            
            print(f"\n📋 Active Rooms ({len(rooms.rooms)}):")
            print("="*70)
            
            for room in rooms.rooms:
                print(f"\n🏠 Room: {room.name}")
                print(f"   SID: {room.sid}")
                print(f"   👥 Participants: {room.num_participants}")
                print(f"   📅 Created: {room.creation_time}")
                print(f"   🔴 Empty timeout: {room.empty_timeout}s")
            
            print("\n" + "="*70)
            
            await lkapi.aclose()
            return rooms.rooms
        except Exception as e:
            print(f"❌ Error listing rooms: {e}")
            await lkapi.aclose()
            return []
    
    async def delete_room(self, room_name: str):
        """Delete a specific room"""
        lkapi = api.LiveKitAPI(
            self.livekit_url,
            self.api_key,
            self.api_secret,
        )
        
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
            print(f"✅ Room '{room_name}' deleted successfully")
            await lkapi.aclose()
            return True
        except Exception as e:
            print(f"❌ Error deleting room '{room_name}': {e}")
            await lkapi.aclose()
            return False
    
    async def delete_all_rooms(self):
        """Delete all active rooms"""
        rooms = await self.list_rooms()
        
        if not rooms:
            print("No rooms to delete")
            return
        
        print(f"\n⚠️  About to delete {len(rooms)} room(s)")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() != 'yes':
            print("Cancelled")
            return
        
        lkapi = api.LiveKitAPI(
            self.livekit_url,
            self.api_key,
            self.api_secret,
        )
        
        for room in rooms:
            try:
                await lkapi.room.delete_room(api.DeleteRoomRequest(room=room.name))
                print(f"✅ Deleted room: {room.name}")
            except Exception as e:
                print(f"❌ Failed to delete {room.name}: {e}")
        
        await lkapi.aclose()
        print("\n✅ Cleanup complete!")
    
    async def list_participants(self, room_name: str):
        """List participants in a specific room"""
        lkapi = api.LiveKitAPI(
            self.livekit_url,
            self.api_key,
            self.api_secret,
        )
        
        try:
            participants = await lkapi.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            
            if not participants.participants:
                print(f"📋 No participants in room '{room_name}'")
                await lkapi.aclose()
                return []
            
            print(f"\n👥 Participants in '{room_name}':")
            print("="*70)
            
            for p in participants.participants:
                print(f"\n👤 Identity: {p.identity}")
                print(f"   Name: {p.name}")
                print(f"   SID: {p.sid}")
                print(f"   State: {p.state}")
                print(f"   Is agent: {p.is_publisher and 'agent' in p.identity.lower()}")
            
            print("\n" + "="*70)
            
            await lkapi.aclose()
            return participants.participants
        except Exception as e:
            print(f"❌ Error listing participants: {e}")
            await lkapi.aclose()
            return []
    
    async def remove_participant(self, room_name: str, participant_identity: str):
        """Remove a specific participant from room"""
        lkapi = api.LiveKitAPI(
            self.livekit_url,
            self.api_key,
            self.api_secret,
        )
        
        try:
            await lkapi.room.remove_participant(
                api.RoomParticipantIdentity(
                    room=room_name,
                    identity=participant_identity
                )
            )
            print(f"✅ Removed participant '{participant_identity}' from room '{room_name}'")
            await lkapi.aclose()
            return True
        except Exception as e:
            print(f"❌ Error removing participant: {e}")
            await lkapi.aclose()
            return False


async def main():
    manager = RoomManager()
    
    if len(sys.argv) < 2:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║                Room Management Utility                        ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
    python3 manage_rooms.py <command> [arguments]

Commands:
    list                           - List all active rooms
    delete <room_name>             - Delete a specific room
    delete-all                     - Delete all active rooms
    participants <room_name>       - List participants in a room
    remove <room_name> <identity>  - Remove participant from room

Examples:
    python3 manage_rooms.py list
    python3 manage_rooms.py delete my-old-room
    python3 manage_rooms.py delete-all
    python3 manage_rooms.py participants test-room
    python3 manage_rooms.py remove test-room agent-bot-123

💡 Tip: Delete old rooms before creating new ones with the same name
        to avoid bot conflicts!
""")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        await manager.list_rooms()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 manage_rooms.py delete <room_name>")
            return
        room_name = sys.argv[2]
        await manager.delete_room(room_name)
    
    elif command == "delete-all":
        await manager.delete_all_rooms()
    
    elif command == "participants":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 manage_rooms.py participants <room_name>")
            return
        room_name = sys.argv[2]
        await manager.list_participants(room_name)
    
    elif command == "remove":
        if len(sys.argv) < 4:
            print("❌ Usage: python3 manage_rooms.py remove <room_name> <identity>")
            return
        room_name = sys.argv[2]
        identity = sys.argv[3]
        await manager.remove_participant(room_name, identity)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run without arguments to see available commands")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")

