import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../App.css';

const LandingPage = () => {
    const navigate = useNavigate();

    useEffect(() => {
        const speakWelcome = () => {
            const text = "Welcome to Vision Assistant. Please tap anywhere on the screen to enter the Dashboard.";
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        };

        // Small delay to ensure browser is ready
        const timer = setTimeout(speakWelcome, 1000);
        return () => clearTimeout(timer);
    }, []);

    const handleEnter = () => {
        window.speechSynthesis.cancel(); // Stop speaking when leaving
        navigate('/dashboard');
    };

    return (
        <div className="landing-page" onClick={handleEnter}>
            <div className="landing-content">
                <h1 className="landing-title">Vision Assistant</h1>
                <p className="landing-subtitle">Superb AI Navigation</p>
                <div className="pulse-button">
                    Tap to Start
                </div>
            </div>
        </div>
    );
};

export default LandingPage;
