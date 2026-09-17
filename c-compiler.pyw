import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import os
import threading
import tempfile

CONFIG_FILE = "mingw_path.txt"

def load_mingw_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    return r"C:\mingw64\bin"

def save_mingw_path(*args):
    with open(CONFIG_FILE, "w") as f:
        f.write(mingw_path_var.get().strip())

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow:
            return
        x, y, _, cy = self.widget.bbox("insert") or (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="lightyellow",
                         relief="solid", borderwidth=1, font=("tahoma", "8", "normal"))
        label.pack()

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

def safe_filename(name):
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    return name

def get_current_command_list(quoted=True):
    source_file = source_var.get().strip().strip('"')
    lang_choice = lang_var.get()
    gui_type = gui_var.get()
    optimization = optimization_var.get()

    use_custom_name = custom_name_var.get()
    custom_name = custom_name_strvar.get().strip()
    use_custom_path = custom_path_var.get()
    custom_path = custom_path_strvar.get().strip()

    include_icon = include_icon_var.get()
    icon_path = icon_strvar.get().strip()
    mingw_bin = mingw_path_var.get().strip()

    compiler = os.path.join(mingw_bin, "gcc.exe") if lang_choice == "c" else os.path.join(mingw_bin, "g++.exe")

    def q(s):
        return f'"{s}"' if quoted else s

    cmd = [q(compiler)]
    output_path = None

    if source_file:
        cmd.append(q(source_file))

        src_dir, src_name = os.path.split(source_file)
        base, _ = os.path.splitext(src_name)
        output_dir = custom_path if (use_custom_path and custom_path) else (src_dir or ".")

        exe_name = safe_filename(custom_name) if (use_custom_name and custom_name) else base
        if not exe_name.lower().endswith(".exe"):
            exe_name += ".exe"

        output_path = os.path.join(output_dir, exe_name)
        cmd.extend(["-o", q(output_path)])
    else:
        cmd.append("<source_file>")
        cmd.extend(["-o", "<output.exe>"])

    cmd.extend(["-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections", optimization])

    if gui_type == "GUI":
        cmd.extend([
            "-mwindows", "-lgdi32", "-lgdiplus", "-lmsimg32",
            "-lcomdlg32", "-lcomctl32", "-lshell32", "-luxtheme",
            "-ldwmapi", "-lwinmm",
        ])

    if include_opengl_var.get():
        cmd.append("-lopengl32")

    if include_icon and icon_path:
        cmd.append("<compiled_icon.res>")

    return cmd, output_path

def get_strip_command_list(output_path, mingw_bin, quoted=True):
    strip_path = os.path.join(mingw_bin, "strip.exe")
    out = output_path if output_path else "<output.exe>"
    if quoted:
        return [f'"{strip_path}"', "--strip-all", f'"{out}"']
    return [strip_path, "--strip-all", out]

def update_preview(*args):
    cmd, output_path = get_current_command_list(quoted=True)
    mingw_bin = mingw_path_var.get().strip()
    strip_cmd = get_strip_command_list(output_path, mingw_bin, quoted=True)

    cmd_string = " ".join(cmd) + " && " + " ".join(strip_cmd)

    preview_text.config(state="normal")
    preview_text.delete("1.0", tk.END)
    preview_text.insert(tk.END, cmd_string)
    preview_text.config(state="disabled")

