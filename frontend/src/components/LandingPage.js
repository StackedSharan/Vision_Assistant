import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../App.css';

const LandingPage = () => {
    const navigate = useNavigate();
    const [isExiting, setIsExiting] = React.useState(false);

    useEffect(() => {
        const speakWelcome = () => {
            console.log("📢 Attempting to speak welcome greeting...");
            const text = "Welcome to Vision Assistant. tap anywhere on the screen to begin";

            // Cancel any pending speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9; // Slightly slower for clarity
            utterance.pitch = 1;

            utterance.onstart = () => console.log("🔊 Speech started!");
            utterance.onerror = (e) => console.error("🔇 Speech error:", e.error);

            window.speechSynthesis.speak(utterance);
        };

        // Try to speak immediately
        speakWelcome();

        // Handle case where voices aren't ready yet
        window.speechSynthesis.onvoiceschanged = () => {
            console.log("🎤 Voices changed/loaded");
            speakWelcome();
        };

        return () => {
            window.speechSynthesis.cancel();
            window.speechSynthesis.onvoiceschanged = null;
        };
    }, []);

    const handleEnter = () => {
        if (isExiting) return; // Prevent double taps

        setIsExiting(true);
        window.speechSynthesis.cancel(); // Stop speaking immediately on tap

        // Wait for animation to finish before navigating
        setTimeout(() => {
            navigate('/dashboard');
        }, 800); // 800ms match CSS animation duration
    };

    return (
        <div className="landing-page" onClick={handleEnter}>
            <div className="landing-background-icons"></div>
            <div className={`landing-content ${isExiting ? 'swipe-up-active' : ''}`}>
                <div className="pulse-container">
                    <div className="pulse-ring"></div>
                    <div className="pulse-ring"></div>
                    <div className="pulse-ring"></div>
                    <div className="nav-icon-ball">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                            <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
                        </svg>
                    </div>
                </div>
                <h1 className="landing-title">VISION ASSISTANT</h1>
            </div>
        </div>
    );
};

export default LandingPage;
