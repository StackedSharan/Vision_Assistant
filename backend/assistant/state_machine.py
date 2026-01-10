from enum import Enum, auto

class State(Enum):
    IDLE = auto()
    LISTENING = auto()
    ENVIRONMENT_SCAN = auto()
    NAVIGATION_MODE = auto()
    ALERT_MODE = auto()
    PAUSE = auto()

class VisionAssistantFSM:
    def __init__(self, tts_engine):
        self.state = State.IDLE
        self.tts = tts_engine
        self.navigation_active = False
        self.hazard_detected = False

    def transition_to(self, new_state: State):
        if self.state == new_state:
            return

        print(f"Transitioning from {self.state} to {new_state}")
        
        # ALERT_MODE has highest priority
        if self.state == State.ALERT_MODE and new_state != State.IDLE and self.hazard_detected:
            print("Cannot transition out of ALERT_MODE while hazard persists")
            return

        self.state = new_state
        self.on_state_enter(new_state)

    def on_state_enter(self, state: State):
        if state == State.LISTENING:
            self.tts.speak("Listening")
        elif state == State.ENVIRONMENT_SCAN:
            self.tts.speak("Scanning environment")
        elif state == State.NAVIGATION_MODE:
            self.tts.speak("Navigation mode started")
            self.navigation_active = True
        elif state == State.ALERT_MODE:
            # We don't speak here because ALERT_MODE usually comes with a specific warning
            pass
        elif state == State.IDLE:
            self.navigation_active = False

    def handle_event(self, event, data=None):
        if event == "VOICE_COMMAND":
            intent = data.get("intent")
            if intent == "start_assistance":
                self.transition_to(State.ENVIRONMENT_SCAN)
            elif intent == "guide_me":
                self.transition_to(State.NAVIGATION_MODE)
            elif intent == "stop_navigation":
                self.transition_to(State.ENVIRONMENT_SCAN)
            elif intent == "pause":
                self.transition_to(State.PAUSE)
            elif intent == "resume":
                self.transition_to(State.ENVIRONMENT_SCAN)
            elif intent == "where_am_i":
                # Handle where am i (status update, don't necessarily change state)
                pass

        elif event == "HAZARD_DETECTED":
            self.hazard_detected = True
            self.transition_to(State.ALERT_MODE)

        elif event == "HAZARD_CLEARED":
            self.hazard_detected = False
            if self.navigation_active:
                self.tts.speak("Hazard cleared. Resuming navigation.")
                self.transition_to(State.NAVIGATION_MODE)
            else:
                self.tts.speak("Hazard cleared. Resuming scan.")
                self.transition_to(State.ENVIRONMENT_SCAN)

        elif event == "USER_STOPPED":
            if self.state == State.NAVIGATION_MODE:
                self.tts.speak("You have stopped. Navigation paused.")
                # We stay in NAVIGATION_MODE but logic will handle the pause
