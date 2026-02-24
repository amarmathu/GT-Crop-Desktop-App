import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import json
from processor import process_sheet, crop_and_mark_sheet, is_valid_sheet, dpi, rotate_images_in_folder, convert_to_300dpi
from tkinterdnd2 import TkinterDnD, DND_FILES

class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class GTCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GT Crop")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        # --- Design System ---
        self.colors = {
            "primary": "#2196F3",       # Blue
            "primary_hover": "#1976D2",
            "secondary": "#FF9800",     # Orange
            "secondary_hover": "#F57C00",
            "success": "#4CAF50",       # Green
            "error": "#F44336",         # Red
            "bg_dark": "#2b2b2b",
            "bg_light": "#f5f5f5",
            "surface_dark": "#333333",
            "surface_light": "#ffffff",
            "text_dark": "#ffffff",
            "text_light": "#000000",
            "gray": "gray50"
        }
        
        # Load theme preference
        self.dark_mode = self.load_theme_preference()
        self.apply_theme()

        # Initialize data
        self.input_files = []  # List of dicts: {'path': str, 'valid': bool, 'widget': ctk.CTkFrame}
        self.output_folder = ""

        # Create GUI
        self.create_widgets()
        
        # Enable Drag & Drop
        self.setup_dnd()

    def setup_dnd(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        image_extensions = {'.jpg', '.jpeg', '.png'}
        
        for f in files:
            if os.path.isdir(f):
                # Add folder content
                for root, _, filenames in os.walk(f):
                    for filename in filenames:
                        if any(filename.lower().endswith(ext) for ext in image_extensions):
                            self.add_file(os.path.join(root, filename))
            elif os.path.isfile(f):
                if any(f.lower().endswith(ext) for ext in image_extensions):
                    self.add_file(f)


    def load_theme_preference(self):
        try:
            if os.path.exists("gtcrop_config.json"):
                with open("gtcrop_config.json", "r") as f:
                    config = json.load(f)
                    return config.get("dark_mode", True)
        except:
            pass
        return True # Default to dark

    def save_theme_preference(self):
        try:
            with open("gtcrop_config.json", "w") as f:
                json.dump({"dark_mode": self.dark_mode}, f)
        except:
            pass

    def apply_theme(self):
        ctk.set_appearance_mode("Dark" if self.dark_mode else "Light")
        self.bg_color = self.colors["bg_dark"] if self.dark_mode else self.colors["bg_light"]
        self.surface_color = self.colors["surface_dark"] if self.dark_mode else self.colors["surface_light"]
        self.text_color = self.colors["text_dark"] if self.dark_mode else self.colors["text_light"]

    def create_widgets(self):
        # Background Image
        self.bg_image = None
        try:
            from PIL import Image
            if os.path.exists("background.png"):
                bg_img_data = Image.open("background.png")
                self.bg_image = ctk.CTkImage(light_image=bg_img_data, dark_image=bg_img_data, size=(1920, 1080))
                self.bg_label = ctk.CTkLabel(self.root, text="", image=self.bg_image)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Failed to load background: {e}")

        # Main Container
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Header Section ---
        self.create_header(self.main_container)

        # --- Content Section (Split into Left: Files, Right: Actions/Status) ---
        content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Left Panel: File List
        self.create_file_panel(content_frame)

        # Right Panel: Controls & Actions
        self.create_control_panel(content_frame)

        # --- Footer Section ---
        self.create_footer(self.main_container)

    def create_header(self, parent):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))

        title = ctk.CTkLabel(header_frame, text="GT Crop", font=("Segoe UI", 28, "bold"))
        title.pack(side="left")

        self.theme_btn = ctk.CTkButton(
            header_frame,
            text="🌙" if not self.dark_mode else "☀️",
            width=40,
            command=self.toggle_theme,
            fg_color="transparent",
            border_width=1,
            text_color=self.text_color
        )
        self.theme_btn.pack(side="right")

    def create_file_panel(self, parent):
        left_frame = ctk.CTkFrame(parent, fg_color=self.surface_color, corner_radius=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        # Panel Header
        panel_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        panel_header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(panel_header, text="Input Files", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        # File Counts
        self.file_count_label = ctk.CTkLabel(panel_header, text="0 files", text_color=self.colors["gray"])
        self.file_count_label.pack(side="right")

        # File List (Scrollable)
        self.file_scroll_frame = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self.file_scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Add Buttons Area (Bottom of Left Panel)
        add_btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        add_btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            add_btn_frame, 
            text="➕ Add File", 
            command=self.select_single_file,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"]
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            add_btn_frame, 
            text="📁 Add Folder", 
            command=self.select_folder,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"]
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

    def create_control_panel(self, parent):
        right_frame = ctk.CTkFrame(parent, fg_color="transparent", width=300)
        right_frame.pack(side="right", fill="y", padx=(0, 0))

        # -- Output Section --
        out_frame = ctk.CTkFrame(right_frame, fg_color=self.surface_color, corner_radius=10)
        out_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(out_frame, text="Output Settings", font=("Segoe UI", 14, "bold")).pack(padx=15, pady=(15, 10), anchor="w")
        
        self.out_path_label = ctk.CTkLabel(out_frame, text="No folder selected", text_color=self.colors["gray"], wraplength=250, justify="left")
        self.out_path_label.pack(padx=15, pady=(0, 10), anchor="w")

        ctk.CTkButton(
            out_frame, 
            text="Select Output Folder", 
            command=self.select_output,
            fg_color=self.colors["secondary"],
            hover_color=self.colors["secondary_hover"]
        ).pack(padx=15, pady=(0, 15), fill="x")

        # -- Actions Section --
        action_frame = ctk.CTkFrame(right_frame, fg_color=self.surface_color, corner_radius=10)
        action_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(action_frame, text="Actions", font=("Segoe UI", 14, "bold")).pack(padx=15, pady=(15, 10), anchor="w")

        ctk.CTkButton(
            action_frame,
            text="🧹 Remove Invalid",
            command=self.remove_invalid_files,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors["error"],
            text_color=self.colors["error"],
            hover_color="#ffebee" if not self.dark_mode else "#3e2723"
        ).pack(padx=15, pady=(0, 10), fill="x")

        ctk.CTkButton(
            action_frame,
            text="🗑️ Clear All",
            command=self.clear_all_files,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors["gray"],
            text_color=self.colors["gray"]
        ).pack(padx=15, pady=(0, 15), fill="x")

        # -- Tools Section --
        tools_frame = ctk.CTkFrame(right_frame, fg_color=self.surface_color, corner_radius=10)
        tools_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(tools_frame, text="Tools", font=("Segoe UI", 14, "bold")).pack(padx=15, pady=(15, 10), anchor="w")

        ctk.CTkButton(tools_frame, text="🔍 Album Validator", command=self.open_album_validator).pack(padx=15, pady=(0, 10), fill="x")
        ctk.CTkButton(tools_frame, text="🖼️ Crop & Mark ", command=self.start_crop_mark).pack(padx=15, pady=(0, 10), fill="x")
        ctk.CTkButton(tools_frame, text="🔄 Rotate Pages", command=self.rotate_folder_images).pack(padx=15, pady=(0, 15), fill="x")

        # -- Process Button --
        self.btn_process = ctk.CTkButton(
            right_frame,
            text="🚀 Process All Valid",
            command=self.start_processing,
            fg_color=self.colors["success"],
            height=50,
            font=("Segoe UI", 16, "bold")
        )
        self.btn_process.pack(fill="x", pady=(10, 0))

    def create_footer(self, parent):
        footer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(10, 0))

        self.status_label = ctk.CTkLabel(footer_frame, text="Ready", text_color=self.colors["gray"], anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)

        self.progress = ctk.CTkProgressBar(footer_frame, width=300)
        self.progress.set(0)
        self.progress.pack(side="right", padx=10)
        self.progress.pack_forget() # Hide initially

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.save_theme_preference()
        self.apply_theme()
        
        # Refresh UI elements that don't auto-update
        self.theme_btn.configure(text="🌙" if not self.dark_mode else "☀️")
        
        # Re-create file list to update colors (simpler than updating each widget)
        current_files_data = self.input_files[:] # Copy list
        self.input_files = [] # Clear internal list
        for widget in self.file_scroll_frame.winfo_children():
            widget.destroy() # Destroy all current widgets
        
        # Re-add files, which will create new widgets with updated theme colors
        for f_data in current_files_data:
            self.add_file(f_data['path'])
            
        self.refresh_static_widgets()

    def refresh_static_widgets(self):
        # Update static widget colors if needed
        self.out_path_label.configure(text_color=self.text_color)
        self.status_label.configure(text_color=self.colors["gray"])
        self.file_count_label.configure(text_color=self.colors["gray"])
        self.btn_process.configure(fg_color=self.colors["success"])
        self.theme_btn.configure(text_color=self.text_color)

    def add_file_widget(self, file_path, display_text, is_valid):
        row = ctk.CTkFrame(self.file_scroll_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        # Status Icon
        icon = "✅" if is_valid else "❌"
        color = self.colors["success"] if is_valid else self.colors["error"]
        
        ctk.CTkLabel(row, text=icon, width=30).pack(side="left", padx=(5, 0))
        
        # Filename & Details
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        name = os.path.basename(file_path)
        ctk.CTkLabel(text_frame, text=name, anchor="w", font=("Segoe UI", 13), text_color=self.text_color).pack(fill="x")
        ctk.CTkLabel(text_frame, text=display_text.split(":", 1)[1].strip(), anchor="w", font=("Segoe UI", 11), text_color=color).pack(fill="x")

        # Delete Button
        del_btn = ctk.CTkButton(
            row, 
            text="×", 
            width=30, 
            height=30,
            fg_color="transparent", 
            text_color=self.colors["error"],
            hover_color="#ffebee" if not self.dark_mode else "#3e2723",
            command=lambda p=file_path, r=row: self.remove_file(p, r)
        )
        del_btn.pack(side="right", padx=5)

        return row

    def validate_file(self, file_path):
        try:
            from PIL import Image
            img = Image.open(file_path)
            w_in = img.width / dpi
            h_in = img.height / dpi
            is_valid = is_valid_sheet(w_in, h_in)
            status = "OK" if is_valid else "NOT MATCHED"
            return is_valid, f"{os.path.basename(file_path)}: {w_in:.2f} × {h_in:.2f}\" → {status}"
        except Exception as e:
            return False, f"{os.path.basename(file_path)}: Error reading file"

    def add_file(self, file_path):
        # Check if already added
        if any(f['path'] == file_path for f in self.input_files):
            return

        is_valid, display_text = self.validate_file(file_path)
        widget = self.add_file_widget(file_path, display_text, is_valid)
        
        self.input_files.append({
            'path': file_path,
            'valid': is_valid,
            'widget': widget
        })
        self.update_status()

    def remove_file(self, file_path, widget):
        widget.destroy()
        self.input_files = [f for f in self.input_files if f['path'] != file_path]
        self.update_status()

    def clear_all_files(self):
        for f in self.input_files:
            f['widget'].destroy()
        self.input_files = []
        self.update_status()

    def remove_invalid_files(self):
        to_remove = [f for f in self.input_files if not f['valid']]
        for f in to_remove:
            self.remove_file(f['path'], f['widget'])
        
        if to_remove:
            messagebox.showinfo("Success", f"Removed {len(to_remove)} invalid file(s).")
        else:
            messagebox.showinfo("Info", "No invalid files to remove.")

    def select_single_file(self):
        file = filedialog.askopenfilename(title="Select One Sheet Image", filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file:
            self.add_file(file)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder with 100+ Sheets")
        if not folder:
            return
        image_extensions = {'.jpg', '.jpeg', '.png'}
        added_count = 0
        for filename in os.listdir(folder):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                self.add_file(os.path.join(folder, filename))
                added_count += 1
        
        if added_count == 0:
            messagebox.showinfo("Info", "No valid image files found in this folder.")

    def select_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.out_path_label.configure(text=folder, text_color=self.text_color)

    def update_status(self):
        total = len(self.input_files)
        valid = sum(1 for f in self.input_files if f['valid'])
        self.file_count_label.configure(text=f"{total} files ({valid} valid)")
        
        if total > 0 and valid == total:
             self.status_label.configure(text="Ready to process", text_color=self.colors["success"])
        elif total > 0:
             self.status_label.configure(text=f"{total - valid} invalid files detected", text_color=self.colors["secondary"])
        else:
             self.status_label.configure(text="Ready", text_color=self.colors["gray"])

    def start_processing(self):
        if not self.input_files:
            messagebox.showwarning("No Files", "Please add input images.")
            return
        if not self.output_folder:
            messagebox.showwarning("No Output", "Please select an output folder.")
            return

        valid_files = [f for f in self.input_files if f['valid']]
        invalid_count = len(self.input_files) - len(valid_files)

        if invalid_count > 0:
            if not messagebox.askyesno("Invalid Files", f"{invalid_count} invalid files will be skipped. Continue?"):
                return

        if not valid_files:
            messagebox.showwarning("No Valid Files", "No valid sheets to process!")
            return

        self.progress.pack(side="right", padx=10)
        self.btn_process.configure(state="disabled", text="Processing...")
        self.status_label.configure(text="Processing...", text_color=self.colors["primary"])
        
        # Extract just paths for the processor
        paths = [f['path'] for f in valid_files]
        threading.Thread(target=self.process_all, args=(paths,), daemon=True).start()

    def process_all(self, file_paths):
        success_count = 0
        for i, path in enumerate(file_paths):
            try:
                success, msg = process_sheet(path, self.output_folder)
                if success: success_count += 1
                print(f"{os.path.basename(path)}: {msg}")
            except Exception as e:
                print(f"Error: {e}")
            
            self.root.after(0, self.update_progress, (i + 1) / len(file_paths))

        self.root.after(0, self.on_processing_complete, success_count, len(file_paths))

    def update_progress(self, value):
        self.progress.set(value)

    def on_processing_complete(self, success, total):
        self.progress.pack_forget()
        self.btn_process.configure(state="normal", text="🚀 Process All Valid")
        self.status_label.configure(text=f"Done! {success}/{total} processed.", text_color=self.colors["success"])
        messagebox.showinfo("Complete", f"Processed {success} of {total} sheets.")

    # --- Sub-Windows ---
    def start_crop_mark(self):
        CropMarkWindow(self.root, self.dark_mode)

    def open_album_validator(self):
        validator_window = ctk.CTkToplevel(self.root)
        validator_window.title("GT Crop - Album Validator")
        validator_window.geometry("720x520")
        AlbumValidator(validator_window, self.dark_mode)

    def rotate_folder_images(self):
        folder = filedialog.askdirectory(title="Select Folder to Rotate Images")
        if not folder: return

        if not messagebox.askyesno("Confirm", "Rotate all images in folder?\nOdd -> Left, Even -> Right"):
            return

        self.status_label.configure(text="Rotating...", text_color=self.colors["primary"])
        threading.Thread(target=self._do_rotate, args=(folder,), daemon=True).start()

    def _do_rotate(self, folder):
        success, total, errors = rotate_images_in_folder(folder)
        self.root.after(0, lambda: messagebox.showinfo("Done", f"Rotated {success}/{total} images."))
        self.root.after(0, lambda: self.status_label.configure(text="Rotation complete", text_color=self.colors["success"]))


class CropMarkWindow:
    def __init__(self, parent, dark_mode=False):
        self.parent = parent
        self.dark_mode = dark_mode

        self.window = ctk.CTkToplevel(parent)
        self.window.title("GT Crop - Crop & Mark")
        self.window.geometry("800x600")
        
        # Theme colors
        self.bg_color = "#2b2b2b" if dark_mode else "#f5f5f5"
        self.text_color = "white" if dark_mode else "black"
        self.window.configure(fg_color=self.bg_color)

        # Enable DnD for this window
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind('<<Drop>>', self.on_drop)


        # Header
        header = ctk.CTkFrame(self.window, fg_color="transparent")
        header.pack(fill="x", pady=15)
        ctk.CTkLabel(header, text="Crop & Mark (12x24 / 10x24)", font=("Segoe UI", 20, "bold"), text_color=self.text_color).pack()

        # Controls
        controls = ctk.CTkFrame(self.window, fg_color="transparent")
        controls.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(controls, text="➕ Add Files", command=self.select_files, width=120).pack(side="left", padx=5)
        ctk.CTkButton(controls, text="📁 Add Folder", command=self.select_folder, width=120).pack(side="left", padx=5)
        ctk.CTkButton(controls, text="🗑️ Clear All", command=self.clear_all, fg_color="#F44336", width=100).pack(side="right", padx=5)

        # File List
        self.list_frame = ctk.CTkScrollableFrame(self.window, height=300, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Output
        out_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        out_frame.pack(fill="x", padx=20, pady=10)
        
        self.out_label = ctk.CTkLabel(out_frame, text="Output: Not selected", text_color="gray")
        self.out_label.pack(side="left")
        
        ctk.CTkButton(out_frame, text="Select Output", command=self.select_output, width=120).pack(side="right")

        # Process
        self.btn_process = ctk.CTkButton(self.window, text="🚀 Process Selected Files", command=self.start_processing, fg_color="#4CAF50", height=40)
        self.btn_process.pack(fill="x", padx=20, pady=20)
        
        self.status = ctk.CTkLabel(self.window, text="Ready — Add files to begin", text_color="#4CAF50" if not dark_mode else "#66bb66")
        self.status.pack()

        self.input_files = []
        self.output_folder = ""

    def on_drop(self, event):
        files = self.window.tk.splitlist(event.data)
        image_extensions = {'.jpg', '.jpeg', '.png'}
        
        added_count = 0
        for f in files:
            if os.path.isdir(f):
                for root, _, filenames in os.walk(f):
                    for filename in filenames:
                        if any(filename.lower().endswith(ext) for ext in image_extensions):
                            self.add_file(os.path.join(root, filename))
                            added_count += 1
            elif os.path.isfile(f):
                if any(f.lower().endswith(ext) for ext in image_extensions):
                    self.add_file(f)
                    added_count += 1


    def select_files(self):
        files = filedialog.askopenfilenames(title="Select 12x24 or 10x24 Sheets", filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if files:
            for file_path in files:
                self.add_file(file_path)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder with 100+ Sheets")
        if not folder:
            return
        image_extensions = {'.jpg', '.jpeg', '.png'}
        added_count = 0
        error_count = 0
        for filename in os.listdir(folder):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                file_path = os.path.join(folder, filename)
                try:
                    self.add_file(file_path)
                    added_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {e}")
                    error_count += 1
        if added_count == 0:
            messagebox.showinfo("Info", "No valid image files found in this folder.")
        else:
            message = f"Added {added_count} file(s)"
            if error_count > 0:
                message += f" (with {error_count} errors)"
            messagebox.showinfo("Success", message)

    def add_file(self, file_path):
        try:
            from PIL import Image
            img = Image.open(file_path)
            w_in = img.width / dpi
            h_in = img.height / dpi
            
            # Logic check for 12x24 or 10x24
            is_valid_size = (
                (abs(w_in - 12) < 0.1 and abs(h_in - 24) < 0.1) or
                (abs(w_in - 24) < 0.1 and abs(h_in - 12) < 0.1) or
                (abs(w_in - 10) < 0.1 and abs(h_in - 24) < 0.1) or
                (abs(w_in - 24) < 0.1 and abs(h_in - 10) < 0.1)
            )
            
            status_text = "✅ OK" if is_valid_size else "❌ INVALID SIZE"
            status_color = "#4CAF50" if is_valid_size else "#F44336"
            
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text="✅" if is_valid_size else "❌", width=30).pack(side="left")
            
            details = f"{os.path.basename(file_path)} ({w_in:.1f}x{h_in:.1f}\")"
            ctk.CTkLabel(row, text=details, text_color=self.text_color, anchor="w").pack(side="left", padx=10, fill="x", expand=True)
            ctk.CTkLabel(row, text=status_text, text_color=status_color, width=100).pack(side="left", padx=10)
            
            ctk.CTkButton(row, text="×", width=30, fg_color="transparent", text_color="red", hover_color="#ffebee", command=lambda: self.remove_file(file_path, row)).pack(side="right")
            
            self.input_files.append({'path': file_path, 'widget': row, 'valid': is_valid_size})
        except Exception as e:
            print(f"Error adding file: {e}")

    def remove_file(self, path, widget):
        widget.destroy()
        self.input_files = [f for f in self.input_files if f['path'] != path]

    def clear_all(self):
        for f in self.input_files: f['widget'].destroy()
        self.input_files = []

    def select_output(self):
        self.output_folder = filedialog.askdirectory(title="Select Output Folder")
        if self.output_folder:
            self.out_label.configure(text=f"Output: {self.output_folder}")

    def start_processing(self):
        if not self.input_files:
            messagebox.showwarning("No Files", "Please add input images.")
            return
        if not self.output_folder:
            messagebox.showwarning("No Output", "Please select an output folder.")
            return

        valid_files = [f for f in self.input_files if f['valid']]
        if len(valid_files) == 0:
            messagebox.showinfo("Info", "No valid 12x24 or 10x24 sheets found.")
            return

        self.btn_process.configure(state="disabled", text="Processing...")
        self.status.configure(text=f"Processing {len(valid_files)} files...", text_color="#2196F3")
        threading.Thread(target=self.process_all, args=(valid_files,), daemon=True).start()

    def process_all(self, valid_files):
        success_count = 0
        total_output = 0
        for item in valid_files:
            file_path = item['path']
            try:
                success, msg = crop_and_mark_sheet(file_path, self.output_folder)
                if success:
                    success_count += 1
                    total_output += 2
                print(f"{os.path.basename(file_path)}: {msg}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        self.window.after(0, self.on_processing_complete, success_count, len(valid_files), total_output)

    def on_processing_complete(self, success_count, total_valid, total_output):
        self.btn_process.configure(state="normal", text="🚀 Process Selected Files")
        color = "#4CAF50" if success_count == total_valid else "#ff9800"
        self.status.configure(text=f"Done! {success_count}/{total_valid} files → {total_output} output files.", text_color=color)
        messagebox.showinfo("GT Crop", f"Crop & Mark complete!\n{success_count} out of {total_valid} files processed.\n{total_output} files saved.")


class AlbumValidator:
    def __init__(self, window, dark_mode=False):
        self.window = window
        self.dark_mode = dark_mode
        
        # Theme
        bg = "#2b2b2b" if dark_mode else "#f5f5f5"
        text = "white" if dark_mode else "black"
        self.window.configure(fg_color=bg)
        
        ctk.CTkLabel(window, text="Album Validator", font=("Segoe UI", 20, "bold"), text_color=text).pack(pady=20)
        ctk.CTkButton(window, text="Select Folder", command=self.select_folder).pack(pady=10)
        
        self.result_text = ctk.CTkTextbox(window, width=600, height=300)
        self.result_text.pack(pady=10, padx=20)

        # Enable DnD
        self.window.drop_target_register(DND_FILES)
        self.window.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        files = self.window.tk.splitlist(event.data)
        for f in files:
            if os.path.isdir(f):
                self.validate_album(f)
                return # Only validate the first folder dropped

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Album Folder")
        if folder:
            self.validate_album(folder)

    def validate_album(self, folder):
        image_extensions = {'.jpg', '.jpeg', '.png'}
        files = [os.path.join(folder, f) for f in os.listdir(folder) if any(f.lower().endswith(ext) for ext in image_extensions)]

        if not files:
            self.result_text.insert("end", "No image files found in the folder.\n")
            return

        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"📁 Checking {len(files)} files in:\n{folder}\n\n")

        size_counts = {}
        invalid_files = []
        file_details = []

        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                from PIL import Image
                img = Image.open(file_path)
                w_in = img.width / dpi
                h_in = img.height / dpi

                if is_valid_sheet(w_in, h_in):
                    normalized = tuple(sorted((round(w_in, 2), round(h_in, 2))))
                    size_counts[normalized] = size_counts.get(normalized, 0) + 1
                    file_details.append((filename, normalized, True))
                else:
                    invalid_files.append(filename)
                    file_details.append((filename, (w_in, h_in), False))
            except Exception as e:
                invalid_files.append(f"{filename} (error: {str(e)[:30]}...)")
                file_details.append((filename, None, False))

        total = len(files)
        valid_count = total - len(invalid_files)

        self.result_text.insert("end", f"📊 Summary:\n")
        self.result_text.insert("end", f"   Total files: {total}\n")
        self.result_text.insert("end", f"   Valid sheets: {valid_count}\n")
        self.result_text.insert("end", f"   Invalid/Unreadable: {len(invalid_files)}\n\n")

        if invalid_files:
            self.result_text.insert("end", "❌ Invalid Files:\n")
            for f in invalid_files:
                self.result_text.insert("end", f"   • {f}\n")
            self.result_text.insert("end", "\n")

        if valid_count == 0:
             self.result_text.insert("end", "❌ No valid sheets found.\n")
        elif len(size_counts) == 1:
            size = list(size_counts.keys())[0]
            self.result_text.insert("end", f"✅ VALID ALBUM!\nAll {valid_count} sheets are {size[0]}×{size[1]} inches.\n")
        else:
            self.result_text.insert("end", "⚠️ MULTIPLE SIZES DETECTED:\n")
            for size, count in sorted(size_counts.items()):
                self.result_text.insert("end", f"   • {size[0]}×{size[1]}\" → {count} sheets\n")
            self.result_text.insert("end", f"❌ INVALID ALBUM: {len(size_counts)} different sizes found.\n")

        self.result_text.insert("end", "\n📋 Full File List:\n")
        for filename, size, is_valid in file_details:
            if is_valid:
                self.result_text.insert("end", f"   ✅ {filename}: {size[0]}×{size[1]}\"\n")
            else:
                self.result_text.insert("end", f"   ❌ {filename}\n")

        # --- DPI Correction Logic ---
        incorrect_dpi_files = []
        for filename, _, _ in file_details:
             fpath = os.path.join(folder, filename)
             try:
                 img = Image.open(fpath)
                 d = img.info.get('dpi', (72, 72))
                 if isinstance(d, tuple): d = d[0]
                 if abs(d - 300) > 5: # Tolerance
                     incorrect_dpi_files.append(fpath)
             except:
                 pass
        
        if incorrect_dpi_files:
            self.result_text.insert("end", "\n⚠️ DPI WARNING:\n")
            self.result_text.insert("end", f"Found {len(incorrect_dpi_files)} files with incorrect DPI (not 300).\n")
            
            # Add Fix Button
            btn = ctk.CTkButton(self.window, text=f"🔧 Fix {len(incorrect_dpi_files)} Files (Convert to 300 DPI)", 
                                command=lambda: self.fix_dpi(incorrect_dpi_files), fg_color="#FF9800")
            btn.pack(pady=10)

    def fix_dpi(self, files_to_fix):
        output_folder = filedialog.askdirectory(title="Select Folder to Save Corrected Files")
        if not output_folder: return

        success_count = 0
        for fpath in files_to_fix:
            success, msg = convert_to_300dpi(fpath, output_folder)
            if success: success_count += 1
            print(msg)
        
        messagebox.showinfo("Done", f"Converted {success_count} files to 300 DPI.\nSaved in: {output_folder}")


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = CTkDnD()
    app = GTCropApp(root)
    root.mainloop()