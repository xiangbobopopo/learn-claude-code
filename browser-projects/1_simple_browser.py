#!/usr/bin/env python3
"""
Simple Web Browser using Python and Tkinter
This creates a basic browser with navigation controls
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
from urllib.parse import urlparse

class SimpleBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Browser")
        self.root.geometry("800x600")

        # Create the UI
        self.create_ui()
        
    def create_ui(self):
        # Navigation bar
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Back button
        self.back_btn = ttk.Button(nav_frame, text="←", command=self.go_back)
        self.back_btn.pack(side=tk.LEFT)
        
        # Forward button
        self.forward_btn = ttk.Button(nav_frame, text="→", command=self.go_forward)
        self.forward_btn.pack(side=tk.LEFT)
        
        # URL entry
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(nav_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.bind('<Return>', self.navigate_to_url)
        
        # Go button
        self.go_btn = ttk.Button(nav_frame, text="Go", command=self.navigate)
        self.go_btn.pack(side=tk.LEFT)
        
        # Refresh button
        self.refresh_btn = ttk.Button(nav_frame, text="↻", command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def navigate(self):
        url = self.url_var.get().strip()
        if not url:
            return

        # Add protocol if missing
        if not urlparse(url).scheme:
            url = "https://" + url

        self.url_var.set(url)
        self.status_var.set(f"Loading {url}...")

        # Open in default browser (since Tkinter doesn't have built-in web
        # rendering)
        webbrowser.open(url)
        self.status_var.set(f"Loaded {url}")
        
    def navigate_to_url(self, event=None):
        self.navigate()
        
    def go_back(self):
        self.status_var.set("Back button clicked")
        
    def go_forward(self):
        self.status_var.set("Forward button clicked")
        
    def refresh(self):
        if self.url_var.get():
            self.navigate()

if __name__ == "__main__":
    root = tk.Tk()
    browser = SimpleBrowser(root)
    root.mainloop()
