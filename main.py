import customtkinter as ctk

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class VeloceNodeMateApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Veloce Node-Mate: Autonomous DePIN Watchdog")
        self.geometry("800x600")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header / Dashboard ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Veloce Node-Mate Dashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        self.start_button = ctk.CTkButton(self.header_frame, text="Start Nodes", command=self.start_nodes)
        self.start_button.pack(pady=10)

        # --- Console Area ---
        self.console_frame = ctk.CTkFrame(self)
        self.console_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        self.console_label = ctk.CTkLabel(self.console_frame, text="System Console", font=ctk.CTkFont(size=14, weight="bold"))
        self.console_label.pack(pady=5)

        self.console_textbox = ctk.CTkTextbox(self.console_frame, width=700, height=300)
        self.console_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        self.console_textbox.insert("0.0", "Initializing...\nConnecting to DePIN networks...\nStanding by for user command.")
        self.console_textbox.configure(state="disabled")

        # --- Ad Space Placeholder ---
        self.ad_frame = ctk.CTkFrame(self, height=90, fg_color="gray")
        self.ad_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.ad_frame.pack_propagate(False) # Keep the height fixed
        
        self.ad_label = ctk.CTkLabel(self.ad_frame, text="[PAID ADVERTISING SPACE 728x90]", text_color="black", font=ctk.CTkFont(size=16, weight="bold"))
        self.ad_label.pack(expand=True)

    def start_nodes(self):
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", "\n[System] Attempting to start node sequence... (Beta feature restricted)")
        self.console_textbox.configure(state="disabled")
        self.console_textbox.see("end")

if __name__ == "__main__":
    app = VeloceNodeMateApp()
    app.mainloop()
