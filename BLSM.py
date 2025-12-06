#!/usr/bin/env python3
"""
BLSM v2 - Bonelab Simple Mod Manager (Final)
- Ensures working dir is the script/exe folder (fixes disappearing profiles)
- Profiles folder created next to script/exe
- Dark UI using CustomTkinter when available (falls back to Tkinter look)
- ZIP extraction with safe extraction and simple auto-fix for nested folders
- Profiles: create / rename / delete / create-from-mods / export
- Add ZIP/Folder to profile (ZIPs are extracted into profile)
- Activate profile (copy profile contents into Mods folder) and Unload (clear Mods)
- Profile contents are shown when selecting a profile
- Scrollbars on lists, dark-friendly colors
Save this file as BLSM.py and run with the same Python used to build your EXE.
"""

import os
import sys
import shutil
import zipfile
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# --- Ensure working directory is the script/executable folder ---
if getattr(sys, "frozen", False):
    # Running as EXE
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    os.chdir(SCRIPT_DIR)
except Exception:
    pass

# --- Optional nicer UI with customtkinter ---
USE_CTK = False
try:
    import customtkinter as ctk
    USE_CTK = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except Exception:
    ctk = None  # fallback to plain Tkinter widgets

# --- Constants ---
CONFIG_FILE = "blsm_config.json"
PROFILES_DIR = "profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

# --- Utility functions ---


