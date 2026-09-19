"""Google Gemini Multimodal Live API Client for JARVIS.

Connects to gemini-3.1-flash-live-preview via WebSockets using google-genai SDK.
Handles:
- Bidirectional low-latency audio streaming (16kHz in, 24kHz out)
- Real-time barge-in and server-side interruption detection
- Automatic Tool Execution (OS actions, application launcher, screen vision)
- State transitions (idle, listening, thinking, speaking) for HUD animation
"""

import asyncio
import base64
import os
from typing import Optional, Callable, Dict, Any

from google import genai
from google.genai import types

from ..tools import dispatch_tool_call
from .audio_manager import AudioManager

class LiveClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.1-flash-live-preview",
        voice_name: str = "Puck",
        system_instruction: str = "You are JARVIS, a concise, polite Windows voice assistant.",
        audio_manager: Optional[AudioManager] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        on_transcript: Optional[Callable[[str, str], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.voice_name = voice_name
        self.system_instruction = system_instruction
        self.audio_manager = audio_manager
        self.on_state_change = on_state_change
        self.on_transcript = on_transcript
        self.on_dismiss = on_dismiss
        self.resumption_handle = None

        self._session = None
        self._is_running = False
        self._pending_dismissal = False
        self._client = None
        self._current_state = "idle"

    def set_state(self, state: str):
        """Update current agent state and notify listeners (e.g. HUD)."""
        self._current_state = state
        if self.on_state_change:
            self.on_state_change(state)

    def _init_client(self):
        """Initialize Google GenAI client."""
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please provide it in environment or .env file."
            )
        self._client = genai.Client(api_key=self.api_key)

    async def run(self):
        """Start and maintain the bidirectional Live Session."""
        self._init_client()
        self._is_running = True
        self._pending_dismissal = False
        self.resumption_handle = None
        self.set_state("connecting")

        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=self.system_instruction)]
            ),
            tools=[{"function_declarations": self._build_function_declarations()}],
        )

        try:
            async with self._client.aio.live.connect(model=self.model, config=config) as session:
                self._session = session
                self.set_state("listening")
                
                # Run sender and receiver concurrently
                send_task = asyncio.create_task(self._audio_sender_loop(session))
                receive_task = asyncio.create_task(self._receiver_loop(session))

                done, pending = await asyncio.wait(
                    [send_task, receive_task],
                    return_when=asyncio.FIRST_EXCEPTION
                )

                for task in pending:
                    task.cancel()
                for task in done:
                    exc = task.exception()
                    if exc:
                        raise exc

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[LiveClient] Live Session error: {e}")
            raise e
        finally:
            self._is_running = False
            self._session = None
            self.set_state("idle")

    def _build_function_declarations(self):
        """Build JSON function declarations for tools dispatch."""
        return [
            {
                "name": "set_volume",
                "description": "Adjust Windows system volume.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "Action: 'up', 'down', 'mute', or 'unmute'."},
                        "steps": {"type": "INTEGER", "description": "Steps to change volume (default 5)."}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "lock_workstation",
                "description": "Lock the Windows PC workstation immediately.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "system_power",
                "description": "Put PC to sleep, initiate shutdown/restart, or cancel pending shutdown.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "'sleep', 'shutdown', 'restart', or 'cancel_shutdown'."},
                        "confirm": {"type": "BOOLEAN", "description": "User confirmed the action."}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "get_system_status",
                "description": "Get current CPU utilization, RAM usage, and battery status.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "launch_application",
                "description": "Launch a Windows desktop application (e.g. chrome, vscode, spotify, notepad, calc, wt).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "app_name": {"type": "STRING", "description": "Name or executable of the application."}
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "open_url",
                "description": "Open a website or link in default browser.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "url": {"type": "STRING", "description": "URL to open (e.g. https://github.com)."}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "capture_screen",
                "description": "Take an instant in-memory screenshot of user's active display for visual analysis.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "quality": {"type": "INTEGER", "description": "JPEG compression quality (1-100). Default 80."}
                    }
                }
            },
            {
                "name": "execute_powershell",
                "description": "Execute a non-destructive PowerShell command for developer automation.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "PowerShell command string to run."}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "open_path",
                "description": "Open a file or folder in Windows File Explorer.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "Absolute or relative path to a file or directory."}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "dismiss_session",
                "description": "Put JARVIS into standby mode ONLY when the user explicitly and directly says goodbye, tells you to sleep, or dismisses you (e.g. 'I will call you later', 'goodbye', 'bye', 'see you later', 'that is all', 'cukup', 'dah jarvis', 'tidur jarvis', 'standby'). NEVER invoke this tool when the user is starting a conversation, greeting, saying hello, or asking a question.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "farewell_phrase": {"type": "STRING", "description": "The explicit parting words spoken by the user."}
                    },
                    "required": ["farewell_phrase"]
                }
            },
            {
                "name": "write_to_notepad",
                "description": "Write or create notes/text in Windows Notepad and display them to the user (e.g. 'write in notepad', 'tulis di notepad', 'catat di notepad', 'buat catatan').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "The exact text content to write into Notepad."},
                        "title": {"type": "STRING", "description": "Optional title or filename for the note (default: 'JARVIS_Note')."}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "type_text",
                "description": "Simulate typing text into the currently active focused application or window using keyboard simulation.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "The exact text string to type into the active window."}
                    },
                    "required": ["text"]
                }
            }
        ]

    async def _audio_sender_loop(self, session):
        """Continuously stream microphone audio chunks to Gemini."""
        if not self.audio_manager:
            return

        try:
            async for chunk in self.audio_manager.stream_input():
                if not self._is_running:
                    break
                
                # Send real-time audio chunk (16kHz PCM)
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=chunk,
                        mime_type="audio/pcm;rate=16000"
                    )
                )
        except Exception:
            pass

    async def _receiver_loop(self, session):
        """Receive responses, audio streams, and tool call requests continuously across multiple turns."""
        while self._is_running:
            try:
                async for response in session.receive():
                    if not self._is_running:
                        break

                    # Capture session resumption handle for subsequent turns
                    if response.session_resumption_update and response.session_resumption_update.new_handle:
                        self.resumption_handle = response.session_resumption_update.new_handle

                    server_content = response.server_content
                    if server_content:
                        # Check for Barge-in / Interruption
                        if getattr(server_content, "interrupted", False):
                            if self.audio_manager:
                                self.audio_manager.interrupt()
                            self.set_state("listening")
                            continue

                        # Process Model Turn
                        model_turn = server_content.model_turn
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                # Spoken Audio from JARVIS
                                if hasattr(part, "inline_data") and part.inline_data:
                                    audio_data = part.inline_data.data
                                    if audio_data and self.audio_manager:
                                        if isinstance(audio_data, str):
                                            audio_data = base64.b64decode(audio_data)
                                        self.set_state("speaking")
                                        self.audio_manager.play_audio(audio_data)

                                # Text Transcript / Thinking
                                if hasattr(part, "text") and part.text:
                                    if self.on_transcript:
                                        self.on_transcript("JARVIS", part.text)

                        if getattr(server_content, "turn_complete", False):
                            # Wait for output speaker playback to drain
                            while self.audio_manager and self.audio_manager.is_playing:
                                await asyncio.sleep(0.08)
                            await asyncio.sleep(0.15)
                            
                            # If user requested dismissal, end session cleanly into standby
                            if self._pending_dismissal:
                                print("[LiveClient] Dismissal requested by user. Entering standby.")
                                self._pending_dismissal = False
                                self.resumption_handle = None
                                self.stop()
                                break

                            self.set_state("listening")
                            # Break inner iterator to call session.receive() for the next turn
                            break

                    # Handle Tool Calls
                    tool_call = response.tool_call
                    if tool_call and tool_call.function_calls:
                        self.set_state("thinking")
                        responses = []
                        for call in tool_call.function_calls:
                            call_name = call.name
                            call_args = dict(call.args) if call.args else {}
                            
                            if call_name == "dismiss_session":
                                farewell = str(call_args.get("farewell_phrase", "") or call_args.get("reason", "")).lower().strip()
                                valid_dismissal_keywords = (
                                    "bye", "goodbye", "later", "cukup", "tidur", "standby",
                                    "see you", "dah", "dadah", "selesai", "istirahat", "stop",
                                    "sleep", "close session", "dismiss"
                                )
                                if any(kw in farewell for kw in valid_dismissal_keywords):
                                    self._pending_dismissal = True
                                    result = await asyncio.to_thread(dispatch_tool_call, call_name, call_args)
                                else:
                                    print(f"[LiveClient] Dismissal rejected. Spurious farewell: '{farewell}'")
                                    self._pending_dismissal = False
                                    result = {
                                        "status": "ignored",
                                        "message": "Dismissal rejected: the user is asking a question, giving a command, or continuing the session, not dismissing you. Do not say goodbye. Fulfill the user's request, Sir."
                                    }
                            else:
                                # Execute tool in a background thread to prevent blocking asyncio loop
                                result = await asyncio.to_thread(dispatch_tool_call, call_name, call_args)
                            
                            # Special screen vision handling: stream image blob if captured
                            image_bytes = result.pop("_bytes", None)
                            if image_bytes:
                                await session.send_realtime_input(
                                    video=types.Blob(
                                        data=image_bytes,
                                        mime_type="image/jpeg"
                                    )
                                )

                            responses.append(
                                types.FunctionResponse(
                                    name=call_name,
                                    id=call.id,
                                    response={"result": result}
                                )
                            )

                        # Send tool results back to the session
                        await session.send_tool_response(function_responses=responses)
                        self.set_state("speaking")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[LiveClient] Receiver error: {e}")
                break

    def stop(self):
        """Terminate the live session and clear session resumption handle."""
        self._is_running = False
        self._pending_dismissal = False
        self.resumption_handle = None
        self.set_state("idle")
