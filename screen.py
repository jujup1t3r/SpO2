import time
import cv2
import subprocess
import threading
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

# ==========================================
# 1. Camera Initialization
# ==========================================
# Initialize PiCamera2 for Global Shutter (IMX296)
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (640, 480)}
)
picam2.configure(config)
picam2.start()
encoder = H264Encoder()

class SmartCamApp:
    def __init__(self, window):
        self.window = window
        self.window.geometry("480x320") # Optimized for 3.5" SPI LCD
        self.window.title("Global Shutter Recording System")
        self.window.configure(bg='#121212') # Dark theme for better contrast

        self.recording = False
        self.start_time = 0
        self.current_filename = ""

        # --- UI Components ---
        # Video Preview Label
        self.lbl_video = tk.Label(window, bg='#121212')
        self.lbl_video.pack(pady=5)

        # Record Toggle Button
        self.btn_rec = tk.Button(window, text="START RECORD", font=("Arial", 12, "bold"),
                                 bg="#2ecc71", fg="white", width=18, height=1,
                                 activebackground="#27ae60", command=self.manual_toggle)
        self.btn_rec.pack(pady=2)

        # Status & Timer Label
        self.lbl_status = tk.Label(window, text="SYSTEM READY", font=("Arial", 10), 
                                   bg='#121212', fg='#ecf0f1')
        self.lbl_status.pack()

        # Begin the main refresh loop
        self.update_loop()

    def convert_to_mp4(self, h264_file):
        """Convert raw H264 bitstream to MP4 container using FFmpeg."""
        mp4_name = h264_file.replace(".h264", ".mp4")
        subprocess.run(['ffmpeg', '-i', h264_file, '-c', 'copy', mp4_name, '-y', '-loglevel', 'quiet'])

    def manual_toggle(self):
        """Toggle recording state when the touchscreen button is pressed."""
        if not self.recording:
            self.start_rec()
        else:
            self.stop_rec()

    def start_rec(self):
        """Handle recording initiation and UI state update."""
        if not self.recording:
            self.current_filename = f"rec_{datetime.now().strftime('%H%M%S')}.h264"
            picam2.start_recording(encoder, self.current_filename)
            self.recording = True
            self.start_time = time.time()
            self.btn_rec.config(text="STOP", bg="#e74c3c")

    def stop_rec(self):
        """Handle recording termination and trigger background conversion."""
        if self.recording:
            picam2.stop_recording()
            # Run conversion in a separate thread to prevent UI freezing
            threading.Thread(target=self.convert_to_mp4, args=(self.current_filename,), daemon=True).start()
            self.recording = False
            self.btn_rec.config(text="START RECORD", bg="#2ecc71")

    def update_loop(self):
        """Primary application loop for frame processing and GUI updates."""
        # Auto-stop after 10 seconds of recording
        if self.recording:
            elapsed = time.time() - self.start_time
            if elapsed >= 10:
                self.stop_rec()

        # Capture frame from the sensor
        frame = picam2.capture_array()
        
        # FIX: Convert BGR (OpenCV default) to RGB (PIL/Tkinter requirement)
        # This fixes the "Blue Skin" issue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # FIX: Resize preview to fit within the 3.5" screen boundaries
        # Reduced height (200px) ensures the button remains visible
        frame_sm = cv2.resize(frame_rgb, (260, 200)) 
        
        # Convert array to Tkinter-compatible image
        img = Image.fromarray(frame_sm)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl_video.imgtk = imgtk
        self.lbl_video.configure(image=imgtk)

        # Update dynamic status text
        if self.recording:
            timer = int(10 - (time.time() - self.start_time))
            self.lbl_status.config(text=f"RECORDING: {timer}s", fg="#e74c3c")
        else:
            self.lbl_status.config(text="SYSTEM READY", fg="#2ecc71")

        # Schedule next update (approx. 30 FPS)
        self.window.after(30, self.update_loop)

# ==========================================
# 3. Main Application Entry Point
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = SmartCamApp(root)
    try:
        root.mainloop()
    finally:
        # Clean up hardware resources on exit
        picam2.stop()
        cv2.destroyAllWindows()
