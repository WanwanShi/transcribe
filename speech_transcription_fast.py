import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sounddevice as sd
import soundfile as sf
import whisper
import tempfile
import os
import sys
from datetime import datetime
import queue
import platform
import numpy as np
import ssl
import urllib.request

# Fix SSL certificate issues on macOS
if platform.system() == "Darwin":
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except:
        pass

class FastSpeechTranscriptionTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Fast Speech Transcription Tool")
        self.root.geometry("800x600")
        
        # macOS specific window settings
        if platform.system() == "Darwin":
            try:
                self.root.tk.call('tk', 'scaling', 1.0)
            except:
                pass
        
        # Optimized audio parameters for speed
        self.sample_rate = 16000  # Keep this for Whisper compatibility
        self.channels = 1
        self.recording = False
        self.audio_data = []
        
        # Use tiny model for speed (much faster than base)
        self.whisper_model = None
        self.model_loading = False
        
        # Queue for thread communication
        self.result_queue = queue.Queue()
        
        # Processing timeout
        self.processing_timeout = None
        
        self.setup_ui()
        self.load_whisper_model()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Fast Speech Transcription Tool", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Speed info
        speed_label = ttk.Label(main_frame, text="⚡ Optimized for speed - Using 'tiny' model", 
                               font=("Arial", 10), foreground="blue")
        speed_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Recording controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        
        self.record_btn = ttk.Button(controls_frame, text="Start Recording", 
                                   command=self.toggle_recording)
        self.record_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.status_label = ttk.Label(controls_frame, text="Ready to record", 
                                    foreground="green")
        self.status_label.grid(row=0, column=1, padx=(10, 0))
        
        # Model selection (limited to fast models)
        ttk.Label(controls_frame, text="Model:").grid(row=0, column=2, padx=(20, 5))
        self.model_var = tk.StringVar(value="tiny")
        model_combo = ttk.Combobox(controls_frame, textvariable=self.model_var, 
                                  values=["tiny", "base"],  # Only fast models
                                  state="readonly", width=10)
        model_combo.grid(row=0, column=3, padx=(0, 10))
        model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        
        # Transcription area
        transcription_frame = ttk.LabelFrame(main_frame, text="Transcription", padding="10")
        transcription_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        transcription_frame.columnconfigure(0, weight=1)
        transcription_frame.rowconfigure(0, weight=1)
        
        self.transcription_text = scrolledtext.ScrolledText(transcription_frame, 
                                                          wrap=tk.WORD, height=15)
        self.transcription_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(action_frame, text="Clear", command=self.clear_text).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(action_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(action_frame, text="Save to File", command=self.save_to_file).grid(row=0, column=2, padx=(0, 10))
        
    def load_whisper_model(self):
        """Load Whisper model in a separate thread"""
        def load_model():
            try:
                self.model_loading = True
                self.status_label.config(text="Loading Whisper model...", foreground="orange")
                
                # Use tiny model by default for speed
                model_name = self.model_var.get()
                self.whisper_model = whisper.load_model(model_name)
                self.status_label.config(text=f"Model loaded ({model_name}) - Ready to record", foreground="green")
                self.model_loading = False
            except Exception as e:
                error_msg = f"Error loading model: {str(e)}"
                self.status_label.config(text=error_msg, foreground="red")
                self.model_loading = False
                
        threading.Thread(target=load_model, daemon=True).start()
        
    def on_model_change(self, event=None):
        """Handle model selection change"""
        if not self.model_loading and not self.recording:
            self.load_whisper_model()
            
    def toggle_recording(self):
        """Start or stop recording"""
        if self.model_loading:
            messagebox.showwarning("Please Wait", "Whisper model is still loading. Please wait.")
            return
            
        if self.whisper_model is None:
            messagebox.showerror("Model Not Loaded", "Whisper model failed to load. Please restart the application.")
            return
            
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        """Start audio recording"""
        try:
            self.recording = True
            self.audio_data = []
            self.record_btn.config(text="Stop Recording")
            self.status_label.config(text="Recording... Click 'Stop Recording' when finished", 
                                   foreground="red")
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
            self.recording_thread.start()
            
        except Exception as e:
            messagebox.showerror("Recording Error", f"Could not start recording: {str(e)}")
            
    def record_audio(self):
        """Record audio data using sounddevice"""
        try:
            def callback(indata, frames, time, status):
                if self.recording:
                    self.audio_data.append(indata.copy())
            
            with sd.InputStream(callback=callback, channels=self.channels, 
                              samplerate=self.sample_rate, dtype=np.float32):
                while self.recording:
                    sd.sleep(100)  # Sleep for 100ms
                    
        except Exception as e:
            print(f"Recording error: {e}")
            self.root.after(0, lambda: self.status_label.config(
                text=f"Recording error: {str(e)}", foreground="red"))
                
    def stop_recording(self):
        """Stop recording and transcribe"""
        if not self.recording:
            return
            
        self.recording = False
        self.record_btn.config(text="Start Recording")
        self.status_label.config(text="Processing audio...", foreground="orange")
        
        # Set a shorter timeout for faster processing
        self.processing_timeout = self.root.after(15000, self.handle_processing_timeout)  # 15 seconds
        
        # Start transcription in a separate thread
        threading.Thread(target=self.transcribe_audio, daemon=True).start()
        
    def transcribe_audio(self):
        """Transcribe the recorded audio with optimizations"""
        if not self.audio_data:
            self.root.after(0, lambda: self.status_label.config(
                text="No audio recorded - Please try again", foreground="red"))
            return
            
        try:
            # Combine all audio data
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Check if audio has any content
            if np.max(np.abs(audio_array)) < 0.01:
                self.root.after(0, lambda: self.status_label.config(
                    text="Audio too quiet - Please speak louder", foreground="red"))
                return
            
            # Save audio to temporary file with optimized settings
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                sf.write(temp_file.name, audio_array, self.sample_rate)
                
                # Transcribe using Whisper with optimized settings
                if self.whisper_model is None:
                    self.root.after(0, lambda: self.status_label.config(
                        text="Whisper model not loaded", foreground="red"))
                    return
                    
                # Use optimized transcription settings for speed
                result = self.whisper_model.transcribe(
                    temp_file.name,
                    fp16=False,  # Use FP32 for CPU
                    language=None,  # Auto-detect language
                    task="transcribe"
                )
                transcription = result["text"].strip()
                
                # Update UI in main thread
                self.root.after(0, self.update_transcription, transcription)
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
        except Exception as e:
            error_msg = f"Transcription error: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(
                text=error_msg, foreground="red"))
            # Cancel timeout if it exists
            if self.processing_timeout:
                self.root.after_cancel(self.processing_timeout)
                self.processing_timeout = None
            
    def handle_processing_timeout(self):
        """Handle processing timeout"""
        self.status_label.config(text="Processing timeout - Please try again", foreground="red")
        self.processing_timeout = None
        
    def update_transcription(self, text):
        """Update the transcription text area"""
        # Cancel timeout if it exists
        if self.processing_timeout:
            self.root.after_cancel(self.processing_timeout)
            self.processing_timeout = None
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add timestamp and transcription
        if self.transcription_text.get("1.0", tk.END).strip():
            self.transcription_text.insert(tk.END, f"\n\n[{timestamp}]\n")
        else:
            self.transcription_text.insert(tk.END, f"[{timestamp}]\n")
            
        self.transcription_text.insert(tk.END, text)
        self.transcription_text.see(tk.END)
        
        self.status_label.config(text="Transcription complete - Ready to record", 
                               foreground="green")
        
    def clear_text(self):
        """Clear the transcription text"""
        self.transcription_text.delete("1.0", tk.END)
        
    def copy_to_clipboard(self):
        """Copy transcription to clipboard"""
        text = self.transcription_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Text copied to clipboard!")
        else:
            messagebox.showwarning("No Text", "No text to copy!")
            
    def save_to_file(self):
        """Save transcription to a text file"""
        text = self.transcription_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "No text to save!")
            return
            
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                messagebox.showinfo("Saved", f"Text saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save file: {str(e)}")

def main():
    # Check for macOS specific requirements
    if platform.system() == "Darwin":
        print("macOS detected - Make sure you have granted microphone permissions to Terminal/Python")
        print("Go to System Preferences > Security & Privacy > Privacy > Microphone")
        print("Add Terminal or your Python executable to the allowed apps")
        print()
    
    root = tk.Tk()
    
    # Set a theme appropriate for the platform
    try:
        style = ttk.Style()
        available_themes = style.theme_names()
        
        if platform.system() == "Darwin":
            if 'aqua' in available_themes:
                style.theme_use('aqua')
            elif 'default' in available_themes:
                style.theme_use('default')
        else:
            if 'winnative' in available_themes:
                style.theme_use('winnative')
            elif 'clam' in available_themes:
                style.theme_use('clam')
    except:
        pass
        
    app = FastSpeechTranscriptionTool(root)
    
    # Handle window closing
    def on_closing():
        if hasattr(app, 'recording') and app.recording:
            app.stop_recording()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main() 