def safe_extract_member(zf: zipfile.ZipFile, member: str, target_dir: str):
    """
    Safely extract a member (prevents ZipSlip).
    """
    # Normalize path and ensure it stays inside target_dir
    dest_path = os.path.normpath(os.path.join(target_dir, member))
    if not dest_path.startswith(os.path.normpath(target_dir)):
        raise Exception("Illegal file path in zip (ZipSlip attempt)")
    # Create parent directories
    parent = os.path.dirname(dest_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    # Extract file content
    with zf.open(member) as src, open(dest_path, "wb") as dst:
        shutil.copyfileobj(src, dst)


def extract_zip_autofix(zip_path: str, dest: str):
    """
    Extract zip to dest. Try to auto-fix single-top-folder zips by moving contents up.
    This is a simple heuristic (if the zip contains exactly one top-level folder).
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        # collect top-level entries
        top_levels = set()
        for n in zf.namelist():
            part = n.split("/", 1)[0]
            if part:
                top_levels.add(part)
        # extract all safely
        for member in zf.namelist():
            # skip directory entries — zipfile.extract will handle them, but we use safe extraction for files
            if member.endswith("/"):
                continue
            # If single top-level folder, strip it
            if len(top_levels) == 1:
                root = list(top_levels)[0]
                if member.startswith(root + "/"):
                    member_stripped = member[len(root) + 1 :]
                else:
                    member_stripped = member
            else:
                member_stripped = member
            # skip empty names
            if not member_stripped:
                continue
            safe_extract_member(zf, member, dest)  # writes to dest/member (we'll handle nested folder fix below)
    # If zip had a single top-level folder that was extracted, try to flatten
    try:
        # find entries in dest
        entries = os.listdir(dest)
        if len(entries) == 1:
            single = os.path.join(dest, entries[0])
            if os.path.isdir(single):
                # move contents up
                for child in os.listdir(single):
                    shutil.move(os.path.join(single, child), os.path.join(dest, child))
                try:
                    os.rmdir(single)
                except Exception:
                    pass
    except FileNotFoundError:
        pass


# --- App class ---


class BLSMApp:
    def __init__(self):
        # Create main window (use CTk if available for nicer look)
        if USE_CTK:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
        self.root.title("BLSM — Bonelab Mod Manager")
        self.root.geometry("980x560")

        # state
        self.mods_folder = ""
        self.load_config()

        # build UI
        self.build_ui()

        # initial load
        self.refresh_profiles()
        # If we have last selected in config, try to select it
        try:
            last = getattr(self, "config", {}).get("last_profile", None)
            if last:
                idx = None
                for i, p in enumerate(self.list_profiles.get(0, "end")):
                    if p == last:
                        idx = i
                        break
                if idx is not None:
                    self.list_profiles.selection_set(idx)
                    self.list_profiles.activate(idx)
                    self.load_profile_contents()
        except Exception:
            pass

    # ---------- UI ----------
    def build_ui(self):
        # choose widget classes
        Frame = ctk.CTkFrame if USE_CTK else tk.Frame
        Button = ctk.CTkButton if USE_CTK else tk.Button
        Label = ctk.CTkLabel if USE_CTK else tk.Label
        Entry = ctk.CTkEntry if USE_CTK else tk.Entry

        # layout: three columns
        root = self.root
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.columnconfigure(2, weight=2)

        # left: profiles
        left = Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        Label(left, text="Profiles", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        # profiles listbox with dark look
        self.list_profiles = tk.Listbox(left, bg="#2b2b2b", fg="white", selectbackground="#1f6aa5", height=22)
        self.list_profiles.pack(fill="both", expand=True, pady=6)
        # scrollbar for profiles
        sbp = tk.Scrollbar(left, orient="vertical", command=self.list_profiles.yview)
        self.list_profiles.config(yscrollcommand=sbp.set)
        sbp.pack(side="right", fill="y")
        self.list_profiles.bind("<<ListboxSelect>>", lambda e: self.load_profile_contents())

        # profile buttons
        Button(left, text="New", command=self.new_profile).pack(fill="x", pady=3)
        Button(left, text="Rename", command=self.rename_profile).pack(fill="x", pady=3)
        Button(left, text="Delete", command=self.delete_profile).pack(fill="x", pady=3)
        Button(left, text="Create from Mods Folder", command=self.create_profile_from_mods).pack(fill="x", pady=6)

        # middle: profile contents
        mid = Frame(root)
        mid.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        Label(mid, text="Profile Contents", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.list_contents = tk.Listbox(mid, bg="#2b2b2b", fg="white", selectbackground="#1f6aa5")
        self.list_contents.pack(fill="both", expand=True, pady=6)
        sbc = tk.Scrollbar(mid, orient="vertical", command=self.list_contents.yview)
        self.list_contents.config(yscrollcommand=sbc.set)
        sbc.pack(side="right", fill="y")

        Button(mid, text="Add ZIP / Folder", command=self.add_to_profile).pack(fill="x", pady=3)
        Button(mid, text="Remove Selected", command=self.remove_from_profile).pack(fill="x", pady=3)
        Button(mid, text="Export as ZIP", command=self.export_profile).pack(fill="x", pady=3)

        # right: mods folder and actions
        right = Frame(root)
        right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        Label(right, text="Mods Folder", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.mods_entry = Entry(right, width=40)
        # if Entry is ctk entry, its insert signature same as tk.Entry; if fallback Entry is tk.Entry, it's fine
        self.mods_entry.pack(pady=6)
        if self.mods_folder:
            try:
                self.mods_entry.delete(0, "end")
                self.mods_entry.insert(0, self.mods_folder)
            except Exception:
                pass

        Button(right, text="Select Folder", command=self.select_mods_folder).pack(fill="x", pady=3)
        Button(right, text="Auto-Detect", command=self.autodetect_mods_folder).pack(fill="x", pady=3)

        # extraction target radio (extract zip into profile or into mods folder)
        self.extract_target_var = tk.StringVar(value="profile")
        tk.Label(right, text="When adding ZIPs, extract to:").pack(anchor="w", pady=(10, 0))
        r1 = tk.Radiobutton(right, text="Profile (default)", variable=self.extract_target_var, value="profile")
        r2 = tk.Radiobutton(right, text="Mods folder", variable=self.extract_target_var, value="mods")
        r1.pack(anchor="w")
        r2.pack(anchor="w")

        Button(right, text="Activate Profile (copy)", command=self.confirm_activate).pack(fill="x", pady=8)
        Button(right, text="Unload Mods (clear)", command=self.confirm_unload).pack(fill="x", pady=3)

        # small status label
        self.status_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self.status_var, wraplength=220, justify="left").pack(pady=(10, 0))

    # ---------- Config ----------
    def load_config(self):
        self.config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    self.mods_folder = self.config.get("mods_folder", "")
            except Exception:
                self.config = {}
        # ensure profiles dir exists
        os.makedirs(PROFILES_DIR, exist_ok=True)

    def save_config(self):
        try:
            self.config["mods_folder"] = self.mods_folder
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    # ---------- Profiles ----------
    def refresh_profiles(self):
        self.list_profiles.delete(0, "end")
        try:
            for name in sorted(os.listdir(PROFILES_DIR)):
                path = os.path.join(PROFILES_DIR, name)
                if os.path.isdir(path):
                    self.list_profiles.insert("end", name)
        except Exception:
            pass

    def get_selected_profile(self):
        sel = self.list_profiles.curselection()
        if not sel:
            return None
        return self.list_profiles.get(sel[0])

    def load_profile_contents(self, event=None):
        prof = self.get_selected_profile()
        self.list_contents.delete(0, "end")
        # save last profile in config
        if prof:
            self.config["last_profile"] = prof
            self.save_config()
        if not prof:
            return
        profile_path = os.path.join(PROFILES_DIR, prof)
        try:
            # list top-level entries (folders/files) for clarity
            for entry in sorted(os.listdir(profile_path)):
                self.list_contents.insert("end", entry)
        except Exception:
            pass

    def new_profile(self):
        name = simpledialog.askstring("New Profile", "Profile name:")
        if not name:
            return
        path = os.path.join(PROFILES_DIR, name)
        if os.path.exists(path):
            messagebox.showerror("Error", "Profile already exists.")
            return
        try:
            os.makedirs(path, exist_ok=False)
            self.refresh_profiles()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create profile: {e}")

    def rename_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            return
        new = simpledialog.askstring("Rename Profile", "New name:", initialvalue=prof)
        if not new or new == prof:
            return
        src = os.path.join(PROFILES_DIR, prof)
        dst = os.path.join(PROFILES_DIR, new)
        if os.path.exists(dst):
            messagebox.showerror("Error", "Target profile name already exists.")
            return
        try:
            os.rename(src, dst)
            self.refresh_profiles()
        except Exception as e:
            messagebox.showerror("Error", f"Rename failed: {e}")

    def delete_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            return
        if not messagebox.askyesno("Confirm", f"Delete profile '{prof}'?"):
            return
        try:
            shutil.rmtree(os.path.join(PROFILES_DIR, prof))
            self.refresh_profiles()
            self.list_contents.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")

    def create_profile_from_mods(self):
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror("Error", "Set a valid mods folder first.")
            return
        name = simpledialog.askstring("New Profile from Mods", "Enter profile name:")
        if not name:
            return
        dest = os.path.join(PROFILES_DIR, name)
        if os.path.exists(dest):
            messagebox.showerror("Error", "Profile already exists.")
            return
        try:
            os.makedirs(dest, exist_ok=True)
            for item in os.listdir(self.mods_folder):
                s = os.path.join(self.mods_folder, item)
                d = os.path.join(dest, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            self.refresh_profiles()
            messagebox.showinfo("BLSM", "Profile created from mods folder.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create profile: {e}")

    # ---------- Profile contents management ----------
    def add_to_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            messagebox.showerror("Error", "Select a profile first.")
            return
        files = filedialog.askopenfilenames(title="Select ZIP files or folders (hold Ctrl for many)")
        if not files:
            return
        dest_profile = os.path.join(PROFILES_DIR, prof)
        for f in files:
            try:
                if os.path.isfile(f) and f.lower().endswith(".zip"):
                    # choose target based on radio
                    target_choice = self.extract_target_var.get()
                    target = dest_profile if target_choice == "profile" else self.mods_folder
                    if target_choice == "mods" and (not self.mods_folder or not os.path.exists(self.mods_folder)):
                        messagebox.showerror("Error", "Mods folder not set or doesn't exist.")
                        continue
                    extract_zip_autofix(f, target)
                elif os.path.isdir(f):
                    shutil.copytree(f, os.path.join(dest_profile, os.path.basename(f)), dirs_exist_ok=True)
                else:
                    # regular file -> copy into profile
                    shutil.copy2(f, dest_profile)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add {f}: {e}")
        self.load_profile_contents()

    def remove_from_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            return
        sel = self.list_contents.curselection()
        if not sel:
            return
        profile_path = os.path.join(PROFILES_DIR, prof)
        # remove selected entries (top-level)
        for i in reversed(sel):
            name = self.list_contents.get(i)
            target = os.path.join(profile_path, name)
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                elif os.path.exists(target):
                    os.remove(target)
                self.list_contents.delete(i)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove {name}: {e}")

    def export_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            return
        prof_path = os.path.join(PROFILES_DIR, prof)
        save = filedialog.asksaveasfilename(title="Export profile as ZIP", defaultextension=".zip",
                                            filetypes=[("Zip files", "*.zip")], initialfile=f"{prof}.zip")
        if not save:
            return
        try:
            with zipfile.ZipFile(save, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(prof_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        arc = os.path.relpath(fp, prof_path)
                        zf.write(fp, arc)
            messagebox.showinfo("BLSM", "Profile exported.")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    # ---------- Mods folder ----------
    def select_mods_folder(self):
        folder = filedialog.askdirectory(title="Select Bonelab Mods Folder")
        if not folder:
            return
        self.mods_folder = folder
        # try to set in entry
        try:
            self.mods_entry.delete(0, "end")
            self.mods_entry.insert(0, folder)
        except Exception:
            pass
        self.save_config()

    def autodetect_mods_folder(self):
        try:
            user = os.environ.get("USERPROFILE", "")
            candidate = os.path.join(user, "AppData", "LocalLow", "Stress Level Zero", "BONELAB", "Mods")
            if os.path.exists(candidate):
                self.mods_folder = candidate
                try:
                    self.mods_entry.delete(0, "end")
                    self.mods_entry.insert(0, candidate)
                except Exception:
                    pass
                self.save_config()
                messagebox.showinfo("Auto-Detect", f"Found mods folder:\n{candidate}")
            else:
                messagebox.showwarning("Auto-Detect", "Mods folder not found. Please select manually.")
        except Exception as e:
            messagebox.showerror("Auto-Detect Error", f"Auto-detection failed:\n{e}")

    # ---------- Activate / Unload ----------
    def confirm_activate(self):
        prof = self.get_selected_profile()
        if not prof:
            messagebox.showerror("Error", "Select a profile first.")
            return
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror("Error", "Set a valid mods folder first.")
            return
        if not messagebox.askyesno("Confirm", f'Clear mods folder and activate profile "{prof}"?'):
            return
        self.activate_profile()

    def activate_profile(self):
        prof = self.get_selected_profile()
        if not prof:
            return
        prof_path = os.path.join(PROFILES_DIR, prof)
        if not os.path.exists(prof_path):
            messagebox.showerror("Error", "Profile folder not found.")
            return
        # clear mods folder (try best-effort)
        try:
            for item in os.listdir(self.mods_folder):
                p = os.path.join(self.mods_folder, item)
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
        except Exception as e:
            # non-fatal; warn user
            messagebox.showwarning("Warning", f"Failed to fully clear mods folder: {e}")
        # copy profile contents into mods
        try:
            for item in os.listdir(prof_path):
                s = os.path.join(prof_path, item)
                d = os.path.join(self.mods_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
            messagebox.showinfo("BLSM", "Profile activated.")
        except Exception as e:
            messagebox.showerror("Error", f"Activation failed: {e}")

    def confirm_unload(self):
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showerror("Error", "Set a valid mods folder first.")
            return
        if not messagebox.askyesno("Confirm", "Unload (clear) all mods in the mods folder?"):
            return
        try:
            for item in os.listdir(self.mods_folder):
                p = os.path.join(self.mods_folder, item)
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            messagebox.showinfo("BLSM", "Mods folder cleared.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear mods folder: {e}")

    # ---------- Run ----------
    def run(self):
        self.root.mainloop()


# --------- Entrypoint ---------
if __name__ == "__main__":
    app = BLSMApp()
    app.run()