def run_compile(source_file, use_custom_path, custom_path, include_icon, icon_path, mingw_bin):
    temp_res = None
    rc_file_path = None
    windres_path = os.path.join(mingw_bin, "windres.exe")
    strip_path = os.path.join(mingw_bin, "strip.exe")

    try:
        if not os.path.isfile(source_file):
            messagebox.showerror("Error", "Invalid source file.")
            return

        cmd, output_path = get_current_command_list(quoted=False)

        src_dir, _ = os.path.split(source_file)
        output_dir = custom_path if use_custom_path else (src_dir or ".")
        os.makedirs(output_dir, exist_ok=True)

        if include_icon and icon_path:
            cmd.remove("<compiled_icon.res>")
            escaped_icon_path = icon_path.replace("\\", "\\\\")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".rc") as rc_file:
                rc_file.write(f"IDI_ICON1 ICON \"{escaped_icon_path}\"".encode('utf-8'))
                rc_file_path = rc_file.name

            temp_res = rc_file_path.replace(".rc", ".res")
            subprocess.run([windres_path, rc_file_path, "-O", "coff", "-o", temp_res], check=True)
            cmd.append(temp_res)

        print("\nRunning command:\n", cmd, "\n")

        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            messagebox.showerror("GCC Error", result.stderr or "Unknown error")
            return

        output_path_clean = output_path
        subprocess.run([strip_path, "--strip-all", output_path_clean], check=False)

        messagebox.showinfo("Success", f"Compiled to:\n{output_path_clean}")
        os.startfile(output_dir)

    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Compilation failed:\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
    finally:
        if temp_res and os.path.exists(temp_res):
            try: os.remove(temp_res)
            except: pass
        if rc_file_path and os.path.exists(rc_file_path):
            try: os.remove(rc_file_path)
            except: pass

        compile_button.config(state="normal")
        status_label.config(text="")

def start_compile():
    source_file = source_var.get().strip().strip('"')
    if not source_file:
        messagebox.showerror("Error", "Select a source file.")
        return

    use_custom_path = custom_path_var.get()
    custom_path = custom_path_strvar.get().strip()
    include_icon_flag = include_icon_var.get()
    icon_file = icon_strvar.get().strip()
    mingw_bin = mingw_path_var.get().strip()

    if not os.path.isdir(mingw_bin):
        messagebox.showerror("Error", "Invalid MinGW bin path.")
        return
    if use_custom_path and not os.path.isdir(custom_path):
        messagebox.showerror("Error", "Custom output path is invalid.")
        return
    if include_icon_flag and (not icon_file or not os.path.isfile(icon_file)):
        messagebox.showerror("Error", "Invalid icon file.")
        return

    compile_button.config(state="disabled")
    status_label.config(text="Compiling...")

    threading.Thread(target=run_compile, args=(
        source_file, use_custom_path, custom_path,
        include_icon_flag, icon_file, mingw_bin
    ), daemon=True).start()


def toggle_custom_name():
    custom_name_entry.config(state="normal" if custom_name_var.get() else "disabled")
    update_preview()

def toggle_custom_path():
    state = "normal" if custom_path_var.get() else "disabled"
    custom_path_entry.config(state=state)
    browse_path_button.config(state=state)
    update_preview()

def toggle_icon():
    state = "normal" if include_icon_var.get() else "disabled"
    icon_entry.config(state=state)
    browse_icon_button.config(state=state)
    update_preview()

def browse_mingw():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        mingw_path_var.set(folder_selected)

def browse_source():
    filetypes = [("C/C++ source files", "*.c *.cpp"), ("All files", "*.*")]
    file_selected = filedialog.askopenfilename(filetypes=filetypes)
    if file_selected:
        source_var.set(file_selected)

def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        custom_path_strvar.set(folder_selected)

def browse_icon():
    file_selected = filedialog.askopenfilename(filetypes=[("Icon files", "*.ico")])
    if file_selected:
        icon_strvar.set(file_selected)


root = tk.Tk()
root.title("MinGW Compiler GUI")
root.geometry("620x800")
root.resizable(False, False)

mingw_path_var = tk.StringVar(value=load_mingw_path())
source_var = tk.StringVar()
lang_var = tk.StringVar(value="c")
gui_var = tk.StringVar(value="Console")
include_opengl_var = tk.IntVar(value=0)
custom_name_var = tk.IntVar(value=0)
custom_name_strvar = tk.StringVar()
custom_path_var = tk.IntVar(value=0)
custom_path_strvar = tk.StringVar()
include_icon_var = tk.IntVar(value=0)
icon_strvar = tk.StringVar()
optimization_var = tk.StringVar(value="-O2")

for var in (mingw_path_var, source_var, lang_var, gui_var, include_opengl_var, custom_name_strvar, custom_path_strvar, icon_strvar, optimization_var):
    var.trace_add("write", update_preview)

mingw_path_var.trace_add("write", save_mingw_path)


