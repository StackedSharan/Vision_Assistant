import re

class IntentParser:
    def __init__(self):
        self.intents = {
            "start_assistance": [r"start assistance", r"begin assistance", r"start scanning", r"start", r"begin", r"go", r"proceed"],
            "what_is_front": [r"what is in front", r"what do you see", r"describe environment", r"what is there"],
            "guide_me": [r"guide me to (.+)", r"take me to (.+)", r"how do i get to (.+)", r"navigate to (.+)", r"(canteen)", r"(architecture)"],
            "stop_navigation": [r"stop navigation", r"cancel navigation", r"stop guiding"],
            "where_am_i": [r"where am i", r"current location", r"my position"],
            "pause": [r"pause assistance", r"stop listening", r"pause"],
            "resume": [r"resume assistance", r"start listening again", r"resume"],
            "next_step": [r"next step", r"go forward", r"skip", r"step forward"],
            "repeat": [r"repeat", r"say again", r"what was that", r"previous step", r"go back"]
        }

    def parse(self, text: str):
        text = text.lower().strip()
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    data = {}
                    if intent == "guide_me":
                        data["destination"] = match.group(1)
                    return {"intent": intent, "data": data}
        
        return {"intent": "unknown", "data": {"original_text": text}}
