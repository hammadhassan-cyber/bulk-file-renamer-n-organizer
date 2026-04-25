import os
import shutil
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_SUPPORTED = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    DND_SUPPORTED = False

LOG_FILE = "file_organizer_log.csv"

FILE_TYPES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
    "PDFs": [".pdf"],
    "Documents": [".doc", ".docx", ".txt", ".odt", ".rtf", ".pptx", ".xlsx"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".ts"],
}

undo_actions = []

def get_files(folder_path):
    try:
        entries = os.listdir(folder_path)
    except PermissionError:
        messagebox.showerror("Error", "Permission denied.")
        return []
    return sorted(
        name for name in entries
        if os.path.isfile(os.path.join(folder_path, name))
    )

def format_file_size(file_path):
    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1_048_576:
            return f"{size_bytes // 1024} KB"
        return f"{size_bytes // 1_048_576} MB"
    except Exception:
        return "?"

def format_modified_date(file_path):
    try:
        modified_timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(modified_timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "?"

def avoid_overwrite(target_path):
    if not os.path.exists(target_path):
        return target_path
    base_name, extension = os.path.splitext(target_path)
    counter = 1
    while os.path.exists(f"{base_name}_{counter}{extension}"):
        counter += 1
    return f"{base_name}_{counter}{extension}"


def write_log(folder_path, old_name, new_name, action="Rename"):
    log_path = os.path.join(folder_path, LOG_FILE)
    is_new_log = not os.path.isfile(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        if is_new_log:
            writer.writerow(["Timestamp", "Action", "Old", "New"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action, old_name, new_name,])

def build_new_name(file_name, prefix_text, suffix_text, find_text, replace_text, file_index, use_numbering):
    base_name, extension = os.path.splitext(file_name)
    if find_text:
        base_name = base_name.replace(find_text, replace_text)
    if prefix_text:
        base_name = prefix_text + base_name
    if suffix_text:
        base_name = base_name + suffix_text
    if use_numbering:
        base_name = f"{base_name}_{file_index}"
    return base_name + extension

def get_category(extension):
    extension = extension.lower()
    for category_name, extension_list in FILE_TYPES.items():
        if extension in extension_list:
            return category_name
    return "Others"

BaseWindow = TkinterDnD.Tk if DND_SUPPORTED else tk.Tk

class FileOrganizerApp(BaseWindow):
    def __init__(self):
        super().__init__()
        self.title("Bulk File Renamer & Smart Organizer")
        self.geometry("1020x720")
        self.configure(bg="#1e1e2e")

        self.selected_folder = tk.StringVar()
        self.status_text = tk.StringVar(value="Drop a folder here or browse to get started.")
        self.prefix_text = tk.StringVar()
        self.suffix_text = tk.StringVar()
        self.find_text = tk.StringVar()
        self.replace_text = tk.StringVar()
        self.use_numbering = tk.BooleanVar(value=False)
        self.organize_mode = tk.StringVar(value="type")

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        background_color = "#1e1e2e"
        foreground_color = "#cdd6f4"
        style.configure("TLabel", background=background_color, foreground=foreground_color, font=("Consolas", 10))
        style.configure("TButton", font=("Consolas", 10, "bold"), padding=6)
        style.configure("TEntry", fieldbackground="#313244", foreground=foreground_color)
        style.configure("TCheckbutton", background=background_color, foreground=foreground_color, font=("Consolas", 10))
        style.configure("TRadiobutton", background=background_color, foreground=foreground_color, font=("Consolas", 10))
        style.configure("TNotebook", background=background_color)
        style.configure("TNotebook.Tab", font=("Consolas", 10, "bold"))
        style.configure("Treeview", background="#313244", fieldbackground="#313244", foreground=foreground_color, rowheight=24, font=("Consolas", 9))
        style.configure("Treeview.Heading", background="#45475a", foreground=foreground_color, font=("Consolas", 9, "bold"))

    def _build_ui(self):
        top_frame = tk.Frame(self, bg="#1e1e2e", pady=8)
        top_frame.pack(fill="x", padx=14)

        tk.Label(top_frame, text="Folder:", bg="#1e1e2e", fg="#89b4fa", font=("Consolas", 11, "bold")).pack(side="left")
        ttk.Entry(top_frame, textvariable=self.selected_folder, width=58).pack(side="left", padx=6)
        ttk.Button(top_frame, text="Browse", command=self.browse_folder).pack(side="left")

        self.drop_area = tk.Label(top_frame, text=" Drop folder here ", bg="#313244",
            fg="#cdd6f4", font=("Consolas", 10, "bold"), relief="groove", borderwidth=2, padx=18, pady=6, cursor="hand2",)
        self.drop_area.pack(side="left", padx=10)
        self.drop_area.bind("<Enter>", lambda event: self._set_drop_area_hover(True))
        self.drop_area.bind("<Leave>", lambda event: self._set_drop_area_hover(False))
        self.drop_area.bind("<Button-1>", lambda event: self.browse_folder())

        ttk.Button(top_frame, text="Undo Last", command=self.undo_last_action).pack(side="right")

        if DND_SUPPORTED:
            self.drop_area.drop_target_register(DND_FILES)
            self.drop_area.dnd_bind("<<Drop>>", self.handle_drop)
        else:
            self.drop_area.config(text=" Drag & drop unavailable ")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=6)

        self._build_files_tab()
        self._build_rename_tab()
        self._build_organize_tab()
        self._build_preview_tab()
        self._build_logs_tab()

        tk.Label(self, textvariable=self.status_text, bg="#181825", fg="#a6e3a1", font=("Consolas", 9),
                  anchor="w", pady=4,).pack(fill="x", side="bottom", padx=10)

    def _set_drop_area_hover(self, is_hovered):
        self.drop_area.configure(bg="#45475a" if is_hovered else "#313244")

    def handle_drop(self, event):
        try:
            dropped_items = self.tk.splitlist(event.data)
            if not dropped_items:
                raise ValueError("No dropped path received")
            dropped_path = dropped_items[0].strip().strip("{}\"")
            if os.path.isdir(dropped_path):
                self.selected_folder.set(dropped_path)
                self.status_text.set(f"Folder selected: {dropped_path}")
                self.refresh_file_list()
            else:
                messagebox.showwarning("Invalid Drop", f"Please drop a valid folder.\n\nReceived: {dropped_path}")
        except Exception as error:
            messagebox.showwarning("Invalid Drop", f"Please drop a valid folder.\n\nDetails: {error}")

    def browse_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder", mustexist=True)
        if folder_path:
            self.selected_folder.set(folder_path)
            self.status_text.set(f"Folder selected: {folder_path}")
            self.refresh_file_list()

    def get_valid_folder(self):
        folder_path = self.selected_folder.get().strip()
        if not folder_path:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return None
        if not os.path.isdir(folder_path):
            messagebox.showerror("Invalid Folder", f"Not a valid folder:\n{folder_path}")
            return None
        return folder_path

    def _build_files_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text=" Files ")

        header = tk.Frame(frame, bg="#1e1e2e")
        header.pack(fill="x", padx=12, pady=(8, 2))
        ttk.Button(header, text="Refresh", command=self.refresh_file_list).pack(side="left")
        self.file_count_label = tk.Label(header, text="", bg="#1e1e2e", fg="#a6adc8", font=("Consolas", 9))
        self.file_count_label.pack(side="left", padx=10)

        columns = ("Filename", "Size", "Modified")
        self.file_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.file_tree.heading("Filename", text="Filename")
        self.file_tree.heading("Size", text="Size")
        self.file_tree.heading("Modified", text="Date Modified")
        self.file_tree.column("Filename", width=520)
        self.file_tree.column("Size", width=100, anchor="center")
        self.file_tree.column("Modified", width=170, anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        self.file_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=6)
        scrollbar.pack(side="right", fill="y", pady=6, padx=(0, 8))

    def _build_rename_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text=" Rename ")

        options_box = tk.LabelFrame(frame, text=" Options ", bg="#1e1e2e", fg="#89b4fa", font=("Consolas", 10, "bold"), padx=12, pady=10)
        options_box.pack(fill="x", padx=14, pady=12)

        def add_label(text, row_index, column_index):
            tk.Label(options_box, text=text, bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10)).grid(row=row_index, column=column_index, sticky="w", pady=4, padx=4)

        add_label("Prefix:", 0, 0)
        ttk.Entry(options_box, textvariable=self.prefix_text, width=22).grid(row=0, column=1, padx=6)
        add_label("Suffix:", 0, 2)
        ttk.Entry(options_box, textvariable=self.suffix_text, width=22).grid(row=0, column=3, padx=6)
        add_label("Find:", 1, 0)
        ttk.Entry(options_box, textvariable=self.find_text, width=22).grid(row=1, column=1, padx=6)
        add_label("Replace:", 1, 2)
        ttk.Entry(options_box, textvariable=self.replace_text, width=22).grid(row=1, column=3, padx=6)

        ttk.Checkbutton(options_box, text="Auto Numbering (file_1, file_2 …)", variable=self.use_numbering).grid(row=2, column=0, columnspan=4, sticky="w", pady=6)

        button_row = tk.Frame(frame, bg="#1e1e2e")
        button_row.pack(pady=8)
        ttk.Button(button_row, text="Preview Rename", command=self.preview_rename).pack(side="left", padx=6)
        ttk.Button(button_row, text="Apply Rename", command=self.apply_rename).pack(side="left", padx=6)

    def _build_organize_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text=" Organize ")

        tk.Label(frame, text="Sort files into sub-folders by:", bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10)).pack(anchor="w", padx=16, pady=(14, 4))

        for value, label in [
            ("type", "File Type (Images, Videos, Documents …)"),
            ("ext", "Extension (.jpg, .pdf, .mp4 …)"),
            ("date", "Date Modified (YYYY-MM-DD)"),
            ("size", "File Size (Small / Medium / Large)"),
        ]:
            ttk.Radiobutton(frame, text=label, variable=self.organize_mode, value=value).pack(anchor="w", padx=34, pady=3)

        button_row = tk.Frame(frame, bg="#1e1e2e")
        button_row.pack(pady=12)
        ttk.Button(button_row, text="Preview Organize", command=self.preview_organize).pack(side="left", padx=6)
        ttk.Button(button_row, text="Apply Organize", command=self.apply_organize).pack(side="left", padx=6)

    def _build_preview_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text=" Preview ")

        tk.Label(frame, text="Preview the changes before applying them.", bg="#1e1e2e", fg="#6c7086", font=("Consolas", 9)).pack(anchor="w", padx=14, pady=(8, 2))

        columns = ("Current Name", "New Name / Destination")
        self.preview_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.preview_tree.heading("Current Name", text="Current Name")
        self.preview_tree.heading("New Name / Destination", text="New Name / Destination")
        self.preview_tree.column("Current Name", width=420)
        self.preview_tree.column("New Name / Destination", width=460)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        self.preview_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=8)
        scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 8))

    def _build_logs_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text=" Logs ")

        top_row = tk.Frame(frame, bg="#1e1e2e")
        top_row.pack(fill="x", padx=12, pady=(8, 4))
        ttk.Button(top_row, text="Load Log", command=self.load_log).pack(side="left")

        columns = ("Timestamp", "Action", "Old", "New")
        self.log_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column_name, width in [("Timestamp", 170), ("Action", 90), ("Old", 300), ("New", 300)]:
            self.log_tree.heading(column_name, text=column_name)
            self.log_tree.column(column_name, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        self.log_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=6)
        scrollbar.pack(side="right", fill="y", pady=6, padx=(0, 8))

    def refresh_file_list(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        self.file_tree.delete(*self.file_tree.get_children())
        file_names = get_files(folder_path)
        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)
            self.file_tree.insert("", "end", values=(file_name, format_file_size(file_path), format_modified_date(file_path)))
        self.file_count_label.config(text=f"{len(file_names)} file(s)")
        self.status_text.set(f"Found {len(file_names)} file(s) in: {folder_path}")

    def _show_preview(self, preview_rows):
        self.preview_tree.delete(*self.preview_tree.get_children())
        for old_value, new_value in preview_rows:
            self.preview_tree.insert("", "end", values=(old_value, new_value))
        self.notebook.select(3)

    def undo_last_action(self):
        if not undo_actions:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        errors = []
        while undo_actions:
            original_path, changed_path = undo_actions.pop()
            try:
                if os.path.exists(changed_path):
                    shutil.move(changed_path, original_path)
            except Exception as error:
                errors.append(str(error))
        if errors:
            messagebox.showerror("Undo Errors", "\n".join(errors))
        else:
            self.status_text.set("Undo complete.")
        self.refresh_file_list()

    def get_rename_pairs(self, folder_path):
        file_names = get_files(folder_path)
        return [
            (
                file_name,
                build_new_name(file_name, self.prefix_text.get().strip(), self.suffix_text.get().strip(),
                    self.find_text.get().strip(), self.replace_text.get(), index, self.use_numbering.get(),
                ),
            )
            for index, file_name in enumerate(file_names, start=1)
        ]

    def preview_rename(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        rename_pairs = self.get_rename_pairs(folder_path)
        if not rename_pairs:
            messagebox.showinfo("Empty", "No files found in that folder.")
            return
        self._show_preview(rename_pairs)
        self.status_text.set(f"Preview shows {len(rename_pairs)} rename(s).")

    def apply_rename(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        rename_pairs = self.get_rename_pairs(folder_path)
        if not rename_pairs:
            self.status_text.set("No files found.")
            return
        if not messagebox.askyesno("Confirm", f"Rename {len(rename_pairs)} file(s)?"):
            return
        undo_actions.clear()
        renamed_count = 0
        skipped_count = 0
        for old_name, new_name in rename_pairs:
            old_path = os.path.join(folder_path, old_name)
            new_path = avoid_overwrite(os.path.join(folder_path, new_name))
            try:
                os.rename(old_path, new_path)
                undo_actions.append((old_path, new_path))
                write_log(folder_path, old_name, os.path.basename(new_path))
                renamed_count += 1
            except Exception as error:
                skipped_count += 1
                print(f"Rename [{old_name}]: {error}")
        self.status_text.set(f"Renamed {renamed_count} file(s). Skipped {skipped_count}.")
        self.refresh_file_list()

    def get_destination_folder(self, folder_path, file_name):
        _, extension = os.path.splitext(file_name)
        mode = self.organize_mode.get()
        file_path = os.path.join(folder_path, file_name)

        if mode == "type":
            return get_category(extension)
        if mode == "ext":
            return extension.lstrip(".").upper() or "NoExt"
        if mode == "date":
            try:
                return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d")
            except Exception:
                return "UnknownDate"
        if mode == "size":
            try:
                size_bytes = os.path.getsize(file_path)
            except Exception:
                return "Unknown"
            if size_bytes < 1_000_000:
                return "Small (< 1 MB)"
            if size_bytes < 50_000_000:
                return "Medium (1-50 MB)"
            return "Large (> 50 MB)"
        return "Others"

    def get_organize_pairs(self, folder_path):
        return [
            (file_name, self.get_destination_folder(folder_path, file_name))
            for file_name in get_files(folder_path)
            if file_name != LOG_FILE
        ]

    def preview_organize(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        organize_pairs = self.get_organize_pairs(folder_path)
        if not organize_pairs:
            messagebox.showinfo("Empty", "No files found in that folder.")
            return
        self._show_preview([(file_name, f"-> {destination_folder}/") for file_name, destination_folder in organize_pairs])
        self.status_text.set(f"Preview shows {len(organize_pairs)} file(s).")

    def apply_organize(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        organize_pairs = self.get_organize_pairs(folder_path)
        if not organize_pairs:
            self.status_text.set("No files found.")
            return
        if not messagebox.askyesno("Confirm", f"Move {len(organize_pairs)} file(s) into sub-folders?"):
            return
        undo_actions.clear()
        moved_count = 0
        skipped_count = 0
        for file_name, destination_folder in organize_pairs:
            source_path = os.path.join(folder_path, file_name)
            destination_dir = os.path.join(folder_path, destination_folder)
            destination_path = avoid_overwrite(os.path.join(destination_dir, file_name))
            try:
                os.makedirs(destination_dir, exist_ok=True)
                shutil.move(source_path, destination_path)
                undo_actions.append((source_path, destination_path))
                write_log(folder_path, file_name, os.path.join(destination_folder, os.path.basename(destination_path)), "Move")
                moved_count += 1
            except PermissionError:
                skipped_count += 1
            except Exception as error:
                skipped_count += 1
                print(f"Organize [{file_name}]: {error}")
        self.status_text.set(f"Moved {moved_count} file(s) into sub-folders. Skipped {skipped_count}.")
        self.refresh_file_list()

    def load_log(self):
        folder_path = self.get_valid_folder()
        if not folder_path:
            return
        log_path = os.path.join(folder_path, LOG_FILE)
        if not os.path.isfile(log_path):
            messagebox.showinfo("No Log", "No log file found in this folder yet.")
            return
        self.log_tree.delete(*self.log_tree.get_children())
        with open(log_path, "r", encoding="utf-8", newline="") as log_file:
            reader = csv.reader(log_file)
            for row_index, row in enumerate(reader):
                if row_index == 0 and row and row[0] == "Timestamp":
                    continue
                if len(row) >= 4:
                    self.log_tree.insert("", "end", values=(row[0], row[1], row[2], row[3]))
        self.status_text.set("Log loaded.")


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()
