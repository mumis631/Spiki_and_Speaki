import tkinter as tk
from tkinter import messagebox
import os

# --- 設定データ ---
TILE_SIZE = 20
QUICK_TILE_SIZE = 8  # クイックビュー用の小さいタイルサイズ
COLORS = {
    'S': "#3498db", 'F': "#7f8c8d", 'W': "#2c3e50", 'P': "#e67e22",
    'B': "#d35400", 'M': "#7e6c24", 'G': "#2ecc71", 'D': "#9b59b6",
    'K': "#c0be2d", 'L': "#33bde7", 'R': "#e74c3c"
}
TILE_TYPES = {
    'S': {"w": 2, "h": 3}, 'F': {"w": 2, "h": 2}, 'W': {"w": 2, "h": 2},
    'P': {"w": 2, "h": 1}, 'B': {"w": 2, "h": 2}, 'M': {"w": 2, "h": 2},
    'G': {"w": 2, "h": 2}, 'D': {"w": 2, "h": 3}, 'K': {"w": 2, "h": 2},
    'L': {"w": 2, "h": 1}, 'R': {"w": 2, "h": 1}
}
SAVE_DIR = "stages"
CATEGORIES = ["grassland", "forest", "cave"]

class MapEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Large-Scale Map Editor")
        self.selected_filename = tk.StringVar(value="ファイルを選択してください")
        
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

        # --- UI構成 ---
        # 1. 左側：ファイル選択パネル
        self.file_panel = tk.Frame(root, width=220, bg="#ecf0f1", padx=10, pady=10)
        self.file_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.file_panel.pack_propagate(False) 
        
        tk.Label(self.file_panel, text="STAGE SELECT", font=("Arial", 12, "bold"), bg="#ecf0f1").pack(pady=5)
        
        # ボタンエリア（スクロールが必要な場合に備えFrameで括る）
        btn_frame = tk.Frame(self.file_panel, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X)

        for cat in CATEGORIES:
            frame = tk.LabelFrame(btn_frame, text=cat.capitalize(), bg="#ecf0f1")
            frame.pack(fill=tk.X, pady=2)
            btn_container = tk.Frame(frame, bg="#ecf0f1")
            btn_container.pack()
            for i in range(1, 11):
                fname = f"{cat}_{i:02d}.csv"
                btn = tk.Button(btn_container, text=f"{i:02d}", width=2, 
                                command=lambda f=fname: self.select_file(f))
                btn.grid(row=(i-1)//5, column=(i-1)%5, padx=1, pady=1)

        # --- 追加：クイックビュー領域 ---
        tk.Label(self.file_panel, text="Quick Preview", font=("Arial", 9, "bold"), bg="#ecf0f1").pack(pady=(20, 0))
        self.quick_canvas = tk.Canvas(self.file_panel, bg="white", height=200, highlightthickness=1, highlightbackground="#bdc3c7")
        self.quick_canvas.pack(fill=tk.X, pady=5)

        # 2. 右側：メインエリア
        self.main_area = tk.Frame(root)
        self.main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(self.main_area, pady=5)
        toolbar.pack(fill=tk.X)
        tk.Label(toolbar, textvariable=self.selected_filename, fg="blue", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(toolbar, text="LOAD -> Edit", bg="#2ecc71", fg="white", width=15, command=self.load_file).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="SAVE", bg="#e74c3c", fg="white", width=10, command=self.save_file).pack(side=tk.LEFT, padx=5)

        self.paned = tk.PanedWindow(self.main_area, orient=tk.HORIZONTAL, sashwidth=4, bg="#bdc3c7")
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(self.paned, font=("Courier", 12), undo=True, wrap=tk.NONE)
        self.paned.add(self.text_area, width=580)
        self.text_area.bind("<<Modified>>", self.on_modify)

        self.canvas = tk.Canvas(self.paned, bg="#ffffff")
        self.paned.add(self.canvas)

    def select_file(self, filename):
        """ファイルを選択し、クイックプレビューを表示する"""
        self.selected_filename.set(filename)
        self.quick_draw(filename)

    def quick_draw(self, filename):
        """左下の小窓にCSVの内容を即座に描画する"""
        self.quick_canvas.delete("all")
        path = os.path.join(SAVE_DIR, filename)
        if not os.path.exists(path):
            self.quick_canvas.create_text(100, 100, text="New File", fill="#bdc3c7")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().strip().split('\n')
                for row, line in enumerate(lines):
                    tiles = [t.strip() for t in line.split(',')]
                    for col, char in enumerate(tiles):
                        if char in TILE_TYPES:
                            config = TILE_TYPES[char]
                            w, h = config["w"] * QUICK_TILE_SIZE, config["h"] * QUICK_TILE_SIZE
                            x1, y1 = col * QUICK_TILE_SIZE, row * QUICK_TILE_SIZE
                            self.quick_canvas.create_rectangle(x1, y1, x1+w, y1+h, fill=COLORS.get(char, "#000"), outline="")
        except Exception:
            pass

    def load_file(self):
        """現在選択されているファイルを編集画面に読み込む"""
        fname = self.selected_filename.get()
        path = os.path.join(SAVE_DIR, fname)
        if not os.path.exists(path):
            if messagebox.askyesno("新規", f"{fname} を作成しますか？"):
                self.text_area.delete("1.0", tk.END)
                self.draw_map()
                return
            else: return

        with open(path, "r", encoding="utf-8") as f:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", f.read())
            self.text_area.edit_modified(False)
        self.draw_map()

    def save_file(self):
        fname = self.selected_filename.get()
        if ".csv" not in fname: return
        path = os.path.join(SAVE_DIR, fname)
        with open(path, "w", encoding="utf-8", newline='') as f:
            f.write(self.text_area.get("1.0", tk.END).strip())
        
        self.root.title(f"SAVED: {fname}")
        self.root.after(1000, lambda: self.root.title("Large-Scale Map Editor"))
        # 保存したらクイックプレビューも更新
        self.quick_draw(fname)

    def draw_map(self):
        self.canvas.delete("all")
        content = self.text_area.get("1.0", tk.END).strip()
        lines = content.split('\n')
        for row, line in enumerate(lines):
            tiles = [t.strip() for t in line.split(',')]
            for col, char in enumerate(tiles):
                if char in TILE_TYPES:
                    config = TILE_TYPES[char]
                    w, h = config["w"] * TILE_SIZE, config["h"] * TILE_SIZE
                    x1, y1 = col * TILE_SIZE, row * TILE_SIZE
                    self.canvas.create_rectangle(x1, y1, x1+w, y1+h, fill=COLORS.get(char, "#000"), outline="#ecf0f1")
                    self.canvas.create_text(x1+w/2, y1+h/2, text=char, fill="white", font=("Arial", 7))

    def on_modify(self, event):
        self.text_area.edit_modified(False)
        self.draw_map()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1400x800")
    app = MapEditor(root)
    root.mainloop()