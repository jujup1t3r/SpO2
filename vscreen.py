import time
import cv2
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
import os
import subprocess  # Used for converting file formats

os.environ["DISPLAY"] = ":0"

try:
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)})
    picam2.configure(config)
    picam2.start()
    encoder = H264Encoder()
except Exception as e:
    print(f"Camera Initialization Error: {e}")

class SmartCamApp:
    def __init__(self, window):
        self.window = window
        self.window.attributes('-fullscreen', True)
        self.window.configure(bg='black')
        self.window.bind("<Escape>", lambda e: self.window.destroy())

        self.recording = False
        self.start_time = 0
        self.current_h264 = "" # Store filename for conversion

        # --- UI Layers ---
        self.lbl_video = tk.Label(window, bg='black', bd=0)
        self.lbl_video.place(x=0, y=0, relwidth=1, relheight=1)

        self.status_indicator = tk.Label(window, text="● READY", font=("Arial", 12, "bold"), 
                                        bg='black', fg="#2ecc71")
        self.status_indicator.place(x=20, y=20)

        self.lbl_timer = tk.Label(window, text="00:00", font=("Arial", 14, "bold"), 
                                  bg='black', fg="white")
        self.lbl_timer.place(relx=0.5, y=30, anchor='center')

        self.canvas = tk.Canvas(window, width=100, height=100, bg='black', highlightthickness=0, bd=0)
        self.canvas.place(relx=0.5, rely=0.85, anchor='center')
        self.canvas.create_oval(10, 10, 90, 90, outline="white", width=4)
        self.btn_shutter = self.canvas.create_oval(18, 18, 82, 82, fill="white", outline="")
        self.canvas.tag_bind(self.btn_shutter, "<Button-1>", lambda e: self.manual_toggle())

        self.update_loop()

    def manual_toggle(self):
        if not self.recording: self.start_rec()
        else: self.stop_rec()

    def start_rec(self):
        if not self.recording:
            timestamp = datetime.now().strftime('%H%M%S')
            self.current_h264 = f"/home/spo2/rec_{timestamp}.h264"
            
            picam2.start_recording(encoder, self.current_h264)
            self.recording = True
            self.start_time = time.time()
            
            self.status_indicator.config(text="● RECORDING", fg="#ff4757")
            self.canvas.itemconfig(self.btn_shutter, fill="#ff4757")

    def stop_rec(self):
        if self.recording:
            picam2.stop_recording()
            self.recording = False
            
            # Reset UI
            self.status_indicator.config(text="● PROCESSING...", fg="#f1c40f")
            self.lbl_timer.config(text="00:00")
            self.canvas.itemconfig(self.btn_shutter, fill="white")
            
            # Convert to MP4 in a background thread so the UI doesn't freeze
            h264_file = self.current_h264
            mp4_file = h264_file.replace(".h264", ".mp4")
            self.convert_to_mp4(h264_file, mp4_file)

    def convert_to_mp4(self, input_file, output_file):
        """Convert H264 to MP4 using FFmpeg."""
        try:
            # Use subprocess to run ffmpeg command
            # -y overwrites if file exists, -i is input
            command = f"ffmpeg -y -i {input_file} -c copy {output_file} && rm {input_file}"
            subprocess.Popen(command, shell=True) 
            print(f"Conversion started: {output_file}")
            self.status_indicator.config(text="● READY", fg="#2ecc71")
        except Exception as e:
            print(f"Conversion Error: {e}")

    def update_loop(self):
        try:
            # 1. Update Timer Logic
            if self.recording:
                elapsed = time.time() - self.start_time
                mins, secs = divmod(int(elapsed), 60)
                self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")
                
                # Auto-stop after 10 seconds
                if elapsed >= 10: 
                    self.stop_rec()

            # 2. Camera Preview Logic (Always running)
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            win_w = self.window.winfo_width()
            win_h = self.window.winfo_height()
            if win_w > 1 and win_h > 1:
                frame = cv2.resize(frame, (win_w, win_h))

            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.lbl_video.imgtk = imgtk
            self.lbl_video.configure(image=imgtk)
            
        except Exception as e:
            print(f"Loop Error: {e}")

        self.window.after(20, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartCamApp(root)
    try:
        root.mainloop()
    finally:
        picam2.stop()
