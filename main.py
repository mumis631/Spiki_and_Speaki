# -*- coding: utf-8 -*-
import pygame
import asyncio
import sys
import csv
import json
import os
import base64
import hashlib
import platform
import math
from settings import *
from player import Player
from tiles import MapManager
### debug用
import subprocess # subprocessを使うのが最も軽量で安定します
IS_RELEASE = getattr(sys, 'frozen', False)
DEBUG_MODE = not IS_RELEASE
###
# セーブファイル用の秘密鍵
SECRET_SALT = "my_super_secret_key_123"

# 実行ファイル(exe)またはスクリプトの場所にカレントディレクトリを移動
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    """ リソースファイルへの絶対パスを取得する """
    try:
        # PyInstallerで実行した時の一時フォルダパス
        base_path = sys._MEIPASS
    except Exception:
        # 通常実行時（開発時）のパス
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def load_map_from_csv(filename):
    """
    stagesフォルダ内のCSVファイルを読み込み、2次元配列を返す。
    """
    map_data = []
    # stages フォルダ内のパスを生成
    path = resource_path(os.path.join("stages", filename))
    
    if not os.path.exists(path):
        print(f"【エラー】ファイルが見つかりません: {path}")
        return None
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # セルが空の場合は半角スペース" "に変換。
                # それ以外は、前後の余計な空白を削除（strip）して格納。
                processed_row = [cell.strip() if cell.strip() != "" else " " for cell in row]
                map_data.append(processed_row)
        return map_data
    except Exception as e:
        print(f"【CSV読み込み失敗】: {e}")
        return None
    
