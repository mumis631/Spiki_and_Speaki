import pygame

GRID_SIZE = 32
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8  # もしくは現在お使いの重力の値
OFFSET_X = -GRID_SIZE // 2
OFFSET_Y = -GRID_SIZE // 2

TILE_TYPES = {
    'S': {"img": None, "w": 2, "h": 2},            # 開始位置
    'F': {"img": "floor", "w": 2, "h": 2},         # Floor (床)
    'W': {"img": "wall",  "w": 2, "h": 2},         # Wall (壁)
    'P': {"img": "platform", "w": 2, "h": 1},      # Platform (すり抜け床)
    'B': {"img": "brick", "w": 2, "h": 2},         # Brick (破壊可能ブロック)
    'M': {"img": "pushablebrock", "w": 2, "h": 2}, # Move (移動可能ブロック)
    'G': {"img": "goal",  "w": 2, "h": 2},         # Goal (ゴール)
    'K': {"img": "key", "w": 2, "h": 2},    # 鍵 (Key)
    'D': {"img": "door", "w": 2, "h": 3},   # ドア (Door)
    'L': {"img": "toggle_large", "w": 2, "h": 1},  # 大(Large)の時だけ実体化
    'R': {"img": "toggle_small", "w": 2, "h": 1},  # 小(Regular/Small)の時だけ実体化
}

MAP_CONFIG = {
    # Grassland Chapter (01-10)
    "grassland_01": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_01.csv",
        "target_changes": 0,
        "tutorial": ["← →: Move", "M: Menu  R: Restart", "かぼちゃに触れるとステージクリア！"]
    },
    "grassland_02": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_02.csv", 
        "target_changes": 1,
        "tutorial": ["C: Change Supiki", "ｽﾋﾟｷのほうが小さいよ。", "キャンディがなくなると変身できなくなるよ。"]
    },
    "grassland_03": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_03.csv", 
        "target_changes": 1,
        "tutorial": ["SPACE: Jump  DOWN: Drop", "ｽﾋﾟｷのほうが高く跳べるよ。"]
    },
    "grassland_04": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_04.csv", 
        "target_changes": 2,
        "tutorial": ["スピッキーは岩を動かせるよ。"]
    },
    "grassland_05": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_05.csv", 
        "target_changes": 3,
        "tutorial": ["スピッキーはひび割れたブロックを壊せるよ。"]
    },
    "grassland_06": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_06.csv", 
        "target_changes": 0,
    },
    "grassland_07": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_07.csv", 
        "target_changes": 5,
    },
    "grassland_08": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_08.csv", 
        "target_changes": 5,
    },
    "grassland_09": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_09.csv", 
        "target_changes": 2,
    },
    "grassland_10": {
        "chapter_id": "grassland", 
        "bg_key": "bg_grassland", 
        "csv": "grassland_10.csv",  
        "target_changes": 5,
    },
    
    # Forest Chapter (01-10)
    "forest_01": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_01.csv",
        "target_changes": 1,
        "tutorial": ["鍵を持っているとドアを開けられるよ。"]
    },
    "forest_02": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_02.csv",
        "target_changes": 2,
    },
    "forest_03": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_03.csv",
        "target_changes": 1,
    },
    "forest_04": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_04.csv",
        "target_changes": 5,
    },
    "forest_05": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_05.csv",
        "target_changes": 5,
    },
    "forest_06": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_06.csv",
        "target_changes": 5,
    },
    "forest_07": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_07.csv",
        "target_changes": 3,
    },
    "forest_08": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_08.csv",
        "target_changes": 5,
    },
    "forest_09": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_09.csv",
        "target_changes": 5,
    },
    "forest_10": {
        "chapter_id": "forest", 
        "bg_key": "bg_forest", 
        "csv": "forest_10.csv",
        "target_changes": 3,
    },
    
    # Cave Chapter (01-10)
    "cave_01": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_01.csv",
        "target_changes": 3,
        "tutorial": ["青ブロックはスピッキーの時だけ現れるよ。", "赤ブロックはｽﾋﾟｷの時だけ現れるよ。"]
    },
    "cave_02": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_02.csv",
        "target_changes": 1,
    },
    "cave_03": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_03.csv",
        "target_changes": 3,
    },
    "cave_04": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_04.csv",
        "target_changes": 2,
    },
    "cave_05": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_05.csv",
        "target_changes": 2,
        "tutorial": ["エレベーターバグでブロックを運ぼう。","ぶっ飛んだらごめんね。"]
    },
    "cave_06": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_06.csv",
        "target_changes": 3,
        "tutorial": ["足場から離れても一瞬だけ空中でジャンプができるよ。","※ここからはシビアな操作が要求されます。"]
    },
    "cave_07": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_07.csv",
        "target_changes": 3,
    },
    "cave_08": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_08.csv",
        "target_changes": 5,
    },
    "cave_09": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_09.csv",
        "target_changes": 5,
    },
    "cave_10": {
        "chapter_id": "cave", 
        "bg_key": "bg_cave", 
        "csv": "cave_10.csv",
        "target_changes": 5,
    },
}