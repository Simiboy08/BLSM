import os
import shutil
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "blsm_config.json"
PROFILES_DIR = "profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

class BLSMApp:
    """
    BLSM – Bonelab Mod Manager.
    Handles profiles, mods folder, and exporting profiles as zip.
    """
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("BLSM – Bonelab Mod Manager")
        self.root.geometry("900x500")

        self.mods_folder = ""
        self.load_config()

        self.build_ui()
        self.refresh_profiles()

        self.root.mainloop()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                import json
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.mods_folder = data.get('mods_folder','')
            except:
                pass

    def save_config(self):
        import json
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'mods_folder': self.mods_folder}, f, indent=2)

    def build_ui(self):
        
        self.frame_left = ctk.CTkFrame(self.root)
        self.frame_left.pack(side='left', fill='y', padx=10, pady=10)

        ctk.CTkLabel(self.frame_left, text="Profiles", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor='w')
        self.list_profiles = tk.Listbox(self.frame_left, height=20, width=28, bg='#2b2b2b', fg='white', selectbackground='#1f6aa5')
        self.list_profiles.pack(pady=10)
        self.list_profiles.bind('<<ListboxSelect>>', lambda e: self.load_profile_contents())

        ctk.CTkButton(self.frame_left, text="New", command=self.new_profile).pack(fill='x', pady=2)
        ctk.CTkButton(self.frame_left, text="Rename", command=self.rename_profile).pack(fill='x', pady=2)
        ctk.CTkButton(self.frame_left, text="Delete", command=self.delete_profile).pack(fill='x', pady=2)
        
        ctk.CTkButton(self.frame_left, text="Create Profile from Mods Folder", command=self.create_profile_from_mods).pack(fill='x', pady=2)

      
        self.frame_mid = ctk.CTkFrame(self.root)
        self.frame_mid.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.frame_mid, text="Profile Contents", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor='w')
        self.list_contents = tk.Listbox(self.frame_mid, height=20, bg='#2b2b2b', fg='white', selectbackground='#1f6aa5')
        self.list_contents.pack(fill='both', expand=True, pady=10)

        ctk.CTkButton(self.frame_mid, text="Add ZIP/Folder", command=self.add_to_profile).pack(fill='x', pady=2)
        ctk.CTkButton(self.frame_mid, text="Remove Selected", command=self.remove_from_profile).pack(fill='x', pady=2)
        ctk.CTkButton(self.frame_mid, text="Export as ZIP", command=self.export_profile).pack(fill='x', pady=2)

        
        self.frame_right = ctk.CTkFrame(self.root)
        self.frame_right.pack(side='right', fill='y', padx=10, pady=10)

        ctk.CTkLabel(self.frame_right, text="Mods Folder", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor='w')
        self.mods_entry = ctk.CTkEntry(self.frame_right, width=250)
        self.mods_entry.pack(pady=5)
        self.mods_entry.insert(0,self.mods_folder)

        ctk.CTkButton(self.frame_right, text="Select Folder", command=self.select_mods_folder).pack(fill='x', pady=2)
        ctk.CTkButton(self.frame_right, text="Auto-Detect", command=self.autodetect_mods_folder).pack(fill='x', pady=2)

        ctk.CTkButton(self.frame_right, text="Activate Profile", command=self.confirm_activate).pack(fill='x', pady=10)
        ctk.CTkButton(self.frame_right, text="Unload Mods", command=self.confirm_unload).pack(fill='x')

    
    def refresh_profiles(self):
        self.list_profiles.delete(0,'end')
        for name in sorted(os.listdir(PROFILES_DIR)):
            if os.path.isdir(os.path.join(PROFILES_DIR,name)):
                self.list_profiles.insert('end', name)

    def selected_profile(self):
        sel = self.list_profiles.curselection()
        if not sel: return None
        return self.list_profiles.get(sel[0])

    def load_profile_contents(self):
        prof = self.selected_profile()
        self.list_contents.delete(0,'end')
        if not prof: return
        path = os.path.join(PROFILES_DIR, prof)
        for root,dirs,files in os.walk(path):
            for f in files:
                self.list_contents.insert('end', os.path.relpath(os.path.join(root,f), path))

    def new_profile(self):
        name = simpledialog.askstring("New Profile","Profile name:")
        if not name: return
        os.makedirs(os.path.join(PROFILES_DIR,name), exist_ok=True)
        self.refresh_profiles()

    def rename_profile(self):
        prof = self.selected_profile()
        if not prof: return
        new = simpledialog.askstring("Rename Profile","New name:",initialvalue=prof)
        if not new: return
        os.rename(os.path.join(PROFILES_DIR,prof), os.path.join(PROFILES_DIR,new))
        self.refresh_profiles()

    def delete_profile(self):
        prof = self.selected_profile()
        if not prof: return
        if not messagebox.askyesno("Confirm","Delete profile?" ): return
        shutil.rmtree(os.path.join(PROFILES_DIR,prof))
        self.refresh_profiles()

    
    def create_profile_from_mods(self):
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror("Error","Mods folder not set or does not exist")
            return
        name = simpledialog.askstring("New Profile from Mods","Enter profile name:")
        if not name: return
        dest = os.path.join(PROFILES_DIR, name)
        os.makedirs(dest, exist_ok=True)
        for item in os.listdir(self.mods_folder):
            s = os.path.join(self.mods_folder,item)
            d = os.path.join(dest,item)
            if os.path.isdir(s): shutil.copytree(s,d,dirs_exist_ok=True)
            else: shutil.copy2(s,d)
        self.refresh_profiles()
        messagebox.showinfo("BLSM","Profile created from current mods folder")

    
    def add_to_profile(self):
        prof = self.selected_profile()
        if not prof: return
        files = filedialog.askopenfilenames()
        if not files: return
        dest = os.path.join(PROFILES_DIR, prof)
        for f in files:
            if os.path.isdir(f): shutil.copytree(f, os.path.join(dest, os.path.basename(f)), dirs_exist_ok=True)
            else: shutil.copy2(f, dest)
        self.load_profile_contents()

    def remove_from_profile(self):
        prof = self.selected_profile()
        if not prof: return
        sel = list(self.list_contents.curselection())
        if not sel: return
        path = os.path.join(PROFILES_DIR, prof)
        for i in reversed(sel):
            f = self.list_contents.get(i)
            p = os.path.join(path,f)
            if os.path.isdir(p): shutil.rmtree(p)
            else: os.remove(p)
            self.list_contents.delete(i)

    def export_profile(self):
        prof = self.selected_profile()
        if not prof: return
        path = filedialog.asksaveasfilename(defaultextension='.zip')
        if not path: return
        src = os.path.join(PROFILES_DIR,prof)
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as zf:
            for root,dirs,files in os.walk(src):
                for f in files:
                    zf.write(os.path.join(root,f), os.path.relpath(os.path.join(root,f),src))

    
    def select_mods_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.mods_folder = folder
            self.mods_entry.delete(0,'end')
            self.mods_entry.insert(0,folder)
            self.save_config()

    def autodetect_mods_folder(self):
        user = os.environ.get('USERPROFILE','')
        folder = os.path.join(user,'AppData','LocalLow','Stress Level Zero','BONELAB','Mods')
        if os.path.exists(folder):
            self.mods_folder = folder
            self.mods_entry.delete(0,'end')
            self.mods_entry.insert(0,folder)
            self.save_config()
            messagebox.showinfo("Auto-Detect", f"Found mods folder:\n{folder}")
        else:
            messagebox.showinfo("Auto-Detect","Mods folder not found. Select manually.")

    
    def confirm_activate(self):
        if not self.selected_profile(): return
        if not self.mods_folder: return
        if messagebox.askyesno("Confirm","Clear mods folder and activate profile?"):
            self.activate_profile()

    def confirm_unload(self):
        if not self.mods_folder: return
        if messagebox.askyesno("Confirm","Unload all mods?"):
            self.clear_folder(self.mods_folder)
            messagebox.showinfo("BLSM","Mods folder cleared")

    
    def clear_folder(self, folder):
        for item in os.listdir(folder):
            p = os.path.join(folder,item)
            if os.path.isdir(p): shutil.rmtree(p)
            else: os.remove(p)

    def activate_profile(self):
        prof = self.selected_profile()
        path = os.path.join(PROFILES_DIR,prof)
        self.clear_folder(self.mods_folder)
        for item in os.listdir(path):
            s = os.path.join(path,item)
            d = os.path.join(self.mods_folder,item)
            if os.path.isdir(s): shutil.copytree(s,d,dirs_exist_ok=True)
            else: shutil.copy2(s,d)
        messagebox.showinfo("BLSM","Profile activated")

if __name__ == '__main__':
   
    BLSMApp()

