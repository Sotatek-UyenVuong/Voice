import { useState, useEffect, useRef } from 'react';
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, useRoomContext } from '@livekit/components-react';
import '@livekit/components-styles';
import './App.css';
import AnimatedAvatar from './components/AnimatedAvatar';

const SERVER_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8089' 
  : 'https://192.168.200.22:8089';

function VoiceAssistantUI() {
  const { state, audioTrack } = useVoiceAssistant(); // Get audioTrack from agent
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [messages, setMessages] = useState([]);
  const [currentUserText, setCurrentUserText] = useState('');
  const [currentAiText, setCurrentAiText] = useState('');
  const messagesEndRef = useRef(null);
  const room = useRoomContext();
  const prevStateRef = useRef(state);
  const savedUserTextRef = useRef('');
  const savedAiTextRef = useRef('');

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentUserText, currentAiText]);

  // Track conversation from room events
  useEffect(() => {
    if (!room) return;

    const handleTranscriptionReceived = (
      segments,
      participant
    ) => {
      const text = segments.map(s => s.text).join(' ').trim();
      console.log('📝 Transcription:', text, 'isLocal:', participant?.isLocal, 'state:', state);
      if (!text) return;
      
      const isLocal = participant?.isLocal;

      if (isLocal) {
        // User speaking
        setCurrentUserText(prev => {
          const newText = text;
          console.log('👤 User text updated:', newText);
          return newText !== prev ? newText : prev;
        });
      } else {
        // AI speaking
        setCurrentAiText(prev => {
          const newText = text;
          console.log('🤖 AI text updated:', newText);
          
          // Check if this is a new sentence (text got shorter or completely different)
          if (prev && newText !== prev) {
            const isNewSentence = newText.length < prev.length * 0.7 || 
                                  !newText.startsWith(prev.substring(0, Math.min(20, prev.length)));
            
            if (isNewSentence) {
              // Save the previous sentence before starting a new one
              console.log('🔄 New sentence detected, saving previous:', prev);
              setMessages(msgs => [...msgs, { type: 'ai', text: prev }]);
            }
          }
          
          return newText !== prev ? newText : prev;
        });
      }
    };

    // Debug: Log all room events
    const handleParticipantConnected = (participant) => {
      console.log('👋 Participant connected:', participant.identity, participant.isLocal ? '(local)' : '(remote)');
    };

    const handleParticipantDisconnected = (participant) => {
      console.log('👋 Participant disconnected:', participant.identity);
    };

    const handleDisconnected = () => {
      console.log('🔌 Room disconnected event fired');
    };

    room.on('transcriptionReceived', handleTranscriptionReceived);
    room.on('participantConnected', handleParticipantConnected);
    room.on('participantDisconnected', handleParticipantDisconnected);
    room.on('disconnected', handleDisconnected);

    // Log initial state
    console.log('🏠 Room connected, participants:', room.remoteParticipants.size);

    return () => {
      room.off('transcriptionReceived', handleTranscriptionReceived);
      room.off('participantConnected', handleParticipantConnected);
      room.off('participantDisconnected', handleParticipantDisconnected);
      room.off('disconnected', handleDisconnected);
    };
  }, [room, state]);

  // Update refs continuously when text changes
  useEffect(() => {
    savedUserTextRef.current = currentUserText;
  }, [currentUserText]);
  
  useEffect(() => {
    savedAiTextRef.current = currentAiText;
  }, [currentAiText]);
  
  // Save messages when state changes
  useEffect(() => {
    const prevState = prevStateRef.current;
    prevStateRef.current = state;
    
    if (prevState === 'listening' && state === 'thinking') {
      const textToSave = savedUserTextRef.current;
      if (textToSave) {
        setTimeout(() => {
          setMessages(prev => [...prev, { type: 'user', text: textToSave }]);
          setCurrentUserText('');
        }, 0);
      }
    }
    
    // When state changes to thinking, save any current AI text
    if (state === 'thinking' && savedAiTextRef.current) {
      const textToSave = savedAiTextRef.current;
      setTimeout(() => {
        setMessages(prev => [...prev, { type: 'ai', text: textToSave }]);
        setCurrentAiText('');
      }, 0);
    }
    
    if (prevState === 'speaking' && state === 'idle') {
      const textToSave = savedAiTextRef.current;
      if (textToSave) {
        setTimeout(() => {
          setMessages(prev => [...prev, { type: 'ai', text: textToSave }]);
          setCurrentAiText('');
        }, 0);
      }
    }
  }, [state]);

  const toggleMicrophone = () => {
    if (room) {
      const newState = !isMicEnabled;
      room.localParticipant.setMicrophoneEnabled(newState);
      setIsMicEnabled(newState);
    }
  };

  return (
    <div className="chat-container">
      {/* Header with Avatar */}
      <div className="chat-header">
        <div className="header-left">
          <button className="back-button">←</button>
          <div>
            <div className="header-title">🍜 AI Voice</div>
            <div className="header-subtitle">Bistro Bliss Voice Assistant</div>
          </div>
        </div>
        
        {/* Animated Avatar */}
        <div className="header-avatar">
          <AnimatedAvatar 
            audioTrack={audioTrack}
            isAgent={true}
          />
          <div className="avatar-status">
            {state === 'speaking' && '🗣️ Speaking...'}
            {state === 'listening' && '👂 Listening...'}
            {state === 'thinking' && '🤔 Thinking...'}
            {state === 'idle' && '💤 Ready...'}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 && !currentUserText && !currentAiText && (
          <div className="empty-state">
            <div className="mic-icon">🎤</div>
            <h3>Start Conversation</h3>
            <p>Start talking to order or make a reservation</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div className="message-bubble">
              {msg.text}
            </div>
          </div>
        ))}

        {/* Current user speech (while listening) */}
        {currentUserText && state === 'listening' && (
          <div className="message user">
            <div className="message-bubble typing">
              {currentUserText}
              <span className="cursor">|</span>
            </div>
          </div>
        )}

        {/* Loading when AI is thinking */}
        {state === 'thinking' && (
          <div className="message ai">
            <div className="message-bubble typing">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        {/* Current AI speech (while speaking) */}
        {currentAiText && (
          <div className="message ai">
            <div className="message-bubble typing">
              {currentAiText}
              {state === 'speaking' && <span className="cursor">|</span>}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Status Bar */}
      <div className="status-bar">
        <button 
          className={`mic-toggle-button ${!isMicEnabled ? 'disabled' : ''}`}
          onClick={toggleMicrophone}
          title={isMicEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          <svg 
            viewBox="0 0 24 24" 
            width="28" 
            height="28"
            fill="currentColor"
          >
            {isMicEnabled ? (
              // Microphone ON - classic vintage microphone
              <>
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </>
            ) : (
              // Microphone OFF - with slash
              <>
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                <line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" strokeWidth="2.5"/>
              </>
            )}
          </svg>
        </button>

        <div className={`status-indicator ${state} ${!isMicEnabled ? 'mic-off' : ''}`}>
          <div className="status-dot"></div>
          <span className="status-text">
            {!isMicEnabled && 'Mic Off'}
            {isMicEnabled && state === 'listening' && 'Listening...'}
            {isMicEnabled && state === 'thinking' && 'Processing...'}
            {isMicEnabled && state === 'speaking' && 'Speaking...'}
            {isMicEnabled && state === 'idle' && 'Press to talk'}
          </span>
        </div>

        {/* Voice visualizer */}
        {isMicEnabled && (state === 'listening' || state === 'speaking') && (
          <div className="voice-visualizer">
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
            <div className="bar"></div>
          </div>
        )}

        {/* Disconnect button */}
        <button 
          className="disconnect-button"
          onClick={() => {
            console.log('🔌 Disconnect button clicked');
            room.disconnect();
          }}
          title="Disconnect"
        >
          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11H7v-2h10v2z"/>
          </svg>
          End
        </button>
      </div>

      <RoomAudioRenderer />
    </div>
  );
}

// Helper function to generate unique room name with timestamp
const generateUniqueRoomName = (prefix = 'room') => {
  const timestamp = Date.now();
  const randomStr = Math.random().toString(36).substr(2, 5);
  return `${prefix}-${timestamp}-${randomStr}`;
};

function App() {
  // Use unique room name by default (with timestamp)
  const [roomName, setRoomName] = useState(() => generateUniqueRoomName('restaurant'));
  const [userName, setUserName] = useState('web-user');
  const [token, setToken] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Function to generate new unique room name
  const generateNewRoomName = () => {
    setRoomName(generateUniqueRoomName('restaurant'));
  };

  const generateToken = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await fetch(
        `${SERVER_URL}/api/token?room=${encodeURIComponent(roomName)}&name=${encodeURIComponent(userName)}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to generate token. Make sure server.py is running!');
      }
      
      const data = await response.json();
      setToken(data.token);
      setIsConnected(true);
    } catch (err) {
      setError(err.message);
      console.error('Error generating token:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const disconnect = async () => {
    console.log('🔌 Disconnecting from room:', roomName);
    
    // Call API to delete room
    try {
      const response = await fetch(
        `${SERVER_URL}/api/room/${encodeURIComponent(roomName)}`,
        { method: 'DELETE' }
      );
      if (response.ok) {
        console.log('✅ Room deleted successfully');
      }
    } catch (err) {
      console.warn('⚠️ Could not delete room:', err);
    }
    
    // Reset state
    setToken('');
    setIsConnected(false);
    // Generate new room name for next connection
    setRoomName(generateUniqueRoomName('restaurant'));
    console.log('✅ Disconnected successfully');
  };

  if (!isConnected) {
    return (
      <div className="app">
        <div className="connect-container">
          <h1>🍽️ Bistro Bliss</h1>
          <p className="subtitle">Restaurant Voice Assistant</p>
          
          <div className="menu-info">
            <h3>📋 Our Menu</h3>
            <div className="menu-items" style={{ fontSize: '13px', lineHeight: '1.6' }}>
              <p><strong>Breakfast:</strong> Pancakes $11.99 | Eggs Benedict $14.99</p>
              <p><strong>Mains:</strong> Cheeseburger $14.99 | Ribeye $34.99</p>
              <p><strong>Drinks:</strong> Cappuccino $4.99 | Mojito $12.99</p>
              <p><strong>Desserts:</strong> Tiramisu $10.99 | Cheesecake $9.99</p>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="roomName">
              Room Name 
              <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>
                ✨ Auto-generated unique name
              </span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                id="roomName"
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="Enter room name"
                style={{ flex: 1 }}
              />
              <button 
                onClick={generateNewRoomName}
                className="generate-room-button"
                type="button"
                title="Generate new room name"
              >
                🔄
              </button>
            </div>
            <small style={{ color: '#888', fontSize: '11px', marginTop: '4px', display: 'block' }}>
              💡 Unique room name → Bot auto-joins each session
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="userName">Your Name</label>
            <input
              id="userName"
              type="text"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="Enter your name"
            />
          </div>

          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          <button 
            onClick={generateToken} 
            disabled={isLoading || !roomName}
            className="connect-button"
          >
            {isLoading ? '⏳ Connecting...' : '🎤 Connect & Talk'}
          </button>

          <div className="info-box">
            <h4>💡 Instructions:</h4>
            <ol>
              <li>Click "Connect & Talk"</li>
              <li>Allow microphone access</li>
              <li>Start ordering!</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <LiveKitRoom
        token={token}
        serverUrl="wss://uyen-7wr708uf.livekit.cloud"
        connect={true}
        audio={true}
        video={false}
        onDisconnected={disconnect}
        className="room-container"
      >
        <VoiceAssistantUI />
      </LiveKitRoom>
    </div>
  );
}

export default App;
