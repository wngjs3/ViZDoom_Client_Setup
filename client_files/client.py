#!/usr/bin/env python3

import os
import sys
import argparse
from random import choice
import cv2
import requests
from utils import (
    normalize_angle_deg,
    get_all_objects_info,
    draw_esp_overlay,
    sync_vizdoom_ini,
)
import vizdoom as vzd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
from PIL import Image, ImageTk  # Add PIL
import gc  # Explicit garbage collection management

# Platform check for handling autorelease pool issues on macOS
is_macos = sys.platform == "darwin"
if is_macos:
    try:
        # Prevent autorelease pool issues when using Tkinter and OpenCV on macOS
        os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    except:
        pass


def setup_input_controls(game):
    """Set up control buttons"""
    print("[INFO] Setting up control buttons...")
    game.clear_available_buttons()

    buttons = [
        vzd.Button.MOVE_FORWARD,
        vzd.Button.MOVE_BACKWARD,
        vzd.Button.MOVE_LEFT,
        vzd.Button.MOVE_RIGHT,
        vzd.Button.TURN_LEFT,
        vzd.Button.TURN_RIGHT,
        vzd.Button.ATTACK,
        vzd.Button.USE,
        vzd.Button.TURN_LEFT_RIGHT_DELTA,
        vzd.Button.LOOK_UP_DOWN_DELTA,
        vzd.Button.SELECT_NEXT_WEAPON,
        vzd.Button.SELECT_PREV_WEAPON,
        vzd.Button.SPEED,
        vzd.Button.JUMP,
        vzd.Button.CROUCH,
    ]

    for button in buttons:
        game.add_available_button(button)

    # Key bindings
    print("[INFO] Setting up key bindings...")
    game.add_game_args("+bind e +use")  # Bind E key to use

    # WASD movement key bindings
    game.add_game_args("+bind w +forward")
    game.add_game_args("+bind s +back")
    game.add_game_args("+bind a +moveleft")
    game.add_game_args("+bind d +moveright")

    # Jump and crouch key bindings
    game.add_game_args("+bind space +jump")  # Spacebar for jump only
    game.add_game_args("+bind c +crouch")  # C key for crouch
    game.add_game_args("+bind ctrl +crouch")  # Ctrl key for crouch
    game.add_game_args("+bind capslock +crouch")  # Capslock key for crouch
    game.add_game_args("+viz_respawn_delay 3")
    game.add_game_args("-record multi_rec.lmp")


def setup_game_variables(game):
    """Set up game variables"""
    print("[INFO] Setting up game variables...")
    game_variables = [
        vzd.GameVariable.POSITION_X,
        vzd.GameVariable.POSITION_Y,
        vzd.GameVariable.POSITION_Z,
        vzd.GameVariable.ANGLE,
        vzd.GameVariable.PITCH,  # Add viewing angle needed for ESP functionality
        vzd.GameVariable.HEALTH,
        vzd.GameVariable.ARMOR,
        vzd.GameVariable.SELECTED_WEAPON,
        vzd.GameVariable.AMMO1,
        vzd.GameVariable.AMMO2,
        vzd.GameVariable.DEAD,
        vzd.GameVariable.FRAGCOUNT,
    ]

    for var in game_variables:
        game.add_available_game_variable(var)


def setup_object_info(game):
    """Set up object information"""
    game.set_objects_info_enabled(True)
    game.set_labels_buffer_enabled(True)


def setup_automap(game):
    """Set up automap"""
    game.set_automap_buffer_enabled(True)
    game.set_automap_mode(vzd.AutomapMode.OBJECTS)
    game.set_automap_rotate(False)
    game.set_automap_render_textures(False)


def normalize_angle_deg(deg):
    """Normalize to -180~180 range"""
    while deg > 180:
        deg -= 360
    while deg <= -180:
        deg += 360
    return deg


class ESPOverlayWindow:
    """Tkinter window for displaying ESP overlay"""

    def __init__(self, title="ViZDoom ESP Overlay", width=640, height=480):
        self.root = tk.Toplevel()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.image_on_canvas = None
        self.is_open = True
        self.tk_images = []  # Store image references

        # Bring window to front
        self.root.lift()
        self.root.attributes("-topmost", 1)
        self.root.attributes("-topmost", 0)

    def update_frame(self, frame):
        """Display OpenCV frame in Tkinter window"""
        if not self.is_open:
            return False

        try:
            # Convert OpenCV BGR image to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert NumPy array to PIL image
            pil_image = Image.fromarray(rgb_frame)

            # Convert PIL image to Tkinter-compatible image
            tk_image = ImageTk.PhotoImage(image=pil_image)

            # Store image reference (keep only the last 10)
            self.tk_images.append(tk_image)
            if len(self.tk_images) > 10:
                self.tk_images.pop(0)

            # Delete existing image if present
            if self.image_on_canvas:
                self.canvas.delete(self.image_on_canvas)

            # Draw new image on canvas
            self.image_on_canvas = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=tk_image
            )

            # Update window
            self.root.update()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update ESP frame: {str(e)}")
            return False

    def on_closing(self):
        """Handle window close event"""
        self.is_open = False
        # Clear all image references
        self.tk_images.clear()
        self.image_on_canvas = None

        try:
            # Clean up canvas
            self.canvas.delete("all")
            # Remove root window
            self.root.destroy()
        except:
            pass


