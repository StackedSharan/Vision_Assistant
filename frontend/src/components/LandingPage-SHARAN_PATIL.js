import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

function LandingPage() {
    const navigate = useNavigate();
    const [isExiting, setIsExiting] = useState(false);

    // Wrap handleAutoStart in useCallback
    const handleAutoStart = useCallback(() => {
        setIsExiting(true); // Trigger CSS animation

        // Wait for animation to finish then navigate
        setTimeout(() => {
            navigate('/dashboard');
        }, 1500); // Match CSS transition time
    }, [navigate]);

    useEffect(() => {
        // Speak instruction on load (browser policy permitting)
        const utterance = new SpeechSynthesisUtterance("Welcome to Vision Assistant.");
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);

        // Auto transition timer
        const timer = setTimeout(() => {
            handleAutoStart();
        }, 2500); // Wait 2.5s before starting transition

        return () => clearTimeout(timer);
    }, [handleAutoStart]);

    return (
        <div className={`landing-page ${isExiting ? 'slide-up' : ''}`}>
            <div className="landing-background-icons"></div>

            <div className="landing-content">
                <div className="pulse-container">
                    <div className="pulse-ring"></div>
                    <div className="pulse-ring"></div>
                    <div className="nav-icon-ball">
                        <svg className="nav-icon" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z" />
                        </svg>
                    </div>
                </div>

                <h1 className="landing-title">Vision Assistant</h1>
            </div>
        </div>
    );
}

export default LandingPage;
