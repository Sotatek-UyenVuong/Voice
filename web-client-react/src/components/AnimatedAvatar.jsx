import { useState, useEffect, useRef } from 'react';
import './AnimatedAvatar.css';

/**
 * Animated Avatar với 6 states miệng
 * Volume-based mouth animation
 */
const AnimatedAvatar = ({ audioTrack, isAgent = false }) => {
  const [mouthState, setMouthState] = useState(0); // 0-5 states
  const animationFrameRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);

  useEffect(() => {
    if (!audioTrack) {
      setMouthState(0); // Đóng miệng khi không có audio
      return;
    }

    // Setup Audio Context và Analyser
    const setupAudioAnalysis = async () => {
      try {
        // Lấy MediaStream từ audioTrack
        const mediaStream = new MediaStream([audioTrack.mediaStreamTrack]);
        
        // Create Audio Context
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        const audioContext = audioContextRef.current;
        
        // Create Analyser Node
        analyserRef.current = audioContext.createAnalyser();
        analyserRef.current.fftSize = 256;
        analyserRef.current.smoothingTimeConstant = 0.8;
        
        // Connect source to analyser
        const source = audioContext.createMediaStreamSource(mediaStream);
        source.connect(analyserRef.current);
        
        // Start animation loop
        animateMouth();
      } catch (error) {
        console.error('Error setting up audio analysis:', error);
      }
    };

    setupAudioAnalysis();

    return () => {
      // Cleanup
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [audioTrack]);

  const animateMouth = () => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    const updateMouth = () => {
      // Get audio data
      analyser.getByteFrequencyData(dataArray);
      
      // Calculate average volume (0-255)
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      
      // Normalize volume to 0-1
      const volume = average / 255;
      
      // Map volume to mouth states (0-5)
      // Thresholds for each state
      let newState = 0;
      if (volume > 0.5) {
        newState = 5; // Mở tối đa
      } else if (volume > 0.4) {
        newState = 4; // Mở rất rộng
      } else if (volume > 0.3) {
        newState = 3; // Mở rộng
      } else if (volume > 0.2) {
        newState = 2; // Mở vừa
      } else if (volume > 0.1) {
        newState = 1; // Hơi mở
      } else {
        newState = 0; // Đóng
      }
      
      setMouthState(newState);
      
      // Continue animation loop
      animationFrameRef.current = requestAnimationFrame(updateMouth);
    };
    
    updateMouth();
  };

  return (
    <div className={`animated-avatar ${isAgent ? 'agent' : 'user'}`}>
      <div className="avatar-container">
        {/* Animated mouth - 6 states */}
        <img 
          src={`/avatar/mouth_${mouthState}.png`}
          alt="Avatar"
          className="avatar-mouth"
          style={{
            transition: 'opacity 0.1s ease-in-out'
          }}
          onError={(e) => {
            // Fallback to emoji if images not found
            e.target.style.display = 'none';
            e.target.parentElement.innerHTML = `
              <div style="font-size: 60px; text-align: center;">
                ${mouthState > 3 ? '😮' : mouthState > 1 ? '😊' : '🙂'}
              </div>
            `;
          }}
        />
      </div>
      
      {/* Volume indicator (optional - for debugging) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="volume-debug">
          State: {mouthState}
        </div>
      )}
    </div>
  );
};

export default AnimatedAvatar;