class ServerConnectionGUI:
    def __init__(self, root, dashboard_url="http://34.64.56.178:8080"):
        self.root = root
        # Remove trailing slash from URL if present
        self.dashboard_url = dashboard_url.rstrip("/")
        self.servers = []
        self.selected_server = None
        self.game_thread = None
        self.is_connected = False
        self.esp_window = None  # Store ESP window reference

        # GUI setup
        self.root.title("ViZDoom Client Connection")
        self.root.geometry("600x650")  # Increase window size to accommodate new button
        self.root.resizable(False, False)

        # Dark theme setup - explicitly set background color
        self.root.configure(bg="#cccccc")

        # Main frame
        self.main_frame = tk.Frame(self.root, bg="#cccccc", padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Server list label
        self.title_label = tk.Label(
            self.main_frame,
            text="ViZDoom Server List",
            font=("Arial", 18, "bold"),
            bg="#cccccc",
            fg="#000000",
        )
        self.title_label.pack(pady=10)

        # Server status label
        self.status_frame = tk.Frame(self.main_frame, bg="#cccccc")
        self.status_frame.pack(fill=tk.X, pady=5)

        self.status_label = tk.Label(
            self.status_frame,
            text="Loading server list...",
            font=("Arial", 11),
            bg="#cccccc",
            fg="#000000",
        )
        self.status_label.pack(side=tk.LEFT)

        self.refresh_button = tk.Button(
            self.status_frame,
            text="Refresh",
            command=self.load_servers,
            bg="#dddddd",
            fg="#000000",
            font=("Arial", 11, "bold"),
            relief=tk.RAISED,
            padx=10,
            activebackground="#e5e5e5",
            activeforeground="#000000",
        )
        self.refresh_button.pack(side=tk.RIGHT)

        # Server list frame
        self.server_frame = tk.Frame(self.main_frame, bg="#cccccc")
        self.server_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Listbox for displaying server list
        self.server_list = tk.Listbox(
            self.server_frame,
            bg="#ffffff",
            fg="#000000",
            font=("Arial", 12),
            height=10,
            selectbackground="#0066cc",
            selectforeground="#ffffff",
            relief=tk.SUNKEN,
            bd=2,
        )
        self.server_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.server_list.bind("<<ListboxSelect>>", self.on_server_select)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.server_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.server_list.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.server_list.yview)

        # Player information frame
        self.player_frame = tk.LabelFrame(
            self.main_frame,
            text="Player Settings",
            font=("Arial", 12, "bold"),
            bg="#cccccc",
            fg="#000000",
            padx=15,
            pady=10,
        )
        self.player_frame.pack(fill=tk.X, pady=15)

        # Player name
        self.name_frame = tk.Frame(self.player_frame, bg="#cccccc")
        self.name_frame.pack(fill=tk.X, pady=8)

        self.name_label = tk.Label(
            self.name_frame,
            text="Player Name:",
            font=("Arial", 12),
            bg="#cccccc",
            fg="#000000",
        )
        self.name_label.pack(side=tk.LEFT, padx=5)

        self.name_entry = tk.Entry(
            self.name_frame,
            font=("Arial", 12),
            bg="#ffffff",
            fg="#000000",
            insertbackground="#000000",
            relief=tk.SUNKEN,
            bd=2,
            width=20,
        )
        self.name_entry.insert(0, "Player")
        self.name_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Player color
        self.color_frame = tk.Frame(self.player_frame, bg="#cccccc")
        self.color_frame.pack(fill=tk.X, pady=8)

        self.color_label = tk.Label(
            self.color_frame,
            text="Player Color:",
            font=("Arial", 12),
            bg="#cccccc",
            fg="#000000",
        )
        self.color_label.pack(side=tk.LEFT, padx=5)

        # Use OptionMenu instead of combobox
        self.color_var = tk.StringVar(self.color_frame)
        self.color_var.set("Blue")  # Default value
        colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Cyan", "White", "Gray"]

        self.color_menu = tk.OptionMenu(self.color_frame, self.color_var, *colors)
        self.color_menu.config(
            font=("Arial", 11),
            bg="#ffffff",
            fg="#000000",
            activebackground="#e5e5e5",
            activeforeground="#000000",
        )
        self.color_menu["menu"].config(
            bg="#ffffff",
            fg="#000000",
            activebackground="#0066cc",
            activeforeground="#ffffff",
        )
        self.color_menu.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # ESP feature checkbox
        self.esp_frame = tk.Frame(self.player_frame, bg="#cccccc")
        self.esp_frame.pack(fill=tk.X, pady=8)

        self.esp_var = tk.BooleanVar(value=False)
        self.esp_check = tk.Checkbutton(
            self.esp_frame,
            text="Enable ESP Overlay",
            variable=self.esp_var,
            bg="#cccccc",
            fg="#000000",
            selectcolor="#aaaaaa",
            activebackground="#cccccc",
            activeforeground="#000000",
            font=("Arial", 12),
            highlightbackground="#cccccc",
            highlightcolor="#cccccc",
        )
        self.esp_check.pack(anchor=tk.W, pady=5)

        # Buttons frame
        self.buttons_frame = tk.Frame(self.main_frame, bg="#cccccc")
        self.buttons_frame.pack(fill=tk.X, pady=10)

        # Single Player button
        self.singleplayer_button = tk.Button(
            self.buttons_frame,
            text="Start Single Player Game",
            command=self.start_singleplayer,
            bg="#88aadd",
            fg="#000000",
            font=("Arial", 14, "bold"),
            relief=tk.RAISED,
            padx=10,
            pady=10,
            activebackground="#99bbee",
            activeforeground="#000000",
        )
        self.singleplayer_button.pack(pady=10, fill=tk.X)

        # Connect to server button
        self.connect_button = tk.Button(
            self.buttons_frame,
            text="Connect to Selected Server",
            command=self.connect_to_server,
            bg="#dddddd",
            fg="#000000",
            font=("Arial", 14, "bold"),
            relief=tk.RAISED,
            padx=10,
            pady=10,
            activebackground="#e5e5e5",
            activeforeground="#000000",
        )
        self.connect_button.pack(pady=10, fill=tk.X)

        # Load server list
        self.load_servers()

    def load_servers(self):
        """Load server list from dashboard server"""
        self.status_label.config(text="Getting server list...")
        self.refresh_button.config(state=tk.DISABLED)

        # Reset listbox
        self.server_list.delete(0, tk.END)

        # Get server list
        threading.Thread(target=self._fetch_servers).start()

    def _fetch_servers(self):
        """Background load of server list"""
        try:
            # Add timeout to prevent response delay
            response = requests.get(f"{self.dashboard_url}/api/servers", timeout=5)
            if response.status_code == 200:
                self.servers = response.json().get("servers", [])

                # Update UI (execute in main thread)
                self.root.after(0, self._update_server_list)
            else:
                # Update UI on API error
                error_msg = f"Failed to load server list: HTTP {response.status_code}"
                self.root.after(
                    0, lambda msg=error_msg: self.status_label.config(text=msg)
                )
        except requests.exceptions.ConnectionError:
            error_msg = f"Connection failed: Cannot connect to {self.dashboard_url}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        except requests.exceptions.Timeout:
            error_msg = "Connection timeout: Response took too long"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))
        except Exception as e:
            # Update UI on exception
            error_msg = f"Failed to load server list: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.status_label.config(text=msg))

        # Restore button state
        self.root.after(0, lambda: self.refresh_button.config(state=tk.NORMAL))

    def _update_server_list(self):
        """Display server list in listbox"""
        if not self.servers:
            self.status_label.config(text="No servers available.")
            return

        # Add servers to listbox
        for server in self.servers:
            status = "Running" if server["status"] == "running" else server["status"]
            display_text = f"{server['name']} - Port: {server['port']} - Players: {server.get('connected_players', 0)}/{server['players']} - {status}"
            self.server_list.insert(tk.END, display_text)

            # Display running servers in different color
            if server["status"] == "running":
                self.server_list.itemconfig(tk.END, {"bg": "#ddffdd", "fg": "#000000"})

        # Update status
        self.status_label.config(text=f"Available servers: {len(self.servers)}")

    def on_server_select(self, event):
        """Function called when server is selected"""
        if not self.server_list.curselection():
            return

        # Get index of selected item
        idx = self.server_list.curselection()[0]

        # Store server info for the selected index
        if idx < len(self.servers):
            self.selected_server = self.servers[idx]

            # Enable connect button and change color
            self.connect_button.config(state=tk.NORMAL, bg="#88dd88", fg="#000000")
        else:
            self.selected_server = None
            self.connect_button.config(state=tk.DISABLED, bg="#dddddd", fg="#000000")

    def connect_to_server(self):
        """Connect to selected server"""
        if not self.selected_server:
            messagebox.showwarning("Connection Error", "Please select a server.")
            return

        # Warn if already connected to a game
        if self.is_connected and self.game_thread and self.game_thread.is_alive():
            messagebox.showinfo("Notice", "Already connected to a game.")
            return

        # Get player name and color
        player_name = self.name_entry.get().strip()
        if not player_name:
            messagebox.showwarning("Connection Error", "Please enter a player name.")
            return

        # Add ESP tag to player name if ESP is enabled
        use_esp = self.esp_var.get()
        if use_esp and not player_name.endswith("-ESP"):
            player_name += "-ESP"

        # Color number conversion
        color_map = {
            "Red": 0,
            "Blue": 1,
            "Green": 2,
            "Yellow": 3,
            "Purple": 4,
            "Cyan": 5,
            "White": 6,
            "Gray": 7,
        }
        player_color = color_map.get(self.color_var.get(), 1)  # Default to blue

        # Save connection info
        # Extract host from URL (remove http:// or https://)
        host = self.dashboard_url.split("//")[1].split("/")[0]
        # Extract port (if port is included in URL)
        if ":" in host:
            host = host.split(":")[0]

        self.status_label.config(text="ini file sync...")

        connection_info = {
            "host_address": host,
            "port": self.selected_server["port"],
            "name": player_name,
            "color": player_color,
            "use_esp": use_esp,
            "gui_instance": self,  # Pass GUI instance
        }

        # Change button text and color
        self.connect_button.config(
            text="Connecting to Game...", bg="#ffaaaa", fg="#000000", state=tk.DISABLED
        )
        self.refresh_button.config(state=tk.DISABLED)

        # Status display
        self.status_label.config(
            text=f"Connecting to game: {self.selected_server['name']} (Port: {self.selected_server['port']})"
        )

        # Start game thread
        self.is_connected = True
        self.game_thread = threading.Thread(
            target=player_client, kwargs=connection_info
        )
        self.game_thread.daemon = True  # Terminate with main program
        self.game_thread.start()

    def game_disconnected(self):
        """Function called when game connection is terminated"""
        self.is_connected = False

        # ESP window reference removal
        self.esp_window = None

        # UI update in main thread
        if self.root.winfo_exists():  # Check if GUI still exists
            self.root.after(0, self._update_ui_after_disconnect)

    def _update_ui_after_disconnect(self):
        """Update UI after game disconnection"""
        # Restore button state and text
        self.connect_button.config(
            text="Connect to Selected Server",
            bg="#dddddd",
            fg="#000000",
            state=tk.NORMAL,
        )
        self.refresh_button.config(state=tk.NORMAL)

        # Update status display
        self.status_label.config(
            text="Game connection ended. Select a server to reconnect."
        )

        # Refresh server list
        self.load_servers()

    def start_singleplayer(self):
        """Start a single player game"""
        # Warn if already connected to a game
        if self.is_connected and self.game_thread and self.game_thread.is_alive():
            messagebox.showinfo("Notice", "Already connected to a game.")
            return

        # Get player name and color
        player_name = self.name_entry.get().strip()
        if not player_name:
            player_name = "Player"

        # Add ESP tag to player name if ESP is enabled
        use_esp = self.esp_var.get()
        if use_esp and not player_name.endswith("-ESP"):
            player_name += "-ESP"

        # Color number conversion
        color_map = {
            "Red": 0,
            "Blue": 1,
            "Green": 2,
            "Yellow": 3,
            "Purple": 4,
            "Cyan": 5,
            "White": 6,
            "Gray": 7,
        }
        player_color = color_map.get(self.color_var.get(), 1)  # Default to blue

        self.status_label.config(text="ini file sync...")

        # Change button text and color
        self.singleplayer_button.config(
            text="Starting Single Player Game...",
            bg="#ffaaaa",
            fg="#000000",
            state=tk.DISABLED,
        )
        self.connect_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)

        # Status display
        self.status_label.config(text="Starting single player game...")

        # Start game thread
        self.is_connected = True
        self.game_thread = threading.Thread(
            target=play_single_player,
            kwargs={
                "name": player_name,
                "color": player_color,
                "window_visible": True,
                "episode_timeout": 10,
                "use_esp": use_esp,
                "gui_instance": self,
            },
        )
        self.game_thread.daemon = True  # Terminate with main program
        self.game_thread.start()