tk.Label(root, text="MinGW bin Path:").pack(pady=(10, 0))
frame_mingw = tk.Frame(root)
mingw_entry = tk.Entry(frame_mingw, width=50, textvariable=mingw_path_var)
mingw_entry.pack(side="left")
tk.Button(frame_mingw, text="Browse", command=browse_mingw).pack(side="left", padx=5)
frame_mingw.pack(pady=5)

tk.Label(root, text="Source File:").pack(pady=(10, 0))
frame_source = tk.Frame(root)
source_entry = tk.Entry(frame_source, width=50, textvariable=source_var)
source_entry.pack(side="left")
tk.Button(frame_source, text="Browse", command=browse_source).pack(side="left", padx=5)
frame_source.pack(pady=5)

frame_lang = tk.Frame(root)
tk.Radiobutton(frame_lang, text="C", variable=lang_var, value="c").pack(side="left", padx=10)
tk.Radiobutton(frame_lang, text="C++", variable=lang_var, value="cpp").pack(side="left", padx=10)
frame_lang.pack()

frame_gui = tk.Frame(root)
tk.Label(frame_gui, text="App Type:").pack(side="left")
tk.Radiobutton(frame_gui, text="Console", variable=gui_var, value="Console").pack(side="left", padx=5)
tk.Radiobutton(frame_gui, text="GUI", variable=gui_var, value="GUI").pack(side="left", padx=5)
frame_gui.pack(pady=10)

tk.Checkbutton(root, text="Link OpenGL (-lopengl32)", variable=include_opengl_var).pack(pady=(0, 5))

tk.Checkbutton(root, text="Custom filename", variable=custom_name_var, command=toggle_custom_name).pack(pady=(5, 0))
custom_name_entry = tk.Entry(root, width=60, state="disabled", textvariable=custom_name_strvar)
custom_name_entry.pack()

tk.Checkbutton(root, text="Custom output folder", variable=custom_path_var, command=toggle_custom_path).pack(pady=(5, 0))
frame_path = tk.Frame(root)
custom_path_entry = tk.Entry(frame_path, width=45, state="disabled", textvariable=custom_path_strvar)
custom_path_entry.pack(side="left")
browse_path_button = tk.Button(frame_path, text="Browse", state="disabled", command=browse_folder)
browse_path_button.pack(side="left", padx=5)
frame_path.pack()

tk.Checkbutton(root, text="Include icon", variable=include_icon_var, command=toggle_icon).pack(pady=(5, 0))
frame_icon = tk.Frame(root)
icon_entry = tk.Entry(frame_icon, width=45, state="disabled", textvariable=icon_strvar)
icon_entry.pack(side="left")
browse_icon_button = tk.Button(frame_icon, text="Browse", state="disabled", command=browse_icon)
browse_icon_button.pack(side="left", padx=5)
frame_icon.pack()

frame_opt = tk.Frame(root)
frame_opt.pack(pady=10, fill="x", padx=20)
tk.Label(frame_opt, text="Optimization Level:").pack(anchor="w")

optimization_options = [
    ("-O0", "No optimization", "black"),
    ("-O1", "Basic optimization", "blue"),
    ("-O2", "Recommended speed", "green"),
    ("-O3", "Aggressive speed", "orange"),
    ("-Ofast", "Extreme speed (unsafe)", "red"),
    ("-Os", "Optimize for size", "green"),
]
for flag, desc, color in optimization_options:
    row = tk.Frame(frame_opt)
    tk.Radiobutton(row, text=flag, variable=optimization_var, value=flag, fg=color).pack(side="left")
    info = tk.Label(row, text="i", fg="blue", cursor="question_arrow")
    info.pack(side="left", padx=3)
    ToolTip(info, desc)
    row.pack(anchor="w", pady=1)

compile_button = tk.Button(root, text="Compile", command=start_compile)
compile_button.pack(pady=(10, 5))
status_label = tk.Label(root, text="", fg="blue")
status_label.pack()

tk.Label(root, text="Live Command Preview:").pack(anchor="w", padx=20)
preview_text = tk.Text(root, height=4, width=70, bg="#f0f0f0", font=("Consolas", 9), wrap="word", state="disabled")
preview_text.pack(padx=20, pady=(0, 15))

update_preview()

root.mainloop()