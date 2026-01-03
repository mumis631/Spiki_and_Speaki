import pygame
from settings import GRID_SIZE, TILE_TYPES

class MapManager:
    def __init__(self):
        self.tiles = []
        self.draw_tiles = []
        self.goal_tiles = []
        self.doors = []
        self.platforms = []
        self.bricks = []
        self.pushable_blocks = []
        self.player_start_pos = (0, 0) # プレイヤーの初期位置格納用
        self.keys = []      # 鍵のRectリスト
        self.doors = []     # ドアのRectリスト
        self.has_keys = 0   # プレイヤーの所持鍵数
        self.large_only_tiles = [] # 'L' の Rect リスト
        self.small_only_tiles = [] # 'R' の Rect リスト

    def create_map(self, map_data):
        self.tiles.clear()
        self.draw_tiles.clear()
        self.goal_tiles.clear()
        self.doors.clear()
        self.platforms.clear()
        self.bricks.clear()
        self.pushable_blocks.clear()
        self.player_start_pos = (0, 0)
        self.keys.clear()
        self.doors.clear()
        self.has_keys = 0
        self.large_only_tiles.clear()
        self.small_only_tiles.clear()
        
        # --- 画面外への侵入を防ぐ「見えない壁」を設置 ---
        # ステージ全体のサイズを計算（タイル数 × グリッドサイズ）
        map_width = len(map_data[0]) * GRID_SIZE
        map_height = len(map_data) * GRID_SIZE
        thickness = 100  # 壁の厚み（プレイヤーが突き抜けない十分な太さ）

        invisible_walls = [
            # 左端の壁
            pygame.Rect(-thickness, 0, thickness, map_height),
            # 右端の壁
            pygame.Rect(map_width, 0, thickness, map_height),
            # 上端の壁（必要に応じて）
            pygame.Rect(0, -thickness, map_width, thickness)
        ]
        
        for wall_rect in invisible_walls:
            # tilesに追加するが、draw_tilesには追加しない（＝判定はあるが見えない）
            self.tiles.append({'rect': wall_rect})
        
        for r_idx, row in enumerate(map_data):
            for c_idx, cell in enumerate(row):
                # 1. cellが数値の0や空文字の場合は完全に無視（エラー防止）
                if cell == 0 or cell == " " or cell == "":
                    continue

                # 2. TILE_TYPESにキーが存在するかチェック
                if cell in TILE_TYPES:
                    cfg = TILE_TYPES[cell]
                    x, y = c_idx * GRID_SIZE, r_idx * GRID_SIZE

                    rect = pygame.Rect(x, y, cfg["w"]*GRID_SIZE, cfg["h"]*GRID_SIZE)
                    img_key = cfg["img"]

                    # プレイヤー開始地点の判定
                    if cell == 'S':
                        self.player_start_pos = (x, y)
                        continue # 'S'自体は壁でも床でもないのでここで終了
                    
                    # --- 種類別の振り分け ---
                    
                    # 破壊可能ブロック
                    if cell == 'B' or cell == 4:
                        self.bricks.append({'rect': rect, 'img_key': img_key})
                    
                    # ゴール
                    elif cell == 'G' or cell == 9:
                        self.goal_tiles.append(rect)
                        self.draw_tiles.append({"img_key": img_key, "pos": (x, y)})
                        
                    # すり抜け床
                    elif cell == 'P' or cell == 3:
                        self.platforms.append(rect)
                        self.draw_tiles.append({"img_key": img_key, "pos": (x, y)})
                        
                    # 押せるブロック
                    elif cell == 'M' or cell == 5:
                        from game_objects import PushableBlock
                        self.pushable_blocks.append(PushableBlock(x, y, img_key))
                    
                    # 鍵 (Key) 
                    elif cell == 'K':
                        self.keys.append({'rect': rect, 'img_key': img_key})
                    
                    # ドア (Door)
                    elif cell == 'D':
                        self.doors.append({'rect': rect, 'img_key': img_key})
                    
                    # 赤ブロック
                    elif cell == 'L':
                        # 判定用リストに入れつつ、描画用にも追加
                        self.large_only_tiles.append({'rect': rect, "img_key": img_key})
                    
                    # 青ブロック
                    elif cell == 'R':
                        # 判定用リストに入れつつ、描画用にも追加
                        self.small_only_tiles.append({'rect': rect, "img_key": img_key})

                    # 通常の壁・床 ('F', 'W', 1, 2 など)
                    else:
                        self.tiles.append({'rect': rect})
                        self.draw_tiles.append({"img_key": img_key, "pos": (x, y)})