def player_client(
    host_address="127.0.0.1",
    port=5029,
    name="Player2",
    color=3,
    window_visible=True,
    episode_timeout=1,
    use_esp=False,
    gui_instance=None,  # Add GUI instance
):
    """
    Creates a VizDoom client that connects to a specific host as Player2.

    Args:
        host_address: IP address of the host to connect to
        port: Port to connect to (default: 5029)
        name: Player name
        color: Player color (0-7)
        window_visible: Whether to show the game window
        episode_timeout: Game timeout in minutes
        use_esp: Whether to use ESP overlay
        gui_instance: ServerConnectionGUI instance for callbacks
    """

    print("[INFO] ini file sync...")
    sync_vizdoom_ini()

    # Initialize the game
    game = vzd.DoomGame()
    game_initialized = False
    esp_enabled = False  # Track ESP activation
    esp_window = None  # Tkinter window instance

    # Additional protection for autorelease pool on macOS
    if is_macos:
        try:
            # Call gc at the point of direct resource use
            gc.collect()
        except:
            pass

    # Explicitly specify OpenCV backend (QT may be more stable on macOS)
    # If OpenCV package is compiled with QT support
    try:
        # Most stable backend on macOS
        cv2.setNumThreads(1)  # Limit multithreading for improved stability
        # Remove previous Qt environment variable setting
        if "QT_QPA_PLATFORM" in os.environ:
            del os.environ["QT_QPA_PLATFORM"]
    except Exception as e:
        print(f"[WARN] Error during OpenCV setup: {e}")

    # Load multiplayer configuration
    game.load_config("cig.cfg")
    game.set_mode(vzd.Mode.ASYNC_SPECTATOR)

    # Set window visibility
    game.set_window_visible(window_visible)

    # Join the specified host
    game.add_game_args(f"-join {host_address}:{port}")

    # Set player name and color
    game.add_game_args(f"+name {name} +colorset {color}")

    # Additional game settings
    game.add_game_args(f"+timelimit {episode_timeout}")
    setup_input_controls(game)
    # Add mouse input setting
    game.add_game_args("+freelook 1")
    setup_game_variables(game)

    # Initialize the game first, create ESP after game initialization
    try:
        print(f"Connecting to host at {host_address}:{port}...")
        game.init()
        game_initialized = True
        print(f"Connected as {name}")

        setup_object_info(game)
        setup_automap(game)

        # ESP setup - created after game initialization
        if use_esp:
            try:
                # Create Tkinter ESP window
                esp_window = ESPOverlayWindow(
                    title=f"ViZDoom ESP Overlay - {name}", width=800, height=600
                )
                esp_enabled = True
                # Store ESP window reference in GUI instance
                if gui_instance is not None:
                    gui_instance.esp_window = esp_window
                print("[INFO] ESP overlay window created successfully")
            except Exception as e:
                print(f"[ERROR] Failed to create ESP overlay window: {str(e)}")
                esp_enabled = False
                esp_window = None
    except Exception as e:
        print(f"[ERROR] Game initialization failed: {str(e)}")
        game_initialized = False

    # Main game loop
    try:
        print("Starting game loop...")

        while not game.is_episode_finished():
            # Respawn if dead
            if game.is_player_dead():
                game.respawn_player()

            # Get the state
            game.advance_action()
            state = game.get_state()

            if state is None:
                continue

            if esp_enabled and esp_window is not None and esp_window.is_open:
                try:
                    print("[INFO] ESP overlay is activated.")
                    px = game.get_game_variable(vzd.GameVariable.POSITION_X)
                    py = game.get_game_variable(vzd.GameVariable.POSITION_Y)
                    pz = game.get_game_variable(vzd.GameVariable.POSITION_Z)
                    angle_deg = game.get_game_variable(vzd.GameVariable.ANGLE)
                    pitch_deg = game.get_game_variable(vzd.GameVariable.PITCH)
                    print(
                        f"[INFO] Player position: {px}, {py}, {pz}, angle: {angle_deg}, pitch: {pitch_deg}"
                    )
                    angle_deg_norm = normalize_angle_deg(angle_deg)

                    if state.screen_buffer is None:
                        print("[WARN] Screen buffer is None.")
                        continue

                    screen_buf = state.screen_buffer

                    if (
                        len(screen_buf.shape) == 3
                    ):  # Possible (channels, height, width) format
                        # Check each dimension size
                        if screen_buf.shape[0] == 3:  # (channels, height, width)
                            screen_buf = np.transpose(screen_buf, (1, 2, 0))
                        elif (
                            screen_buf.shape[2] == 3
                        ):  # Already (height, width, channels) format
                            pass  # No conversion needed
                        else:  # (width, height, channels) or other format
                            screen_buf = np.transpose(screen_buf, (1, 0, 2))

                    print(
                        f"[INFO] Screen buffer shape after conversion: {screen_buf.shape}"
                    )
                    frame = cv2.cvtColor(screen_buf, cv2.COLOR_RGB2BGR)

                    # Get object information
                    player_objects = []
                    has_object_info = (
                        hasattr(state, "objects") and state.objects is not None
                    )
                    print(f"[INFO] Getting object information: {has_object_info}")

                    if has_object_info:
                        # Print detailed debug info only in first frame
                        debug_detail = 1
                        player_objects = get_all_objects_info(
                            state.objects, px, py, debug_detail
                        )

                        # Print detailed information when objects are detected
                        if player_objects:
                            print(
                                f"[DEBUG] Detected player/enemy objects: {len(player_objects)}"
                            )

                            # Print detailed info for each object
                            for i, obj in enumerate(player_objects):
                                obj_name = obj.get("name", "Unknown")
                                obj_id = obj.get("id", -1)
                                obj_pos = obj.get("position", (0, 0, 0))
                                obj_dist = obj.get("distance", 0)
                                obj_health = obj.get("health", "N/A")
                                obj_dead = (
                                    "Dead" if obj.get("is_dead", False) else "Alive"
                                )

                                print(
                                    f"[DEBUG] Object #{i+1}: ID={obj_id}, name={obj_name}, position={obj_pos}, distance={obj_dist:.1f}, HP={obj_health}, status={obj_dead}"
                                )

                            # Apply ESP overlay
                            try:
                                frame_with_esp = draw_esp_overlay(
                                    frame.copy(),
                                    (px, py, pz),
                                    angle_deg_norm,
                                    pitch_deg,
                                    player_objects,
                                )

                                # Display ESP frame in Tkinter window
                                if not esp_window.update_frame(frame_with_esp):
                                    # Update failed - deactivate ESP
                                    esp_enabled = False

                            except Exception as e:
                                print(
                                    f"[ERROR] ESP overlay application error: {str(e)}"
                                )
                                # Display base frame on error
                                try:
                                    esp_window.update_frame(frame)
                                except:
                                    pass
                        else:
                            # No objects detected - display base frame
                            try:
                                esp_window.update_frame(frame)
                            except:
                                pass
                    else:
                        # No object information - display original screen
                        if state.number % 300 == 0:  # Print message every 300 frames
                            print(
                                "[WARN] Server does not provide object information, ESP feature not working."
                            )
                        try:
                            esp_window.update_frame(frame)
                        except:
                            pass
                except Exception as e:
                    print(f"[ERROR] Error during ESP processing: {str(e)}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    except Exception as e:
        print(f"Error during game connection: {str(e)}")

    finally:
        # Game finished
        print("Game finished!")

        # Additional cleanup on macOS
        if is_macos:
            try:
                # Call gc at the point of direct resource release
                gc.collect()
            except:
                pass

        # Close ESP window first
        if esp_enabled and esp_window is not None:
            try:
                # Close in GUI thread for resource cleanup
                if (
                    gui_instance is not None
                    and hasattr(gui_instance, "root")
                    and gui_instance.root.winfo_exists()
                ):
                    # Remove GUI reference
                    if hasattr(gui_instance, "esp_window"):
                        gui_instance.esp_window = None

                    # Execute window closing in GUI thread
                    gui_instance.root.after(0, esp_window.on_closing)
                    time.sleep(0.2)  # Allow time for window to close
                else:
                    # Close window directly
                    esp_window.on_closing()

                # Remove reference
                esp_window = None
            except Exception as e:
                print(f"[WARN] Failed to close ESP window: {str(e)}")

        # Game cleanup next
        try:
            # Safely close the game
            if game_initialized:
                try:
                    if not game.is_episode_finished():
                        print(
                            f"Player frags: {game.get_game_variable(vzd.GameVariable.FRAGCOUNT)}"
                        )
                except:
                    # Ignore if game variables can't be retrieved
                    pass

                try:
                    game.close()
                except:
                    # Ignore if game close fails
                    pass
        except Exception as e:
            print(f"Error during game shutdown: {str(e)}")

        print("Connection closed")

        # Memory cleanup (call twice to handle circular references)
        gc.collect()
        time.sleep(0.1)  # Allow time for GC work to complete
        gc.collect()

        # Explicitly set to None to decrease reference count
        esp_window = None

        # Execute GUI callback - notify game disconnection
        if gui_instance is not None:
            try:
                gui_instance.game_disconnected()
            except Exception as e:
                print(f"Error during GUI callback: {str(e)}")


def play_single_player(
    name="Player",
    color=3,
    window_visible=True,
    episode_timeout=10,
    use_esp=False,
    gui_instance=None,
):
    """
    Creates a single player VizDoom game.

    Args:
        name: Player name
        color: Player color (0-7)
        window_visible: Whether to show the game window
        episode_timeout: Game timeout in minutes
        use_esp: Whether to use ESP overlay
        gui_instance: ServerConnectionGUI instance for callbacks
    """

    print("[INFO] INI 파일 동기화 중...")
    sync_vizdoom_ini()

    # Initialize the game
    game = vzd.DoomGame()
    game_initialized = False
    esp_enabled = False  # Track ESP activation
    esp_window = None  # Tkinter window instance

    # Additional protection for autorelease pool on macOS
    if is_macos:
        try:
            # Call gc at the point of direct resource use
            gc.collect()
        except:
            pass

    # Explicitly specify OpenCV backend (QT may be more stable on macOS)
    try:
        # Most stable backend on macOS
        cv2.setNumThreads(1)  # Limit multithreading for improved stability
        # Remove previous Qt environment variable setting
        if "QT_QPA_PLATFORM" in os.environ:
            del os.environ["QT_QPA_PLATFORM"]
    except Exception as e:
        print(f"[WARN] Error during OpenCV setup: {e}")

    try:

        # Set game mode to PLAYER mode (single player)
        game.set_mode(vzd.Mode.ASYNC_SPECTATOR)

        # Set larger screen resolution for better gameplay experience
        game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
        game.set_screen_format(vzd.ScreenFormat.RGB24)  # Use RGB24 for better colors

        # Set rendering options for better visuals
        game.set_render_hud(True)
        game.set_render_minimal_hud(False)
        game.set_render_weapon(True)
        game.set_render_crosshair(True)
        game.set_render_decals(True)
        game.set_render_particles(True)
        game.set_render_effects_sprites(True)

        # Set window visibility
        game.set_window_visible(window_visible)

        # Set map to map01
        game.set_doom_map("map02")

        # Additional settings to make the game playable
        game.add_game_args(f"-skill 3 +name {name} +colorset {color}")
        game.add_game_args(f"+timelimit {episode_timeout}")

        # Widescreen support
        game.add_game_args("+vid_aspect 16:9")

        # Set up controls and variables
        setup_input_controls(game)
        setup_game_variables(game)

        # Initialize the game
        print("Starting single player game...")
        game.init()
        game_initialized = True
        print(f"Game started as {name}")

        # Set up object info and automap after initialization
        setup_object_info(game)
        # setup_automap(game) error in single play(no map)
        # ESP setup - created after game initialization
        if use_esp:
            try:
                # Get game screen resolution for ESP window
                screen_width = game.get_screen_width() or 1280
                screen_height = game.get_screen_height() or 720

                # Create Tkinter ESP window with game resolution
                esp_window = ESPOverlayWindow(
                    title=f"ViZDoom ESP Overlay - {name}",
                    width=screen_width,
                    height=screen_height,
                )
                esp_enabled = True
                # Store ESP window reference in GUI instance
                if gui_instance is not None:
                    gui_instance.esp_window = esp_window
                print(
                    f"[INFO] ESP overlay window created with resolution: {screen_width}x{screen_height}"
                )
            except Exception as e:
                print(f"[ERROR] Failed to create ESP overlay window: {str(e)}")
                esp_enabled = False
                esp_window = None

        # Main game loop
        try:
            print("Starting game loop...")

            while not game.is_episode_finished():
                # Respawn if dead
                if game.is_player_dead():
                    game.respawn_player()

                # Update game state
                game.advance_action()
                state = game.get_state()

                if state is None:
                    continue

                # ESP overlay functionality
                if esp_enabled and esp_window is not None and esp_window.is_open:
                    try:
                        print("[INFO] ESP overlay is activated.")
                        px = game.get_game_variable(vzd.GameVariable.POSITION_X)
                        py = game.get_game_variable(vzd.GameVariable.POSITION_Y)
                        pz = game.get_game_variable(vzd.GameVariable.POSITION_Z)
                        angle_deg = game.get_game_variable(vzd.GameVariable.ANGLE)
                        pitch_deg = game.get_game_variable(vzd.GameVariable.PITCH)

                        if state.screen_buffer is None:
                            print("[WARN] Screen buffer is None.")
                            continue

                        screen_buf = state.screen_buffer

                        # Handle different buffer formats
                        if (
                            len(screen_buf.shape) == 3
                        ):  # Possible (channels, height, width) format
                            # Check each dimension size
                            if screen_buf.shape[0] == 3:  # (channels, height, width)
                                screen_buf = np.transpose(screen_buf, (1, 2, 0))
                            elif (
                                screen_buf.shape[2] == 3
                            ):  # Already (height, width, channels) format
                                pass  # No conversion needed
                            else:  # (width, height, channels) or other format
                                screen_buf = np.transpose(screen_buf, (1, 0, 2))

                        frame = cv2.cvtColor(screen_buf, cv2.COLOR_RGB2BGR)

                        # Get object information
                        player_objects = []
                        has_object_info = (
                            hasattr(state, "objects") and state.objects is not None
                        )

                        if has_object_info:
                            # Get objects info
                            player_objects = get_all_objects_info(
                                state.objects, px, py, 0
                            )

                            # Apply ESP overlay
                            try:
                                frame_with_esp = draw_esp_overlay(
                                    frame.copy(),
                                    (px, py, pz),
                                    angle_deg,
                                    pitch_deg,
                                    player_objects,
                                )

                                # Display ESP frame in Tkinter window
                                if not esp_window.update_frame(frame_with_esp):
                                    # Update failed - deactivate ESP
                                    esp_enabled = False

                            except Exception as e:
                                print(
                                    f"[ERROR] ESP overlay application error: {str(e)}"
                                )
                                # Display base frame on error
                                try:
                                    esp_window.update_frame(frame)
                                except:
                                    pass
                        else:
                            # No object information - display original screen
                            try:
                                esp_window.update_frame(frame)
                            except:
                                pass
                    except Exception as e:
                        print(f"[ERROR] Error during ESP processing: {str(e)}")

            print("Episode finished!")
            print(f"Player frags: {game.get_game_variable(vzd.GameVariable.FRAGCOUNT)}")

        except KeyboardInterrupt:
            print("\nInterrupted by user")

        except Exception as e:
            print(f"Error during game: {str(e)}")

    except Exception as e:
        print(f"[ERROR] Game initialization failed: {str(e)}")
        game_initialized = False

    finally:
        # Game cleanup
        print("Game finished!")

        # Additional cleanup on macOS
        if is_macos:
            try:
                # Call gc at the point of direct resource release
                gc.collect()
            except:
                pass

        # Close ESP window first
        if esp_enabled and esp_window is not None:
            try:
                # Close in GUI thread for resource cleanup
                if (
                    gui_instance is not None
                    and hasattr(gui_instance, "root")
                    and gui_instance.root.winfo_exists()
                ):
                    # Remove GUI reference
                    if hasattr(gui_instance, "esp_window"):
                        gui_instance.esp_window = None

                    # Execute window closing in GUI thread
                    gui_instance.root.after(0, esp_window.on_closing)
                    time.sleep(0.2)  # Allow time for window to close
                else:
                    # Close window directly
                    esp_window.on_closing()

                # Remove reference
                esp_window = None
            except Exception as e:
                print(f"[WARN] Failed to close ESP window: {str(e)}")

        # Game cleanup next
        try:
            if game_initialized:
                game.close()
        except Exception as e:
            print(f"Error during game shutdown: {str(e)}")

        print("Game closed")

        # Memory cleanup
        gc.collect()
        time.sleep(0.1)
        gc.collect()

        # Explicitly set to None to decrease reference count
        esp_window = None

        # Execute GUI callback - notify game disconnection
        if gui_instance is not None:
            try:
                gui_instance.game_disconnected()
            except Exception as e:
                print(f"Error during GUI callback: {str(e)}")


if __name__ == "__main__":
    # Add global exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        import traceback

        print(f"Exception occurred: {exc_type.__name__}: {exc_value}")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

        # Attempt cleanup on crash
        try:
            gc.collect()
        except:
            pass

        # Prevent program abnormal termination
        return True

    # Set exception handler to sys.excepthook
    import sys

    sys.excepthook = handle_exception

    # Set QT_API environment variable before creating QApplication
    try:
        # QT5 backend settings
        import os

        # Qt5 backend is more stable on macOS
        os.environ["QT_API"] = "pyqt5"
        # Remove QT_QPA_PLATFORM setting
        if "QT_QPA_PLATFORM" in os.environ:
            del os.environ["QT_QPA_PLATFORM"]
    except:
        pass

    # Connect directly with command line arguments if provided, otherwise show GUI
    parser = argparse.ArgumentParser(description="VizDoom Client")
    parser.add_argument("--host", type=str, help="Host IP address")
    parser.add_argument("--port", type=int, help="Host port")
    parser.add_argument("--name", type=str, help="Player name")
    parser.add_argument(
        "--color", type=int, choices=range(8), help="Player color (0-7)"
    )
    parser.add_argument("--hidden", action="store_true", help="Hide game window")
    parser.add_argument("--timeout", type=int, help="Game timeout in minutes")
    parser.add_argument("--esp", action="store_true", help="Enable ESP overlay")
    parser.add_argument("--dashboard", type=str, help="Dashboard server URL")

    args = parser.parse_args()

    # Connect directly with command line arguments
    if args.host and args.port:
        player_client(
            host_address=args.host,
            port=args.port,
            name=args.name or "Player2",
            color=args.color or 3,
            window_visible=not args.hidden,
            episode_timeout=args.timeout or 1,
            use_esp=args.esp or False,
        )
    else:
        # Run in GUI mode
        dashboard_url = args.dashboard or "http://34.64.56.178:8080"
        root = tk.Tk()
        app = ServerConnectionGUI(root, dashboard_url)
        root.mainloop()
