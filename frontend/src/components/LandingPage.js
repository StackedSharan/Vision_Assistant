import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../App.css';

const LandingPage = () => {
    const navigate = useNavigate();

    useEffect(() => {
        const speakWelcome = () => {
            const text = "Tap anywhere on the screen to begin.";
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        };

        // Small delay to ensure browser is ready
        const timer = setTimeout(speakWelcome, 500);
        return () => clearTimeout(timer);
    }, []);

    const handleEnter = () => {
        window.speechSynthesis.cancel(); // Stop speaking when leaving
        navigate('/dashboard');
    };

    return (
        <div className="landing-page" onClick={handleEnter}>
            <div className="landing-background-icons"></div>
            <div className="landing-content">
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
