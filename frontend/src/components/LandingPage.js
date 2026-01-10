import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function LandingPage() {
    const navigate = useNavigate();
<<<<<<< HEAD
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
=======
    const [hasInteracted, setHasInteracted] = useState(false);

    useEffect(() => {
        // Attempt auto-play greeting
        const speakGreeting = () => {
            const utterance = new SpeechSynthesisUtterance("Welcome to Vision Assistant.");
            utterance.rate = 1.0;
            utterance.onend = () => {
                navigate('/dashboard');
            };
            window.speechSynthesis.speak(utterance);
        };

        // Check if we can speak immediately (some browsers allow if triggered by recent interaction or simple reload)
        // But reliably, we might need a tap.
        // Let's try to speak.
        speakGreeting();

        // If speech fails or is blocked, the user sees the button.
    }, [navigate]);

    const handleStart = () => {
        setHasInteracted(true);
        const utterance = new SpeechSynthesisUtterance("Welcome to Vision Assistant.");
        utterance.onend = () => {
            navigate('/dashboard');
        };
        window.speechSynthesis.speak(utterance);
    };

    return (
        <div style={{
            display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
            height: '100vh', background: '#000', color: '#fff', textAlign: 'center'
        }} onClick={handleStart}>
            <h1>Vision Assistant</h1>
            <p>Tap anywhere to start</p>
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
        </div>
    );
}

export default LandingPage;
