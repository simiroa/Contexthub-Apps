import threading
from PySide6.QtCore import QObject, Signal
from ai_text_lab_service import AITextLabService

class StreamWorker(QObject):
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, service: AITextLabService, model: str, system_prompt: str, prompt: str):
        super().__init__()
        self.service = service
        self.model = model
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.cancel_event = threading.Event()

    def run(self):
        try:
            if self.model.startswith("✦ "):
                self.service.stream_gemini(self.model, self.system_prompt, self.prompt, self.chunk_received.emit, self.cancel_event)
            else:
                self.service.stream_ollama(self.model, self.system_prompt, self.prompt, self.chunk_received.emit, self.cancel_event)
            self.finished.emit("Completed")
        except Exception as e:
            self.error.emit(str(e))
