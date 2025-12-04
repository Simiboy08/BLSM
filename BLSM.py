import os, shutil, zipfile, json, tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk

CONFIG_FILE = "blsm_config.json"
PROFILES_DIR = "profiles"

def ensure_dirs():
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)

def zip_safe_extract(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.infolist()
        root_dirs = set(m.filename.split("/")[0] for m in members if "/" in m.filename)
        root = list(root_dirs)[0] if len(root_dirs)==1 else None
        for member in members:
            filename = member.filename
            if root and filename.startswith(root + "/"):
                filename = filename[len(root)+1:]
            if not filename.strip(): continue
            target_path = os.path.join(extract_to, filename)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            try: zip_ref.extract(member, extract_to)
            except: pass
        # Fix nested folder
        if root:
            root_path = os.path.join(extract_to, root)
            if os.path.exists(root_path):
                for item in os.listdir(root_path):
                    shutil.move(os.path.join(root_path,item), extract_to)
                shutil.rmtree(root_path, ignore_errors=True)

class BLSMApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BLSM — Bonelab Mod Manager")
        ensure_dirs()
        self.mods_folder = ""
        self.geometry("1000x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.build_ui()
        self.load_config()
        self.load_profiles()

    def build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=2)

        # LEFT FRAME (Profiles)
        self.frame_left = ctk.CTkFrame(self)
        self.frame_left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.frame_left, text="Profiles", font=("Arial",18)).pack(pady=10)
        self.list_profiles = tk.Listbox(self.frame_left, height=20, bg='#2b2b2b', fg='white', selectbackground='#1f6aa5')
        self.list_profiles.pack(fill="both", expand=True, padx=10)
        scrollbar_profiles = tk.Scrollbar(self.frame_left, command=self.list_profiles.yview)
        self.list_profiles.config(yscrollcommand=scrollbar_profiles.set)
        scrollbar_profiles.pack(side='right', fill='y')
        self.list_profiles.bind('<<ListboxSelect>>', self.load_profile_contents)
        ctk.CTkButton(self.frame_left, text="New Profile", command=self.new_profile).pack(pady=5)
        ctk.CTkButton(self.frame_left, text="Rename", command=self.rename_profile).pack(pady=5)
        ctk.CTkButton(self.frame_left, text="Delete", command=self.delete_profile).pack(pady=5)
        ctk.CTkButton(self.frame_left, text="Create From Mods Folder", command=self.profile_from_mods_folder).pack(pady=5)

        # MIDDLE FRAME (Profile Contents)
        self.frame_mid = ctk.CTkFrame(self)
        self.frame_mid.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.frame_mid, text="Profile Contents", font=("Arial",18)).pack(pady=10)
        self.list_files = tk.Listbox(self.frame_mid, bg='#2b2b2b', fg='white', selectbackground='#1f6aa5')
        self.list_files.pack(fill="both", expand=True, padx=10)
        scrollbar_files = tk.Scrollbar(self.frame_mid, command=self.list_files.yview)
        self.list_files.config(yscrollcommand=scrollbar_files.set)
        scrollbar_files.pack(side='right', fill='y')
        ctk.CTkButton(self.frame_mid, text="Add ZIP / Folder", command=self.add_to_profile).pack(pady=5)
        ctk.CTkButton(self.frame_mid, text="Remove", command=self.remove_from_profile).pack(pady=5)
        ctk.CTkButton(self.frame_mid, text="Export as ZIP", command=self.export_profile).pack(pady=5)

        # RIGHT FRAME (Mods Folder)
        self.frame_right = ctk.CTkFrame(self)
        self.frame_right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.frame_right, text="Mods Folder", font=("Arial",18)).pack(pady=10)
        self.mods_entry = ctk.CTkEntry(self.frame_right, width=350)
        self.mods_entry.pack(pady=5)
        ctk.CTkButton(self.frame_right, text="Select Folder", command=self.select_mods_folder).pack(pady=5)
        ctk.CTkButton(self.frame_right, text="Auto-Detect", command=self.autodetect_mods_folder).pack(pady=5)
        ctk.CTkButton(self.frame_right, text="Activate Profile", command=self.confirm_activate).pack(pady=15)
        ctk.CTkButton(self.frame_right, text="Unload Mods", command=self.confirm_unload).pack(pady=5)
        self.progress = ctk.CTkProgressBar(self.frame_right)
        self.progress.pack(fill="x", padx=20, pady=20)
        self.progress.set(0)

    # CONFIG
    def save_config(self):
        with open(CONFIG_FILE, "w") as f: json.dump({"mods_folder": self.mods_folder}, f, indent=4)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE,"r") as f:
                cfg = json.load(f)
                self.mods_folder = cfg.get("mods_folder","")
                if self.mods_folder: self.mods_entry.insert(0,self.mods_folder)

    # PROFILES
    def load_profiles(self):
        self.list_profiles.delete(0,"end")
        profiles = [p for p in os.listdir(PROFILES_DIR) if os.path.isdir(os.path.join(PROFILES_DIR,p))]
        for p in profiles: self.list_profiles.insert("end",p)

    def load_profile_contents(self, event=None):
        prof = self.get_selected_profile()
        self.list_files.delete(0, 'end')
        if not prof: return
        prof_path = os.path.join(PROFILES_DIR, prof)
        for item in os.listdir(prof_path):
            self.list_files.insert('end', item)

    def get_selected_profile(self):
        sel = self.list_profiles.curselection()
        if not sel: return None
        return self.list_profiles.get(sel[0])

    def new_profile(self):
        name = simpledialog.askstring("New Profile","Enter profile name:")
        if not name: return
        os.makedirs(os.path.join(PROFILES_DIR,name), exist_ok=True)
        self.load_profiles()

    def rename_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        new = simpledialog.askstring("Rename","New name:",initialvalue=prof)
        if not new: return
        os.rename(os.path.join(PROFILES_DIR,prof), os.path.join(PROFILES_DIR,new))
        self.load_profiles()

    def delete_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        if messagebox.askyesno("Delete",f"Delete profile '{prof}'?"):
            shutil.rmtree(os.path.join(PROFILES_DIR,prof), ignore_errors=True)
            self.load_profiles()

    def profile_from_mods_folder(self):
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror('Error','Set a valid mods folder first'); return
        name = simpledialog.askstring('New Profile from Mods','Enter profile name:')
        if not name: return
        dest = os.path.join(PROFILES_DIR,name)
        os.makedirs(dest, exist_ok=True)
        for item in os.listdir(self.mods_folder):
            s,d = os.path.join(self.mods_folder,item), os.path.join(dest,item)
            if os.path.isdir(s): shutil.copytree(s,d,dirs_exist_ok=True)
            else: shutil.copy2(s,d)
        self.load_profiles()
        messagebox.showinfo('BLSM','Profile created from mods folder')

    # PROFILE CONTENTS
    def add_to_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        files = filedialog.askopenfilenames(title="Select ZIP or Folder")
        if not files: return
        dest = os.path.join(PROFILES_DIR,prof)
        for f in files:
            if os.path.isfile(f) and f.endswith(".zip"):
                zip_safe_extract(f,dest)
            elif os.path.isdir(f):
                shutil.copytree(f,os.path.join(dest,os.path.basename(f)),dirs_exist_ok=True)
        self.load_profile_contents()

    def remove_from_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        sel = self.list_files.curselection()
        if not sel: return
        item = self.list_files.get(sel[0])
        target = os.path.join(PROFILES_DIR,prof,item)
        if os.path.exists(target):
            try:
                if os.path.isdir(target): shutil.rmtree(target)
                else: os.remove(target)
            except: pass
        self.load_profile_contents()

    def export_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        export_path = filedialog.asksaveasfilename(defaultextension=".zip")
        if not export_path: return
        prof_path = os.path.join(PROFILES_DIR,prof)
        with zipfile.ZipFile(export_path,"w",zipfile.ZIP_DEFLATED) as zipf:
            for root,dirs,files in os.walk(prof_path):
                for f in files:
                    fp = os.path.join(root,f)
                    arc = os.path.relpath(fp,prof_path)
                    zipf.write(fp,arc)
        messagebox.showinfo('BLSM','Profile exported successfully')

    # MODS FOLDER
    def select_mods_folder(self):
        folder = filedialog.askdirectory(title="Select Bonelab Mods Folder")
        if not folder: return
        self.mods_folder = folder
        self.mods_entry.delete(0,'end')
        self.mods_entry.insert(0,folder)
        self.save_config()

    def autodetect_mods_folder(self):
        try:
            user = os.environ.get('USERPROFILE','')
            folder = os.path.join(user,'AppData','LocalLow','Stress Level Zero','BONELAB','Mods')
            if os.path.exists(folder):
                self.mods_folder = folder
                self.mods_entry.delete(0,'end')
                self.mods_entry.insert(0,folder)
                self.save_config()
                messagebox.showinfo("Auto-Detect",f"Found mods folder:\n{folder}")
            else:
                messagebox.showwarning("Auto-Detect","Mods folder not found. Please select manually.")
        except Exception as e:
            messagebox.showerror("Auto-Detect Error",f"Failed:\n{e}")

    # ACTIVATE / UNLOAD
    def confirm_activate(self):
        prof = self.get_selected_profile()
        if not prof: messagebox.showerror('Error','Select a profile first'); return
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror('Error','Set a valid mods folder first'); return
        if messagebox.askyesno('Confirm',f'Clear mods folder and activate profile "{prof}"?'):
            self.activate_profile()

    def activate_profile(self):
        prof = self.get_selected_profile()
        if not prof: return
        prof_path = os.path.join(PROFILES_DIR,prof)
        for item in os.listdir(self.mods_folder):
            p = os.path.join(self.mods_folder,item)
            try:
                if os.path.isdir(p): shutil.rmtree(p)
                else: os.remove(p)
            except: pass
        for item in os.listdir(prof_path):
            s,d = os.path.join(prof_path,item), os.path.join(self.mods_folder,item)
            if os.path.isdir(s): shutil.copytree(s,d,dirs_exist_ok=True)
            else: shutil.copy2(s,d)
        messagebox.showinfo('BLSM','Profile activated')

    def confirm_unload(self):
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror('Error','Set a valid mods folder first'); return
        if messagebox.askyesno('Confirm','Unload (clear) all mods?'):
            for item in os.listdir(self.mods_folder):
                p = os.path.join(self.mods_folder,item)
                try:
                    if os.path.isdir(p): shutil.rmtree(p)
                    else: os.remove(p)
                except: pass
            messagebox.showinfo('BLSM','Mods folder cleared')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ensure_dirs()
    app = BLSMApp()
    app.mainloop()
