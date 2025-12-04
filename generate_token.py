#!/usr/bin/env python3
"""
Generate LiveKit access token for connecting to the voice agent.
Usage: python generate_token.py [room_name] [participant_name]
"""

import sys
import os
from livekit.api import AccessToken, VideoGrants
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_token(room_name: str, participant_name: str = "user") -> str:
    """
    Generate a LiveKit access token for a participant to join a room.
    
    Args:
        room_name: The name of the room to join
        participant_name: The name/identity of the participant
        
    Returns:
        The generated JWT token
    """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError(
            "LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env file"
        )
    
    # Create access token
    token = AccessToken(api_key, api_secret)
    token.with_identity(participant_name)
    token.with_name(participant_name)
    
    # Grant permissions
    token.with_grants(
        VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )
    )
    
    return token.to_jwt()


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_token.py [room_name] [participant_name]")
        print("\nExample:")
        print("  python generate_token.py test-room")
        print("  python generate_token.py test-room john")
        sys.exit(1)
    
    room_name = sys.argv[1]
    participant_name = sys.argv[2] if len(sys.argv) > 2 else "user"
    
    try:
        token = generate_token(room_name, participant_name)
        
        print("\n" + "="*80)
        print("✅ LiveKit Access Token Generated Successfully!")
        print("="*80)
        print(f"\nRoom Name: {room_name}")
        print(f"Participant: {participant_name}")
        print(f"\nToken:\n{token}")
        print("\n" + "="*80)
        print("\n📋 How to use this token:")
        print("\n1. Copy the token above")
        print("2. You can use it in your web client or any LiveKit client")
        print("3. Or test quickly with LiveKit CLI:")
        print(f"\n   livekit-cli join-room \\")
        print(f"     --url {os.getenv('LIVEKIT_URL')} \\")
        print(f"     --token {token}")
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error generating token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