class Game:
    ## debug用
    def launch_editor(self):
        if not DEBUG_MODE:
            print("デバッグ機能は無効です。")
            return
        try:
            """別プロセスでエディタを起動する"""
            try:
                # editor.py という名前で保存されていると想定
                # プロセスを切り離して起動するため、ゲームが止まらない
                subprocess.Popen(["python", "editor.py"])
            except Exception as e:
                print(f"エディタの起動に失敗しました: {e}")
        except Exception as e:
            print(f"エディタ起動失敗: {e}")

    def debug_unlock_all_stages(self):
        """全てのチャプターとステージをクリア済みに設定する（既存スコアは維持）"""
        if not DEBUG_MODE:
            return

        chapters = ["grassland", "forest", "cave"]
        stages_per_chapter = 10
        
        # 既存のスコア（辞書）をベースにする
        new_cleared_dict = dict(self.cleared_stages) 
        
        for chapter in chapters:
            for stage_num in range(1, stages_per_chapter + 1):
                stage_id = f"{chapter}_{stage_num:02}"
                
                # まだ記録がないステージのみ、クリア扱い(999回)として追加
                # すでにクリア済みのステージは、自力で出した最小回数をそのまま保持する
                if stage_id not in new_cleared_dict:
                    new_cleared_dict[stage_id] = 999
        
        # 辞書を更新し、セーブを実行
        self.cleared_stages = new_cleared_dict
        self.save_game() 
        print(f"DEBUG: 全 {len(self.cleared_stages)} ステージの開放を完了しました。")
    ###

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512) # 周波数を 44100Hz に固定
        pygame.init()

        # --- フォント読み込み ---
        font_path = resource_path("Fonts/NotoSansJP-Regular.otf")  # フォントファイル名を直接指定
        font_size = 28
        
        # 1. まずカレントディレクトリのファイルを試す
        if os.path.exists(font_path):
            self.font_s = pygame.font.Font(font_path, font_size)
            self.font_l = pygame.font.SysFont(font_path, 48, bold=True)
            print("a")
        else:
            # 2. ファイルがない場合はシステムフォントから「日本語対応」を明示して取得
            # Windows: "msgothic", Mac: "hiraginosansgbw3"
            self.font_s = pygame.font.SysFont("msgothic, hiraginosansgbw3, sans-serif, Arial", font_size)
            self.font_l = pygame.font.SysFont("msgothic, hiraginosansgbw3, sans-serif, Arial", 48, bold=True)

        self.is_touch_device = False

        # ゲーム自体の基本解像度（固定）
        self.BASE_WIDTH = 800
        self.BASE_HEIGHT = 600
        # 2. 描画用のキャンバス（ここにすべてのゲーム画面を描く）
        self.game_canvas = pygame.Surface((self.BASE_WIDTH, self.BASE_HEIGHT))
        # 実際のウィンドウ（ブラウザやスマホの画面に合わせて変動）
        self.screen = pygame.display.set_mode((self.BASE_WIDTH, self.BASE_HEIGHT), pygame.RESIZABLE)

        self.map_mgr = MapManager()
        from player import Player
        self.player = Player(0, 0)
        self.load_assets()
        pygame.display.set_caption("Spiki & Speaki")
        # ウィンドウアイコンの設定
        try:
            # アイコン用の画像（こちらは .png でOK）を読み込む
            icon_img = self.images.get(f"common_candy")
            pygame.display.set_icon(icon_img)
        except Exception as e:
            print(f"Icon load error: {e}")
        self.clock = pygame.time.Clock()
        
        self.cleared_stages = set()  # クリアしたステージIDを保存する
        self.load_game()  # 起動時にロードを実行

        self.scene = "SELECT"
        self.focus_target = "STAGE"  # 初期状態はステージ選択
        self.is_paused = False  # Trueなら設定画面を表示
        self.is_cleared = False
        self.current_tutorial = None # または 0
        # 選択状態の管理
        self.chapters = ["grassland", "forest", "cave"]
        self.current_chapter_idx = 0  # 現在のタブ
        self.select_stage_idx = 0     # 0〜9 (ステージ1〜10)
        self.current_chapter = 1
        self.current_stage = 1

        # 音声設定
        self.load_sounds()
        self.play_bgm()
        pygame.mixer.set_num_channels(16)
        self.audio_initialized = False

        self.vol_bgm = 0.4 # BGM音量管理 (0.0 ～ 1.0)
        self.vol_se = 0.4 # SE音量管理 (0.0 ～ 1.0)
        self.slider_dragging = None # "BGM" か "SE" か
        self.apply_volume() # 初期音量を適用

        self.btn_font = pygame.font.SysFont("Arial", 24, bold=True)

        # チュートリアル表示
        self.tutorial_alpha = 150.0      # 現在の透明度
        self.tutorial_target_alpha = 150.0 # 目標の透明度
        self.last_input_time = 0         # 最後に操作した時間 (ミリ秒)
        self.idle_delay = 500           # 操作を止めてから戻り始めるまでの時間 (2秒)


        # StageLoad関係
        self.player.state = "IDLE"
        self.player.is_big = True
        self.candy_count = 5
        self.player.change_count = 0
        self.player.rect.topleft = (0, 0)
        self.player.pos_x = float(0)
        self.player.pos_y = float(0)
        self.player.vel_y = 0
        self.player.on_ground = True

        # 仮想キー位置初期化
        self.btn_left = pygame.Rect(0, 0, 0, 0)
        self.btn_right = pygame.Rect(0, 0, 0, 0)
        self.btn_up = pygame.Rect(0, 0, 0, 0)
        self.btn_down = pygame.Rect(0, 0, 0, 0)
        self.btn_jump = pygame.Rect(0, 0, 0, 0)
        self.btn_change = pygame.Rect(0, 0, 0, 0)
        self.btn_reload = pygame.Rect(0, 0, 0, 0)
        self.btn_menu = pygame.Rect(0, 0, 0, 0)
        self.btn_esc = pygame.Rect(0, 0, 0, 0)


    # #######################################################################################
    # SOUNDS
    # #######################################################################################
    async def warmup_sounds(self):
        # 1. BGMを開始（これで全体のゲートが開く）
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)

        # 2. 代表的な短い音を1つだけ「無音」で鳴らし、SFXチャネルを起動
        # ※全てをループさせる必要はありません。1つ通ればパスが開通します。
        if 'break' in self.sounds:
            self.sounds['break'].set_volume(0)
            self.sounds['break'].play()
            await asyncio.sleep(0.5)
            self.sounds['break'].stop()

        # 3. 内部フラグを立てて完了
        self.audio_initialized = True
        self.apply_volume()
    
    def play_bgm(self):
        if os.path.exists(resource_path('sounds/bgm.ogg')):
            pygame.mixer.music.load(resource_path('sounds/bgm.ogg'))
            pygame.mixer.music.play(-1) # -1で無限ループ

    def apply_volume(self):
        # BGMの音量を適用
        pygame.mixer.music.set_volume(self.vol_bgm)
        # 全SEの音量を適用
        for s in self.sounds.values():
            s.set_volume(self.vol_se)

    def load_sounds(self):
        self.sounds = {
            'jump_small': pygame.mixer.Sound(resource_path('sounds/jump_small.ogg')),
            'jump_big': pygame.mixer.Sound(resource_path('sounds/jump_big.ogg')),
            'break': pygame.mixer.Sound(resource_path('sounds/break.ogg')),
            'change_small': pygame.mixer.Sound(resource_path('sounds/change_small.ogg')),
            'change_big': pygame.mixer.Sound(resource_path('sounds/change_big.ogg')),
            'clear': pygame.mixer.Sound(resource_path('sounds/clear.ogg')),
            'hit': pygame.mixer.Sound(resource_path('sounds/hit.ogg')) # 頭突き音
        } 

    def load_assets(self):
        self.images = {}
        base_path = resource_path('assets')

        # タイルサイズ定義
        sizes = {
            'floor': (64, 64),
            'wall': (64, 64),
            'brick': (64, 64),
            'goal': (64, 64), 
            'door': (64, 96),
            'platform': (64, 16),
            'player_big': (64, 96),
            'player_small': (64, 64),
            'player_smile': (64, 64),
            'bg_grassland': (800, 600)
        }
        # os.walkでベースパス以下をスキャン
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('.png'):
                    full_name = os.path.splitext(file)[0] # 例: 'grassland_floor'
                    full_path = os.path.join(root, file)
                    folder = os.path.basename(root)
                    if '_' in folder and folder.split('_')[0].isdigit():
                        folder_clean = folder.split('_', 1)[1] # '0_common' -> 'common'
                    else:
                        folder_clean = folder
                    
                    full_path = os.path.join(root, file)
                    # 画像の読み込み
                    try:
                        img = pygame.image.load(full_path).convert_alpha()
                    except Exception as e:
                        print(f"Asset Load Error: {e}") # これがブラウザのコンソールに表示されます

                    # サイズ設定：'grassland_floor' の末尾 'floor' で判定
                    for key_size, size in sizes.items():
                        if full_name.endswith(key_size):
                            img = pygame.transform.scale(img, size)
                            break
                    
                    # 1. そのままの名前で登録 (例: "cave_brick")
                    self.images[full_name] = img
                    
                    # 2. フォルダ名から数字を除去してプレフィックスとして登録
                    folder = os.path.basename(root)
                    if '_' in folder and folder.split('_')[0].isdigit():
                        folder_prefix = folder.split('_', 1)[1] # "2_cave" -> "cave"
                        # ファイル名に既に "cave_" が入っていなければ結合して登録
                        if not full_name.startswith(folder_prefix):
                            self.images[f"{folder_prefix}_{full_name}"] = img
                    
                    # 3. もし "cave_brick" という名前なら、単に "brick" としても引けるようにバックアップ
                    if '_' in full_name:
                        short_name = full_name.split('_')[-1]
                        if short_name not in self.images:
                            self.images[short_name] = img

    def load_stage(self, stage_id):
        # 1. 設定の取得（安全に取得するために .get() を推奨）
        config = MAP_CONFIG.get(stage_id)
        if not config:
            print(f"Error: {stage_id} not found.")
            return

        # 2. CSVファイルからマップリスト（2次元配列）を読み込み
        map_list = load_map_from_csv(config["csv"])
        if not map_list:
            print(f"Error: Could not load CSV for {stage_id}")
            return

        # 3. チャプター・チュートリアル情報の更新
        self.current_chapter = config.get("chapter_id", "common")
        self.current_tutorial = config.get("tutorial", [])
        self.current_stage_id = stage_id
        self.is_cleared = False

        # 4. マップオブジェクトの生成
        self.map_mgr.create_map(map_list)

        # 5. プレイヤーの開始位置決定
        if self.map_mgr.player_start_pos != (0, 0):
            start_x, start_y = self.map_mgr.player_start_pos
        else:
            # CSVに'S'がない場合のフォールバック
            start_x, start_y = config.get("start_pos", (64, 480))
            
        # 6. プレイヤーの状態をリセット（変更前のロジックを継承）
        self.player.state = "IDLE"
        self.player.is_big = True
        self.candy_count = 5
        self.player.change_count = 0
        self.player.rect.topleft = (start_x, start_y)
        self.player.pos_x = float(start_x)
        self.player.pos_y = float(start_y)
        self.player.vel_y = 0      # 落下速度リセット
        self.player.on_ground = True # 接地状態から開始

    def save_game(self):
        try:
            # 1. cleared_stagesは既に辞書なので、そのまま保存
            save_dict = {
                "cleared": self.cleared_stages,  # {"grassland_01": 2, ...} の形式
                "version": "1.1" # バージョンを上げておくと管理しやすい
            }
            json_str = json.dumps(save_dict)
            
            # 2. 改ざん防止用ハッシュ（既存ロジック）
            signature = hashlib.sha256((json_str + SECRET_SALT).encode()).hexdigest()
            
            # 3. Base64難読化（既存ロジック）
            final_data = {
                "payload": json_str,
                "sig": signature
            }
            encoded_data = base64.b64encode(json.dumps(final_data).encode()).decode()

            with open("save_data.dat", "w") as f:
                f.write(encoded_data)
        except Exception as e:
            print(f"セーブ失敗: {e}")

    def load_game(self):
        if not os.path.exists("save_data.dat"):
            self.cleared_stages = {} # セットではなく辞書で初期化
            return

        try:
            with open("save_data.dat", "r") as f:
                encoded_data = f.read()

            decoded_json = json.loads(base64.b64decode(encoded_data).decode())
            payload = decoded_json["payload"]
            stored_sig = decoded_json["sig"]

            expected_sig = hashlib.sha256((payload + SECRET_SALT).encode()).hexdigest()

            if stored_sig != expected_sig:
                print("警告: 改ざん検知")
                self.cleared_stages = {}
                return

            data = json.loads(payload)
            
            # 重要：JSONからロードすると辞書として戻ってくる
            self.cleared_stages = data["cleared"] 
            
            # 互換性維持：もし古いセーブデータ（リスト形式）だった場合の変換
            if isinstance(self.cleared_stages, list):
                # リストなら回数不明なので、とりあえず目標回数+1などの適当な数値を入れる
                self.cleared_stages = {sid: 999 for sid in self.cleared_stages}
                
            print(f"ロード成功: {self.cleared_stages}")

        except Exception as e:
            print(f"ロード失敗: {e}")
            self.cleared_stages = {}

    def is_stage_unlocked(self, chapter_idx, stage_idx):
        """
        chapter_idx: 0(grassland), 1(forest), 2(cave)
        stage_idx: 0~9 (1~10ステージ)
        """
        # 最初のチャプターの最初のステージは常に開放
        if chapter_idx == 0 and stage_idx == 0:
            return True

        # 1. 同じチャプター内の前のステージがクリアされているかチェック
        if stage_idx > 0:
            prev_stage_id = f"{self.chapters[chapter_idx]}_{stage_idx:02}"
            return prev_stage_id in self.cleared_stages

        # 2. チャプターの最初のステージ(idx 0)の場合、前のチャプターの最後のステージ(idx 9)をチェック
        if stage_idx == 0 and chapter_idx > 0:
            prev_chap_last_stage_id = f"{self.chapters[chapter_idx-1]}_10"
            return prev_chap_last_stage_id in self.cleared_stages

        return False

    def pause(self):
        # 半透明のオーバーレイを表示するなど
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.game_canvas.blit(overlay, (0, 0))
        # 「PAUSE」の文字を表示する処理など

    def perform_jump(self):
        """ジャンプの実行（dt対応・秒速ベース）"""
        # コヨーテタイム（空中でもジャンプを受け付ける猶予時間）を 0.1秒 に設定
        COYOTE_TIME = 0.1 

        if self.player.air_timer < COYOTE_TIME:
            if self.player.is_big:
                # 修正：秒速ベースの速度
                self.player.vel_y = -11.0 
                if 'jump_big' in self.sounds: self.sounds['jump_big'].play()
            else:
                # 小さい時はより高く飛ぶ設定
                self.player.vel_y = -16.5 
                if 'jump_small' in self.sounds: self.sounds['jump_small'].play()
            
            self.player.on_ground = False
            # 空中タイマーを即座に最大にして、多段ジャンプを防止
            self.player.air_timer = COYOTE_TIME

    # #######################################################################################
    # UPDATE
    # #######################################################################################
    def update(self, h_inputs, t_inputs, dt):
        """物理演算・ギミック更新（inputsを受け取る形に完全統合）"""
        if self.scene == "SELECT" or self.is_paused or self.is_cleared:
            return
        
        # 1. 入力の統合（キーボード/スマホの区別をここで吸収）
        # custom_keys は Player.update が期待する形式に合わせる
        custom_keys = {
            pygame.K_LEFT:  h_inputs["left"],
            pygame.K_RIGHT: h_inputs["right"],
            pygame.K_DOWN:  h_inputs["down"]
        }
        
        old_top = self.player.rect.top

        # --- 衝突対象の動的生成 ---
        active_toggle_tiles = self.map_mgr.large_only_tiles if self.player.is_big else self.map_mgr.small_only_tiles
        
        # ドア（鍵がない間は壁）
        player_door_obstacles = []
        if self.map_mgr.has_keys == 0:
            player_door_obstacles = [{'rect': d['rect']} for d in self.map_mgr.doors]
        
        collision_targets = (self.map_mgr.tiles + self.map_mgr.bricks + 
                             player_door_obstacles + active_toggle_tiles)

        # 動くブロックを床として追加
        for pb in self.map_mgr.pushable_blocks:
            if self.player.rect.bottom <= pb.rect.top + 5:
                collision_targets.append({'rect': pb.rect})
                
        # 2. プレイヤー物理更新
        self.player.update(custom_keys, collision_targets, self.map_mgr.platforms, dt)

        # 3. 頭突き判定 (triggerではなく現在の速度と位置で判定)
        if self.player.vel_y <= 0 and not self.player.on_ground:
            self._handle_headbutt(old_top)

        # 4. ギミック更新 (鍵・ドア)
        self._update_gizmos(dt)

        # 5. 押せるブロックの更新
        self._update_pushable_blocks(active_toggle_tiles, dt)

        # 6. 状態判定 (落下・ゴール)
        self._check_game_status()

    def _update_gizmos(self, dt):
        # --- 鍵の取得判定 ---
        for key_data in self.map_mgr.keys[:]:
            if self.player.rect.colliderect(key_data['rect']):
                self.map_mgr.keys.remove(key_data)
                self.map_mgr.has_keys += 1
                if 'pickup' in self.sounds: 
                    self.sounds['pickup'].play()
            # key_data['anim_timer'] = key_data.get('anim_timer', 0) + 5.0 * dt
            # key_data['rect'].y = key_data['base_y'] + math.sin(key_data['anim_timer']) * 5

        # --- ドアの解錠判定 ---
        if self.map_mgr.has_keys > 0:
            for d_data in self.map_mgr.doors[:]:
                # d_data も辞書なので、['rect'] を指定
                if self.player.rect.colliderect(d_data['rect']):
                    self.map_mgr.doors.remove(d_data)
                    self.map_mgr.has_keys -= 1
                    if 'door_open' in self.sounds: self.sounds['door_open'].play()

    def _check_game_status(self):
        for g in self.map_mgr.goal_tiles:
            if self.player.rect.colliderect(g):
                if not self.is_cleared: # 初回クリア時のみ実行
                    self.is_cleared = True
                    self.clear_start_ticks = pygame.time.get_ticks() # 演出用の時刻記録
                    
                    # --- 進捗管理とベストスコア記録 ---
                    if self.current_stage_id != "SELECT":
                        # 現在の変身回数を取得（playerクラスに変身回数カウント変数が実装されている前提：例 self.player.change_count）
                        current_count = getattr(self.player, 'change_count', 0)
                        
                        # 記録更新判定：初クリア、または今回の回数がベストより少ない場合
                        if self.current_stage_id not in self.cleared_stages or \
                           current_count < self.cleared_stages[self.current_stage_id]:
                            
                            self.cleared_stages[self.current_stage_id] = current_count
                            self.save_game()  # 更新があった時のみセーブ
                            print(f"New Record!: {self.current_stage_id} - {current_count} times")
                        else:
                            # 記録更新はしなくても、クリア済みフラグ維持のためにセーブが必要ならここに追加
                            self.save_game()

                    # プレイヤーの状態更新
                    self.player.state = "CLEAR"
                    self.player.is_big = False
                    self.player.rect.height = 64
                    self.player.rect.bottom = g.bottom # 地面に合わせる
                    self.sounds['clear'].play() # クリア音

    def _handle_headbutt(self, old_top):
        """頭突きロジックの集約"""
        check_rect = pygame.Rect(0, 0, 24, max(20, old_top - self.player.rect.top + 10))
        check_rect.centerx = self.player.rect.centerx
        check_rect.top = self.player.rect.top - 5

        # レンガ
        for b in self.map_mgr.bricks[:]:
            if check_rect.colliderect(b['rect']):
                if self.player.rect.top < b['rect'].bottom + 10:
                    if self.player.is_big:
                        self.sounds['break'].play()
                        self.map_mgr.bricks.remove(b)
                    else:
                        self.sounds['hit'].play()
                    self._rebound_player(b['rect'].bottom)
                    return
    
    def _rebound_player(self, new_top):
        self.player.rect.top = new_top
        self.player.pos_y = float(self.player.rect.y)
        self.player.vel_y = 3.0 
        self.player.air_timer = 10

    def _update_pushable_blocks(self, active_toggle_tiles, dt):
        """ブロックの物理と押し出し"""
        block_door_obstacles = [{'rect': d['rect']} for d in self.map_mgr.doors]

        for i, pb in enumerate(self.map_mgr.pushable_blocks):
            other_blocks = [{'rect': ob.rect} for j, ob in enumerate(self.map_mgr.pushable_blocks) if i != j]
            obstacles = (self.map_mgr.tiles + self.map_mgr.bricks + 
                         block_door_obstacles + other_blocks + active_toggle_tiles)
            
            #1. プレイヤーによる押し出し判定（先に速度を決める）
            if self.player.rect.colliderect(pb.rect):
                if self.player.is_big:
                    if self.player.rect.centerx < pb.rect.centerx:
                        pb.vel_x = 5.0 # PUSH_SPEED
                    else:
                        pb.vel_x = -5.0
                
                # 押し戻し処理（物理更新前に行うことで、プレイヤーをブロックに密着させる）
                if self.player.rect.centerx < pb.rect.centerx:
                    self.player.rect.right = pb.rect.left
                else:
                    self.player.rect.left = pb.rect.right
                self.player.pos_x = float(self.player.rect.x - 4)

            # 2. ブロック自身の物理更新（ここで vel_x に基づいて実際に動く）
            pb.update(obstacles, self.map_mgr.platforms, dt)

    # #######################################################################################
    # DRAW
    # #######################################################################################
    def draw_select_menu(self):
        # --- 背景描画 ---
        # 現在のチャプター名を取得 (例: "grassland", "forest" ...)
        current_chap_name = self.chapters[self.current_chapter_idx]
        
        # 背景画像キーを生成 (例: "bg_select_grassland")
        bg_key = f"{current_chap_name}_select_bg"
        
        # 画像を取得（チャプター専用画像 -> 共通セレクト背景 -> 共通プレイ背景 の順で探す）
        bg_img = self.images.get(bg_key, 
                 self.images.get("stage_select_bg", 
                 self.images.get("common_bg")))

        if bg_img:
            # 画面サイズにフィットさせて描画
            self.game_canvas.blit(bg_img, (0, 0))
        else:
            # 画像が一切ない場合のフォールバック（チャプターごとのイメージカラー）
            fallback_colors = {
                "grassland": (40, 80, 40), # 暗い緑
                "forest": (30, 60, 50),    # 深緑
                "cave": (50, 40, 30),      # 茶
            }
            bg_color = fallback_colors.get(current_chap_name, (50, 50, 80))
            self.game_canvas.fill(bg_color)

        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 40))
        self.game_canvas.blit(overlay, (0, 0))
        
        # --- タブ（チャプター）の描画 ---
        tab_x, tab_y = 100, 130
        tab_w = 160  # 幅
        for i, name in enumerate(self.chapters):
            is_chap_unlocked = self.is_stage_unlocked(i, 0)
            rect = pygame.Rect(tab_x + i*(tab_w + 20), tab_y, tab_w, 40)
            
            # --- 1. 発光(Glow)演出：チャプター選択時 ---
            if i == self.current_chapter_idx and self.focus_target == "CHAPTER":
                for r in range(1, 8):
                    glow_alpha = int(100 * (0.5 ** r))
                    if glow_alpha < 5: break
                    glow_rect = rect.inflate(r*2, r*2)
                    glow_color = (255, 255, 0, glow_alpha)
                    s = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(s, glow_color, s.get_rect(), width=2, border_radius=10+r)
                    self.game_canvas.blit(s, glow_rect.topleft)

            # --- 2. 半透明パネルの設定 ---
            tab_panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if i == self.current_chapter_idx:
                # 現在のチャプター（操作中かどうかで明るさを変える）
                alpha = 200 if self.focus_target == "CHAPTER" else 140
                bg_color = (230, 230, 100, alpha)
                border_color = (255, 255, 200, 255)
            elif is_chap_unlocked:
                # 解放済み
                bg_color = (255, 255, 255, 120)
                border_color = (255, 255, 255, 150)
            else:
                # ロック中
                bg_color = (255, 255, 255, 80)
                border_color = (255, 255, 255, 80)

            # --- 3. パネル本体の描画 ---
            pygame.draw.rect(tab_panel, bg_color, tab_panel.get_rect(), border_radius=10)
            pygame.draw.rect(tab_panel, border_color, tab_panel.get_rect(), 2, border_radius=10)
            self.game_canvas.blit(tab_panel, rect)

            # --- 4. チャプター名の描画 ---
            name_color = (255, 255, 255) if is_chap_unlocked else (150, 150, 150)
            txt = self.font_s.render(name.upper(), True, name_color)
            txt_rect = txt.get_rect(center=rect.center)
            
            # テキストシャドウ
            txt_shadow = self.font_s.render(name.upper(), True, (0, 0, 0))
            txt_shadow.set_alpha(100)
            self.game_canvas.blit(txt_shadow, (txt_rect.x + 2, txt_rect.y + 2))
            self.game_canvas.blit(txt, txt_rect)

            # --- 5. ロック演出 ---
            if not is_chap_unlocked:
                lock_base = self.font_s.render("LOCK", True, (255, 255, 255))
                lock_rot = pygame.transform.rotate(lock_base, 20) # タブは細いので20度くらい
                l_rect = lock_rot.get_rect(center=rect.center)
                
                l_shadow = pygame.transform.rotate(self.font_s.render("LOCK", True, (0, 0, 0)), 20)
                self.game_canvas.blit(l_shadow, (l_rect.x + 1, l_rect.y + 1))
                self.game_canvas.blit(lock_rot, l_rect)

        # --- ステージアイコン(01-10)の描画 ---
        start_x, start_y = 100, 220
        for i in range(10):
            unlocked = self.is_stage_unlocked(self.current_chapter_idx, i)
            row, col = i // 5, i % 5
            rect = pygame.Rect(start_x + col*130, start_y + row*130, 80, 80)
            
            # --- 1. 半透明パネル用のSurfaceを作成 ---
            # アイコンと同じサイズの透明なSurfaceを用意
            panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            
            # 色と透明度の設定 (A: 0=透明, 255=不透明)
            if not unlocked:
                # ロック中：かなり薄い白
                bg_color = (255, 255, 255, 80)
                border_color = (255, 255, 255, 80)
            elif i == self.select_stage_idx and self.focus_target == "STAGE":
                # 選択中：明るい黄色（半透明）
                bg_color = (230, 230, 100, 180)
                border_color = (230, 230, 200, 255)
                
                # 発光(Glow)演出を本体の周りに描画
                for r in range(1, 10): # 10段階くらい重ねると滑らか
                    # 外に行くほど透明度を急激に下げる（指数的な減衰が綺麗です）
                    glow_alpha = int(120 * (0.6 ** r)) 
                    if glow_alpha < 5: break
                    # inflateで少しずつ外側に広げたRectを作成
                    glow_rect = rect.inflate(r*2, r*2)
                    glow_color = (255, 255, 0, glow_alpha)
                    s = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(s, glow_color, s.get_rect(), width=2, border_radius=15+r)
                    self.game_canvas.blit(s, glow_rect.topleft)
            else:
                # 開放済み：明るい白（半透明）
                bg_color = (255, 255, 255, 120)
                border_color = (255, 255, 255, 180)

            # --- 2. パネルの描画 (panel_surfに対して) ---
            panel_rect = panel_surf.get_rect()
            # 中塗り
            pygame.draw.rect(panel_surf, bg_color, panel_rect, border_radius=15)
            # 枠線
            pygame.draw.rect(panel_surf, border_color, panel_rect, 2, border_radius=15)
            
            # パネルをメインキャンバスに合成
            self.game_canvas.blit(panel_surf, rect)

            # --- 4. 文字描画 ---
            num_str = f"{i+1:02}"
            # 文字色も明るく調整
            num_color = (255, 255, 255) if unlocked else (180, 180, 180)
            
            # シャドウ（透明感を引き立てるために少し薄く）
            num_shadow = self.font_l.render(num_str, True, (0, 0, 0))
            num_shadow.set_alpha(150)
            self.game_canvas.blit(num_shadow, (rect.centerx - num_shadow.get_width()//2 + 2, rect.centery - num_shadow.get_height()//2 + 2))
            
            # 本体
            num_txt = self.font_l.render(num_str, True, num_color)
            self.game_canvas.blit(num_txt, (rect.centerx - num_txt.get_width()//2, rect.centery - num_txt.get_height()//2))

            # --- 5. ロック演出 ---
            if not unlocked:
                # LOCK文字を斜めに。白を強調。
                lock_base = self.font_s.render("LOCK", True, (255, 255, 255))
                lock_rot = pygame.transform.rotate(lock_base, 30)
                lock_rect = lock_rot.get_rect(center=rect.center)
                
                # 下に黒い影を置いて視認性確保
                lock_shadow = pygame.transform.rotate(self.font_s.render("LOCK", True, (0, 0, 0)), 30)
                self.game_canvas.blit(lock_shadow, (lock_rect.x + 2, lock_rect.y + 2))
                self.game_canvas.blit(lock_rot, lock_rect)
            
            # --- 6. CLEAR表示（条件分岐演出） ---
            if unlocked:
                stage_id = f"{self.chapters[self.current_chapter_idx]}_{i+1:02}"
                if stage_id in self.cleared_stages:
                    import math
                    best_count = self.cleared_stages.get(stage_id, 999)
                    target_count = MAP_CONFIG.get(stage_id, {}).get("target_changes", 0)
                    
                    is_perfect = best_count <= target_count
                    pulse = (math.sin(pygame.time.get_ticks() / 200) + 1) / 2

                    # 1. 条件によって「テキスト」と「色」を決定
                    if is_perfect:
                        text_str = "CLEAR!"
                        glow_base_color = (100, 255, 100) # 鮮やかな緑
                        text_color = (int(100 + 155 * pulse), 255, int(100 + 155 * pulse))
                    else:
                        text_str = "CLEAR"
                        glow_base_color = (100, 255, 100) # 通常クリアも緑で光らせる
                        text_color = (int(100 + 155 * pulse), 255, int(100 + 155 * pulse))

                    # 2. 背後の後光（共通演出）
                    glow_size = int(5 + pulse * 5)
                    for r in range(1, glow_size):
                        alpha = int((80 - r * 10) * pulse)
                        if alpha <= 0: break
                        
                        glow_color = (*glow_base_color, alpha)
                        temp_rect = pygame.Rect(0, 0, 70 + r*2, 20 + r*2)
                        temp_rect.center = (rect.centerx, rect.bottom + 18)
                        
                        s = pygame.Surface(temp_rect.size, pygame.SRCALPHA)
                        pygame.draw.ellipse(s, glow_color, s.get_rect())
                        self.game_canvas.blit(s, temp_rect.topleft)

                    # 3. テキスト描画
                    check_txt = self.font_s.render(text_str, True, text_color)
                    check_rect = check_txt.get_rect(centerx=rect.centerx, top=rect.bottom + 5)
                    
                    # シャドウ
                    check_shadow = self.font_s.render(text_str, True, (0, 0, 0))
                    self.game_canvas.blit(check_shadow, (check_rect.x + 1, check_rect.y + 1))
                    self.game_canvas.blit(check_txt, check_rect)
                    
    def draw_candy_ui(self):
        candy_img = self.images.get("common_candy")
        if candy_img:
            # キャンディのサイズを調整（例: 32x32）
            candy_small = pygame.transform.scale(candy_img, (32, 32))
            for i in range(self.candy_count):
                # 20px間隔で左上に並べる
                self.game_canvas.blit(candy_small, (70 + i * 40, 20))

    def draw_key_ui(self):
        if self.map_mgr.has_keys:
            key_img = self.images.get("common_key", self.images.get("key"))
            if key_img:
                # UI用に少し小さくリサイズ
                small_key = pygame.transform.scale(key_img, (32, 32))
                self.game_canvas.blit(small_key, (300, 20)) # キャンディUIの右あたり
                
                val_txt = self.font_s.render(f"x {self.map_mgr.has_keys}", True, (255, 255, 255))
                self.game_canvas.blit(val_txt, (340, 22))

    def draw_pause_menu(self):
        # 画面全体を暗くする
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.game_canvas.blit(overlay, (0, 0))

        # --- 設定項目（既存） ---
        title = self.font_l.render("SETTINGS", True, (255, 255, 255))
        self.game_canvas.blit(title, (SCREEN_WIDTH//2 - 100, 150))

        # スライダー描画ロジック（既存）
        self.slider_x = 300
        self.slider_y = 300
        self.slider_w = 200
        labels = [("BGM", self.vol_bgm, self.slider_y), (" SE", self.vol_se, self.slider_y + 80)]
        for label, vol, y in labels:
            txt = self.font_s.render(f"{label}: {int(vol*100)}%", True, (255, 255, 255))
            self.game_canvas.blit(txt, (self.slider_x - 130, y - 5))
            pygame.draw.rect(self.game_canvas, (100, 100, 100), (self.slider_x, y+5, self.slider_w, 10), border_radius=5)
            pygame.draw.rect(self.game_canvas, (0, 255, 100), (self.slider_x, y+5, int(self.slider_w * vol), 10), border_radius=5)
            pygame.draw.circle(self.game_canvas, (255, 255, 255), (self.slider_x + int(self.slider_w * vol), y+10), 8)

        # --- クレジット表示（画面下部） ---
        # 1. 表示内容の定義
        credits = [
            "ｽﾋﾟｷ＆スピッキー",
            "Created by: mumis"
        ]
        # 右下からのマージン
        margin_right = 20
        margin_bottom = 15
        
        for i, text in enumerate(reversed(credits)): # 下から順に描画
            # 1. テキスト生成
            raw_txt = self.font_s.render(text, True, (150, 150, 150))
            
            # 2. サイズを60%程度に縮小（font_sが大きすぎる場合の対策）
            orig_w, orig_h = raw_txt.get_size()
            scale = 0.6
            credit_txt = pygame.transform.smoothscale(raw_txt, (int(orig_w * scale), int(orig_h * scale)))
            
            # 3. 透明度をさらに下げる（120/255）
            credit_txt.set_alpha(180)
            
            # 4. 配置計算（右下基準）
            pos_x = SCREEN_WIDTH - credit_txt.get_width() - margin_right
            pos_y = SCREEN_HEIGHT - margin_bottom - (i * 15 + credit_txt.get_height())
            
            # 描画（シャドウなし。文字が小さいため、シャドウがあると逆に潰れて見えるため）
            self.game_canvas.blit(credit_txt, (pos_x, pos_y))

    def draw_virtual_keys(self, surface, screen_w, screen_h):
        # --- 1. サイズと余白の設定 ---
        margin = 20
        bw, bh = 90, 90    # 重なりを防ぐため、100から少しだけ絞り90pxに調整
        sw, sh = 60, 60
        gap = 15           # ボタン同士の隙間

        # --- 2. ボタンの配置定義 ---
        # 左側（移動）：重なりを防ぐため「下」を中央、「左」「右」をその両脇に配置（逆T字）
        # ※画面の一番下に「下ボタン」を配置
        self.btn_down  = pygame.Rect(margin + bw + gap, screen_h - bh - margin, bw, bh)
        self.btn_left  = pygame.Rect(margin, screen_h - bh - margin, bw, bh)
        self.btn_right = pygame.Rect(margin + (bw + gap) * 2, screen_h - bh - margin, bw, bh)
        
        # 「上」は必要なシーンでのみ使用（配置は左と右の間、一段上）
        self.btn_up    = pygame.Rect(margin + bw + gap, screen_h - (bh * 2) - margin - gap, bw, bh)

        # 右側（アクション）：Jumpを右端、Changeをその隣に配置（横並び）
        self.btn_jump   = pygame.Rect(screen_w - bw - margin, screen_h - bh - margin, bw, bh)
        self.btn_change = pygame.Rect(screen_w - (bw * 2) - margin - gap, screen_h - bh - margin, bw, bh)

        # システム系（画面上部）
        self.btn_menu   = pygame.Rect(margin, margin, sw, sh)
        self.btn_esc    = pygame.Rect((screen_w - sw) / 2, margin, sw, sh)
        self.btn_reload = pygame.Rect(screen_w - sw - margin, margin, sw, sh)

        # --- 3. 表示ロジック ---
        if self.is_paused:
            buttons = [(self.btn_esc, "ESC")]
        else:
            if self.scene == "SELECT":
                buttons = [
                    (self.btn_left, "←"), (self.btn_right, "→"),
                    (self.btn_up, "↑"), (self.btn_down, "↓"),
                    (self.btn_jump, "OK"), (self.btn_esc, "ESC")
                ]
            elif self.scene == "PLAYING":
                # プレイ中：↑は除外、移動は←↓→の並びに
                jump_label = "OK" if self.is_cleared else "Jump"
                buttons = [
                    (self.btn_left, "←"), (self.btn_down, "↓"), (self.btn_right, "→"),
                    (self.btn_jump, jump_label),
                    (self.btn_reload, "R"), (self.btn_menu, "M"),
                    (self.btn_esc, "ESC")
                ]
                # クリアしていない時だけ「Change」ボタンをリストに加える
                if not self.is_cleared:
                    buttons.append((self.btn_change, "Spiki"))
            else:
                return

        # --- 4. 描画処理 ---
        for btn, label in buttons:
            s = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
            # 枠と背景の透明度を少し上げて、ゲーム画面を見やすく調整
            pygame.draw.rect(s, (255, 255, 255, 40), s.get_rect(), border_radius=15)
            
            text_surf = self.btn_font.render(label, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(btn.width // 2, btn.height // 2))
            s.blit(text_surf, text_rect)
            
            surface.blit(s, btn.topleft)
            pygame.draw.rect(surface, (255, 255, 255, 80), btn, 2, border_radius=15)

    def draw_play_scene(self, dt):
        # chapterは 'grassland' や 'cave' が入る想定
        chapter = self.current_chapter
            
        # 1. 背景描画
        bg_key = f"{chapter}_bg"
        bg_img = self.images.get(bg_key, self.images.get("common_bg"))
        if bg_img: 
            self.game_canvas.blit(bg_img, (0, 0))
        else: 
            self.game_canvas.fill((50, 50, 80))

        # 2. タイル描画（チャプターごとに切り替え）
        all_draw_targets = [
            {"list": self.map_mgr.draw_tiles, "is_brick": False}, 
            {"list": self.map_mgr.bricks, "is_brick": True},
            {"list": self.map_mgr.pushable_blocks, "is_brick": False},
            {"list": self.map_mgr.keys, "is_brick": True},
            {"list": self.map_mgr.doors, "is_brick": True},
            {"list": self.map_mgr.large_only_tiles, "type": "L", "is_brick": False},
            {"list": self.map_mgr.small_only_tiles, "type": "R", "is_brick": False}
        ]

        for target in all_draw_targets:
            # 透明度のフラグ判定（ターゲットごとに1回だけ実施）
            tile_type = target.get("type")
            is_faded = False
            if tile_type == "L" and not self.player.is_big: is_faded = True
            elif tile_type == "R" and self.player.is_big: is_faded = True

            for item in target["list"]:
                # データ型を特定して rect と img_key を抽出
                if isinstance(item, dict):
                    img_key = item.get("img_key", target.get("img_key"))
                    rect = item["rect"] if "rect" in item else pygame.Rect(*item["pos"], 64, 64)
                elif hasattr(item, "img_key"):
                    img_key = item.img_key
                    rect = item.rect
                else:
                    img_key = target.get("img_key")
                    rect = item

                # 画像検索
                img = self.images.get(f"{chapter}_{img_key}", 
                                    self.images.get(f"common_{img_key}", 
                                    self.images.get(img_key)))
                
                if img:
                    pos = (rect.x + OFFSET_X, rect.y + OFFSET_Y)
                    
                    # ブラウザ最適化：copy()を避け、必要な時だけset_alphaを適用
                    # ※頻繁に切り替わる場合は、あらかじめ半透明画像を作っておくのが理想
                    if is_faded:
                        img.set_alpha(80)
                    else:
                        img.set_alpha(255)
                        
                    self.game_canvas.blit(img, pos)

        # 3. チュートリアル
        if self.current_tutorial:
            current_a = int(self.tutorial_alpha)
            text_a = min(255, current_a + 50) 
            
            rect_width = 620
            line_spacing = 10
            padding = 20
            h = (padding * 2) + (len(self.current_tutorial) * (20 + line_spacing))
            
            # オーバーレイSurfaceの生成
            # ※本来は一度作ったSurfaceをクラス変数に保持し、リサイズ時のみ作り直すのが最速
            overlay = pygame.Surface((rect_width, h), pygame.SRCALPHA)
            overlay.fill((20, 20, 20, current_a)) 
            pygame.draw.rect(overlay, (200, 200, 150, current_a), (0, 0, rect_width, h), 2)
            
            pos_x, pos_y = (800 - rect_width) // 2, 100
            self.game_canvas.blit(overlay, (pos_x, pos_y))
            
            # テキスト描画
            for i, line in enumerate(self.current_tutorial):
                txt = self.font_s.render(line, True, (255, 215, 0))
                txt.set_alpha(text_a)
                self.game_canvas.blit(txt, (pos_x + padding, pos_y + padding + i * (20 + line_spacing)))
        
        # 4. プレイヤーとUIの描画
        self.player.draw(self.game_canvas, self.images, dt)
        self.draw_candy_ui()
        self.draw_key_ui()
                
    def draw(self, dt):
        self.game_canvas.fill((135, 206, 235)) # 背景色など

        if self.scene == "SELECT":
            self.draw_select_menu()
        else:
            self.draw_play_scene(dt)  # プレイ画面の描画（背景、タイル、キャラ）

            if self.is_cleared:
                # --- ステージクリアの豪華演出 ---
                import math

                # 1. クリアした瞬間の時間を記録（一度だけ）
                if not hasattr(self, 'clear_start_ticks') or self.clear_start_ticks == 0:
                    self.clear_start_ticks = pygame.time.get_ticks()

                # 2. 経過時間の計算（秒単位、リセットなしの連続値）
                elapsed_time = (pygame.time.get_ticks() - self.clear_start_ticks) / 1000.0

                # 3. 背後の後光（強烈な発光）
                glow_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                # 登場時のインパクト演出：0.5秒かけて1.5倍から1.0倍に収束しつつ、その後パルス
                entrance_impact = max(0, 1.0 * math.exp(-elapsed_time * 5)) # 急激に減衰する値
                pulse_scale = 1.0 + entrance_impact + 0.1 * math.sin(elapsed_time * 8)

                for r in range(1, 15):
                    alpha = int(100 * (0.7 ** r))
                    # 経過時間によるフェードイン
                    alpha = int(alpha * min(1.0, elapsed_time * 2))
                    
                    glow_surf = pygame.Surface((300 + r*20, 100 + r*10), pygame.SRCALPHA)
                    glow_color = (255, 200 + r*3, 50, alpha)
                    pygame.draw.ellipse(glow_surf, glow_color, glow_surf.get_rect())
                    
                    # 滑らかなスケーリング
                    s_w = int(glow_surf.get_width() * pulse_scale)
                    s_h = int(glow_surf.get_height() * pulse_scale)
                    scaled_glow = pygame.transform.smoothscale(glow_surf, (s_w, s_h))
                    self.game_canvas.blit(scaled_glow, scaled_glow.get_rect(center=glow_center))

                # 4. メインテキスト "STAGE CLEAR!"
                # テキストも後光と同期してパルス
                text_scale = pulse_scale
                
                # 本体
                base_txt = self.font_l.render("STAGE CLEAR!", True, (255, 255, 100))
                w, h = base_txt.get_size()
                scaled_txt = pygame.transform.smoothscale(base_txt, (int(w * text_scale), int(h * text_scale)))
                
                # シャドウ（本体と同じスケールで描画）
                shadow_txt = self.font_l.render("STAGE CLEAR!", True, (50, 20, 0))
                shadow_txt = pygame.transform.smoothscale(shadow_txt, (int(w * text_scale), int(h * text_scale)))
                
                txt_rect = scaled_txt.get_rect(center=glow_center)
                # シャドウを少しずらして描画
                self.game_canvas.blit(shadow_txt, (txt_rect.x + 4, txt_rect.y + 4))
                self.game_canvas.blit(scaled_txt, txt_rect)
            
        if self.is_paused:
            self.draw_pause_menu()  # プレイ画面の上に設定を重ねる

        # --- 比率を維持したスケーリング ---
        # 現在のウィンドウサイズを取得
        window_w, window_h = pygame.display.get_surface().get_size()
        
        # 拡大倍率を計算（幅と高さの小さい方に合わせる）
        scale = min(window_w / self.BASE_WIDTH, window_h / self.BASE_HEIGHT)
        new_size = (int(self.BASE_WIDTH * scale), int(self.BASE_HEIGHT * scale))
        
        # キャンバスをスケーリング
        scaled_canvas = pygame.transform.smoothscale(self.game_canvas, new_size)
        
        # 中央に配置するためのオフセット計算
        self.offset_x = (window_w - new_size[0]) // 2
        self.offset_y = (window_h - new_size[1]) // 2
        self.current_scale = scale # 座標計算用に保存
        
        # 実画面をクリアして貼り付け
        self.screen.fill((20, 20, 20)) # 背景（黒帯部分の色）
        self.screen.blit(scaled_canvas, (self.offset_x, self.offset_y))
        
        # 仮想キーを「実画面」に直接描画
        if self.is_touch_device:
            self.draw_virtual_keys(self.screen, window_w, window_h)

        pygame.display.flip()

    def handle_transformation(self):
        # アイテムがあるかチェック
        if self.candy_count > 0:
            old_bottom = self.player.rect.bottom # 変更前の足元の位置を保持
            if not self.player.is_big:
                # --- 大きくなる時の予測判定 ---
                keys = pygame.key.get_pressed()
                dx = 5 * (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT])
                preview_rect = self.player.rect.copy()
                preview_rect.height = 96
                preview_rect.x += dx 
                preview_rect.bottom = old_bottom
                
                # 判定対象：通常の壁 + レンガ + 「大きくなった時に実体化するLタイル」
                obstacles = self.map_mgr.tiles + self.map_mgr.bricks + self.map_mgr.doors + self.map_mgr.large_only_tiles
                block_rects = [{'rect': pb.rect} for pb in self.map_mgr.pushable_blocks]
                all_collision_targets = obstacles + block_rects
                
                can_grow = True
                for obs in all_collision_targets:
                    if preview_rect.colliderect(obs['rect']):
                        can_grow = False
                        break
                
                if can_grow:
                    self.player.is_big = True
                    self.player.rect.height = 96
                    self.player.rect.bottom = preview_rect.bottom
                    self.player.pos_y = float(self.player.rect.y)
                    self.sounds['change_big'].play()
                    self.candy_count -= 1
                    self.player.change_count += 1

                    # すり抜け床の上にいた場合の補正 床の上に合わせる
                    for p in self.map_mgr.platforms:
                        if self.player.rect.colliderect(p):
                            if abs(self.player.rect.bottom - p.top) < 10:
                                self.player.rect.bottom = p.top
                                self.player.pos_y = float(self.player.rect.y)
                                self.player.vel_y = 0
                                self.player.on_ground = True
            else:
                # --- 小さくなる時の予測判定 ---
                preview_rect = self.player.rect.copy()
                preview_rect.height = 64
                preview_rect.bottom = old_bottom
                
                # 判定対象：通常の壁 + レンガ + 「小さくなった時に実体化するRタイル」
                obstacles = self.map_mgr.tiles + self.map_mgr.bricks + self.map_mgr.small_only_tiles
                
                can_shrink = True
                for obs in obstacles:
                    if preview_rect.colliderect(obs['rect']):
                        can_shrink = False
                        break

                if can_shrink:
                    self.player.is_big = False
                    self.player.rect.height = 64
                    self.player.rect.bottom = old_bottom
                    self.player.pos_y = float(self.player.rect.y) # 明示的に座標更新
                    self.sounds['change_small'].play()
                    self.candy_count -= 1
                    self.player.change_count += 1
                    # (以下すり抜け床補正)
                    for p in self.map_mgr.platforms:
                        if self.player.rect.right > p.left and self.player.rect.left < p.right:
                            if abs(self.player.rect.bottom - p.top) < 10:
                                self.player.rect.bottom = p.top
                                self.player.pos_y = float(self.player.rect.y)
                                self.player.vel_y = 0
                                self.player.on_ground = True
        else:
            # アイテムがない時の処理
            pass

    def get_logical_mouse_pos(self):
        surface = pygame.display.get_surface()
        if not surface:
            return (0, 0)

        # 現在の実画面サイズとスケールを再計算
        window_w, window_h = surface.get_size()
        
        # window_w や window_h が 0 の場合、または計算不能な場合の安全策
        if window_w <= 0 or window_h <= 0:
            return (0, 0)

        scale = min(window_w / self.BASE_WIDTH, window_h / self.BASE_HEIGHT)
        
        # scale が 0 にならないようにチェック
        if scale <= 0:
            return (0, 0)
        
        offset_x = (window_w - (self.BASE_WIDTH * scale)) // 2
        offset_y = (window_h - (self.BASE_HEIGHT * scale)) // 2
        
        raw_x, raw_y = pygame.mouse.get_pos()
        
        # 論理座標（800x600）に変換
        logical_x = (raw_x - offset_x) / scale
        logical_y = (raw_y - offset_y) / scale
        
        return (logical_x, logical_y)

    # #######################################################################################
    # INPUT SYSTEM
    # #######################################################################################
    def _create_empty_input_state(self):
        return {
            "hold": {"left": False, "right": False, "down": False},
            "trigger": {"left": False, "right": False, "up": False, "down": False, 
                        "enter": False, "jump": False, "change": False}
        }

    def _update_touch_input(self, active_fingers, input_state, raw_mouse_pos):
        h = input_state["hold"]
        
        # 1. キーボードのホールド状態（これは常に有効）
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  h["left"] = True
        if keys[pygame.K_RIGHT]: h["right"] = True
        if keys[pygame.K_DOWN]:  h["down"] = True
        if keys[pygame.K_SPACE]: h["jump"] = True
        if keys[pygame.K_c]:     h["change"] = True

        # 2. タッチによるホールド判定
        # 素早い切り替えで active_fingers が一瞬空になっても、
        # 判定が途切れないようループを確実に回す
        for f_pos in list(active_fingers.values()):
            # 移動ボタン：ここが True になり続けることが重要
            if self.btn_left.collidepoint(f_pos):   h["left"] = True
            if self.btn_right.collidepoint(f_pos):  h["right"] = True
            if self.btn_down.collidepoint(f_pos):   h["down"] = True
            
            # アクションボタン：ジャンプしながら移動しやすくする
            if self.btn_jump.collidepoint(f_pos):   h["jump"] = True
            if self.btn_change.collidepoint(f_pos): h["change"] = True

        # 3. マウス判定
        if pygame.mouse.get_pressed()[0]:
            m_pos = raw_mouse_pos
            if self.btn_left.collidepoint(m_pos):   h["left"] = True
            if self.btn_right.collidepoint(m_pos):  h["right"] = True
            if self.btn_jump.collidepoint(m_pos):   h["jump"] = True

    def _handle_events(self, e, active_fingers, window_size, input_state):
        window_w, window_h = window_size
        t = input_state["trigger"]
        h = input_state["hold"] # holdも参照に追加
        
        if e.type in (pygame.FINGERDOWN, pygame.FINGERMOTION):
            self.is_touch_device = True
            f_pos = (e.x * window_w, e.y * window_h)
            active_fingers[e.finger_id] = f_pos 
            
            if e.type == pygame.FINGERDOWN:
                if not self.audio_initialized:
                    # 非同期で最小限の準備を実行
                    asyncio.create_task(self.warmup_sounds())
                
                if self.btn_esc.collidepoint(f_pos):
                    self.is_paused = not self.is_paused
                
                if not self.is_paused:
                    # --- 瞬間(trigger)と継続(hold)を同時にセット ---
                    # これにより素早い指の入れ替えでも1フレームの空白を作らない
                    if self.btn_left.collidepoint(f_pos):
                        t["left"] = h["left"] = True
                    if self.btn_right.collidepoint(f_pos):
                        t["right"] = h["right"] = True
                    if self.btn_up.collidepoint(f_pos):
                        t["up"] = True
                    if self.btn_down.collidepoint(f_pos):
                        t["down"] = h["down"] = True

                    if self.btn_jump.collidepoint(f_pos):
                        if self.is_cleared:
                            # クリア時は「OK」ボタンとして機能
                            self.scene = "SELECT"
                            self.is_cleared = False
                        else:
                            # 通常時はジャンプ
                            t["jump"] = t["enter"] = h["jump"] = True
                    
                    if self.btn_change.collidepoint(f_pos):
                        t["change"] = h["change"] = True
                    
                    # システムボタン
                    if self.btn_reload.collidepoint(f_pos): 
                        self.load_stage(self.current_stage_id)
                    if self.btn_menu.collidepoint(f_pos):
                        self.scene = "SELECT"
                        self.is_cleared = False

        elif e.type == pygame.FINGERUP:
            # 指が離れたときのみ削除
            active_fingers.pop(e.finger_id, None)

        # --- キーボード処理（略） ---
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.is_paused = not self.is_paused
                self.slider_dragging = None
            elif not self.is_paused:
                if e.key == pygame.K_LEFT:   t["left"] = True
                if e.key == pygame.K_RIGHT:  t["right"] = True
                if e.key == pygame.K_UP:     t["up"] = True
                if e.key == pygame.K_DOWN:   t["down"] = True
                if e.key == pygame.K_RETURN: t["enter"] = True
                if e.key == pygame.K_SPACE:  t["jump"] = True  # ジャンプフラグ
                if e.key == pygame.K_c:      t["change"] = True # 切り替えフラグ
                if e.key == pygame.K_r:      self.load_stage(self.current_stage_id)
                if e.key == pygame.K_m:
                    self.scene = "SELECT"
                    self.is_cleared = False
                
                # Debug Keys
                if DEBUG_MODE:
                    if e.key == pygame.K_F1:  self.launch_editor()
                    if DEBUG_MODE and e.key == pygame.K_F11:
                            if self.current_stage_id != "SELECT":
                                self.is_cleared = True
                                # 演出用の開始時刻を記録（豪華演出のガクつき防止）
                                self.clear_start_ticks = pygame.time.get_ticks() 
                                
                                # --- 辞書型のデータ更新 ---
                                # すでに記録がある場合は維持、ない場合は「クリア済み」として999をセット
                                if self.current_stage_id not in self.cleared_stages:
                                    self.cleared_stages[self.current_stage_id] = 999
                                
                                self.save_game()  # ステージ進捗を保存
                                
                                # プレイヤーをクリア状態にする（動けなくする）
                                self.player.state = "CLEAR"
                    if e.key == pygame.K_F12: self.debug_unlock_all_stages()

        # --- マウス処理 ---
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if self.is_paused:
                self._check_slider_collision(self.get_logical_mouse_pos())
        elif e.type == pygame.MOUSEBUTTONUP:
            self.slider_dragging = None

    def _handle_touch_trigger(self, f_x, f_y, window_size, trigger):
        """タッチした瞬間の判定（triggerに集約）"""
        if self.btn_esc.collidepoint((f_x, f_y)):
            self.is_paused = not self.is_paused
            return

        if not self.is_paused:
            # 共通移動系
            if self.btn_left.collidepoint((f_x, f_y)):   trigger["left"] = True
            if self.btn_right.collidepoint((f_x, f_y)):  trigger["right"] = True
            if self.btn_up.collidepoint((f_x, f_y)):     trigger["up"] = True
            if self.btn_down.collidepoint((f_x, f_y)):   trigger["down"] = True
            
            # ジャンプ / 決定
            if self.btn_jump.collidepoint((f_x, f_y)):
                trigger["enter"] = True # セレクト画面用
                trigger["jump"] = True  # プレイ画面用
            
            # 切り替え
            if self.btn_change.collidepoint((f_x, f_y)):
                trigger["change"] = True
            
            # 即時実行
            if self.btn_reload.collidepoint((f_x, f_y)): self.load_stage(self.current_stage_id)
            if self.btn_menu.collidepoint((f_x, f_y)):
                self.scene = "SELECT"
                self.is_cleared = False

    def _check_slider_collision(self, pos):
        """スライダーとの当たり判定"""
        mx, my = pos
        if self.slider_x <= mx <= self.slider_x + self.slider_w:
            if self.slider_y - 20 <= my <= self.slider_y + 40:
                self.slider_dragging = "BGM"
            elif (self.slider_y + 80) - 20 <= my <= (self.slider_y + 80) + 40:
                self.slider_dragging = "SE"

    # #######################################################################################
    # SCENE UPDATE
    # #######################################################################################
    def _update_select_scene(self, inputs, dt):
        trigger = inputs["trigger"]
        
        if self.focus_target == "CHAPTER":
            new_idx = self.current_chapter_idx
            if trigger["left"]:  new_idx = (self.current_chapter_idx - 1) % len(self.chapters)
            if trigger["right"]: new_idx = (self.current_chapter_idx + 1) % len(self.chapters)
            
            if self.is_stage_unlocked(new_idx, 0):
                self.current_chapter_idx = new_idx
            
            if trigger["down"] or trigger["enter"]:
                self.focus_target = "STAGE"
                self.select_stage_idx = 0

        elif self.focus_target == "STAGE":
            new_idx = self.select_stage_idx
            if trigger["up"]:
                if new_idx < 5: self.focus_target = "CHAPTER"
                else: new_idx -= 5
            elif trigger["down"]:
                if new_idx < 5: new_idx += 5
            elif trigger["left"]:  new_idx = (new_idx - 1) % 10
            elif trigger["right"]: new_idx = (new_idx + 1) % 10

            if self.is_stage_unlocked(self.current_chapter_idx, new_idx):
                self.select_stage_idx = new_idx

            if trigger["enter"]:
                chapter = self.chapters[self.current_chapter_idx]
                self.current_stage_id = f"{chapter}_{self.select_stage_idx + 1:02}"
                self.scene = "PLAYING"
                self.load_stage(self.current_stage_id)

    def _update_playing_scene(self, inputs, dt):
        """プレイ中の更新処理（継続と瞬間を使い分け）"""
        if self.is_cleared: return
        
        # 物理演算 (継続入力を使用)
        self.update(inputs["hold"], inputs["trigger"], dt)
        
        # アクション (瞬間入力を使用)
        if inputs["trigger"]["jump"]:   self.perform_jump()
        if inputs["trigger"]["change"]: self.handle_transformation()

        # チュートリアルのアルファ制御
        self._update_tutorial_alpha(inputs, dt)
    
    def _update_tutorial_alpha(self, inputs, dt):
        """チュートリアル表示の濃度（透明度）を操作状況に応じて更新"""
        if not self.current_tutorial:
            return

        # 1. 操作が行われているかチェック
        h, t = inputs["hold"], inputs["trigger"]
        is_active = any([
            h["left"], h["right"], h["down"],
            t["left"], t["right"], t["up"], t["down"],
            t["jump"], t["change"], t["enter"]
        ])

        # pygame.time.get_ticks() は ms 単位なので、dt（秒）との整合性に注意
        # ここでは時間の経過判定にのみ使用
        current_time = pygame.time.get_ticks()
        
        # 2. 目標とする透明度の決定
        if is_active:
            self.last_input_time = current_time
            self.tutorial_target_alpha = 40.0 
        else:
            if current_time - self.last_input_time > self.idle_delay:
                self.tutorial_target_alpha = 150.0
                
        # 3. アルファ値を目標値に向けて徐々に変化させる
        diff = self.tutorial_target_alpha - self.tutorial_alpha
        
        # フェード速度の係数（0.1に近いほど高速）
        fade_factor = 1.0 - math.pow(0.05, dt) 
        
        self.tutorial_alpha += diff * fade_factor

        # 誤差を丸める
        if abs(self.tutorial_alpha - self.tutorial_target_alpha) < 0.5:
            self.tutorial_alpha = self.tutorial_target_alpha

    def _update_pause_logic(self, logical_mouse_pos, dt):
        """ポーズ中（スライダー等）のロジック"""
        if self.slider_dragging:
            old_val = self.vol_bgm if self.slider_dragging == "BGM" else self.vol_se
            
            val = (logical_mouse_pos[0] - self.slider_x) / self.slider_w
            val = max(0.0, min(1.0, val))
            
            if self.slider_dragging == "BGM": self.vol_bgm = val
            else: self.vol_se = val
            
            # 値が実際に変化した時だけ音量を適用する
            if val != old_val:
                self.apply_volume()

    # #######################################################################################
    # MAIN LOOP
    # #######################################################################################
    async def run(self):
        active_fingers = {}
        clock = pygame.time.Clock()

        while True:
            # デルタタイム（経過時間）の取得
            dt = clock.tick() / 1000.0 # 制限をかけず、かかった時間だけを計測
            if dt > 0.1: dt = 1/60.0 # 画面切り替え時などの極端なラグでの突き抜け防止

            window_size = pygame.display.get_surface().get_size()
            raw_mouse_pos = pygame.mouse.get_pos()
            
            # 1. 入力リセット
            input_state = self._create_empty_input_state()

            # 2. イベント処理（キーボードのtriggerと指の最新座標を収集）
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return
                self._handle_events(event, active_fingers, window_size, input_state)
            
            # 3. 入力の統合（ホールド判定）
            self._update_touch_input(active_fingers, input_state, raw_mouse_pos)

            # シーン振り分け
            if self.is_paused:
                self._update_pause_logic(self.get_logical_mouse_pos(), dt)
            elif self.scene == "SELECT":
                self._update_select_scene(input_state, dt)
            elif self.scene == "PLAYING":
                self._update_playing_scene(input_state, dt)

            self.draw(dt)
            await asyncio.sleep(0)

async def main():
    
    game = Game()
    await game.run()  # runメソッドがasyncであることを確認

if __name__ == "__main__":
    asyncio.run(main())