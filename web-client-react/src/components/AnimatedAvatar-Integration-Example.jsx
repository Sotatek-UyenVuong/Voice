/**
 * ============================================
 * EXAMPLE: How to integrate AnimatedAvatar into App.jsx
 * ============================================
 * 
 * Copy đoạn code này vào App.jsx của bạn
 */

import { useEffect, useState, useRef } from 'react';
import { LiveKitRoom, useVoiceAssistant, RoomAudioRenderer } from '@livekit/components-react';
import AnimatedAvatar from './components/AnimatedAvatar';
import '@livekit/components-styles';
import './App.css';

function VoiceInterface() {
  const { state, audioTrack } = useVoiceAssistant();
  const [userAudioTrack, setUserAudioTrack] = useState(null);

  // Get user's microphone audio track
  useEffect(() => {
    const setupUserAudio = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioTrack = stream.getAudioTracks()[0];
        setUserAudioTrack(audioTrack);
      } catch (error) {
        console.error('Error getting user audio:', error);
      }
    };

    if (state === 'connected') {
      setupUserAudio();
    }

    return () => {
      if (userAudioTrack) {
        userAudioTrack.stop();
      }
    };
  }, [state]);

  return (
    <div className="voice-interface">
      <h1>🍜 Restaurant Voice Bot</h1>

      {/* Status */}
      <div className="status-bar">
        <span className={`status-indicator ${state}`}>
          {state === 'connected' ? '🟢 Connected' : 
           state === 'listening' ? '🎤 Listening' :
           state === 'speaking' ? '🔊 Speaking' : '⚪ Idle'}
        </span>
      </div>

      {/* Avatars Section */}
      <div className="avatars-container">
        {/* Agent Avatar */}
        <div className="avatar-section agent">
          <h3>🤖 Restaurant Bot</h3>
          <AnimatedAvatar 
            audioTrack={audioTrack}  // Agent's audio track
            isAgent={true}
          />
          <p className="avatar-label">
            {state === 'speaking' ? '🗣️ Speaking...' : '👂 Listening...'}
          </p>
        </div>

        {/* User Avatar */}
        <div className="avatar-section user">
          <h3>👤 You</h3>
          <AnimatedAvatar 
            audioTrack={userAudioTrack}  // User's audio track
            isAgent={false}
          />
          <p className="avatar-label">
            {state === 'listening' ? '🎤 Speaking...' : '👂 Listening...'}
          </p>
        </div>
      </div>

      {/* Audio Renderer */}
      <RoomAudioRenderer />
    </div>
  );
}

function App() {
  const [token, setToken] = useState('');
  const [url, setUrl] = useState('');
  const [roomName, setRoomName] = useState('');
  const [participantName, setParticipantName] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  // Generate unique room name
  const generateRoomName = () => {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 5);
    return `restaurant-${timestamp}-${random}`;
  };

  useEffect(() => {
    setRoomName(generateRoomName());
    setParticipantName(`User-${Math.random().toString(36).substr(2, 5)}`);
  }, []);

  const handleConnect = async () => {
    try {
      // Fetch token from server
      const response = await fetch(
        `http://localhost:8089/api/token?room=${roomName}&name=${participantName}`
      );
      const data = await response.json();
      
      setToken(data.token);
      setUrl(data.url);
      setIsConnected(true);
    } catch (error) {
      console.error('Error connecting:', error);
      alert('Failed to connect. Make sure server is running.');
    }
  };

  const handleDisconnect = () => {
    setIsConnected(false);
    setToken('');
    setUrl('');
    setRoomName(generateRoomName());
  };

  if (!isConnected) {
    return (
      <div className="connect-screen">
        <h1>🍜 Vietnamese Restaurant Voice Bot</h1>
        <div className="connect-form">
          <input
            type="text"
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
            placeholder="Room Name"
          />
          <input
            type="text"
            value={participantName}
            onChange={(e) => setParticipantName(e.target.value)}
            placeholder="Your Name"
          />
          <button onClick={handleConnect}>
            🎙️ Connect
          </button>
        </div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={handleDisconnect}
    >
      <VoiceInterface />
    </LiveKitRoom>
  );
}

export default App;


/**
 * ============================================
 * ADD TO App.css:
 * ============================================
 */

/*
.avatars-container {
  display: flex;
  gap: 50px;
  justify-content: center;
  align-items: flex-start;
  padding: 30px;
  flex-wrap: wrap;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border-radius: 20px;
  min-width: 250px;
}

.avatar-section.agent {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border: 2px solid #667eea;
}

.avatar-section.user {
  background: linear-gradient(135deg, rgba(72, 187, 120, 0.05) 0%, rgba(56, 178, 172, 0.05) 100%);
  border: 2px solid #48bb78;
}

.avatar-label {
  font-size: 14px;
  color: #666;
  margin: 0;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 20px;
}

.status-bar {
  text-align: center;
  padding: 15px;
  margin-bottom: 20px;
}

.status-indicator {
  padding: 10px 20px;
  border-radius: 25px;
  font-weight: 600;
  display: inline-block;
}

.status-indicator.connected {
  background: #c6f6d5;
  color: #22543d;
}

.status-indicator.listening {
  background: #bee3f8;
  color: #2c5282;
}

.status-indicator.speaking {
  background: #fed7d7;
  color: #742a2a;
}
*/


