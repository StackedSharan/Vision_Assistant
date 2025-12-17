import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

function LandingPage() {
    const navigate = useNavigate();
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
        </div>
    );
}

export default LandingPage;
