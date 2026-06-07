"""
wakeword.py — Detector de palavra de ativação usando Google Speech Recognition
Muito mais preciso, funciona perfeitamente com português brasileiro.
"""

import subprocess
import time
import os
from pathlib import Path

BASE_DIR    = Path(__file__).parent
MAIN_SCRIPT = BASE_DIR / "main.py"
PYTHON_312  = r"C:\Users\Guaraci\AppData\Local\Programs\Python\Python312\python.exe"
JARVIS_DIR  = str(BASE_DIR)

WAKE_WORDS       = ["jarvis", "jardim", "jarbas"]
COOLDOWN_SECONDS = 30  # 30 segundos entre ativações


_jarvis_process  = None
_last_activation = 0.0


def is_jarvis_running() -> bool:
    global _jarvis_process
    if _jarvis_process is None:
        return False
    return _jarvis_process.poll() is None


def launch_jarvis():
    global _jarvis_process, _last_activation
    now = time.time()
    if now - _last_activation < COOLDOWN_SECONDS:
        return
    if is_jarvis_running():
        return
    print("[WakeWord] ✅ Abrindo Jarvis...")
    _last_activation = now
    _jarvis_process = subprocess.Popen(
        [PYTHON_312, str(MAIN_SCRIPT)],
        cwd=JARVIS_DIR,
        creationflags=0x08000000,
        env={**os.environ, "PYTHONPATH": JARVIS_DIR},
    )


def listen_loop():
    try:
        import speech_recognition as sr
    except ImportError:
        print("[WakeWord] ERRO: pip install SpeechRecognition")
        return

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 3000       # ignora ruído de fundo baixo
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    mic = sr.Microphone()

    print("[WakeWord] 👂 Calibrando microfone...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print(f"[WakeWord] ✅ Pronto! Threshold: {recognizer.energy_threshold:.0f}")
    print("[WakeWord] Diga 'Jarvis' para ativar.")

    while True:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)

            try:
                text = recognizer.recognize_google(audio, language="pt-BR").lower().strip()
                print(f"[WakeWord] Ouvi: '{text}'")
                if any(w in text for w in WAKE_WORDS):
                    launch_jarvis()
            except sr.UnknownValueError:
                pass  # não entendeu, ignora
            except sr.RequestError as e:
                print(f"[WakeWord] Erro de conexão: {e}")
                time.sleep(2)

        except sr.WaitTimeoutError:
            pass  # silêncio, continua ouvindo
        except Exception as e:
            print(f"[WakeWord] Erro: {e}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        listen_loop()
    except KeyboardInterrupt:
        print("\n[WakeWord] Encerrado.")
