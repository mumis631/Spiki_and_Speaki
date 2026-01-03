import pygame
import math # サイン波計算用
from settings import SCREEN_HEIGHT, OFFSET_X, OFFSET_Y, GRAVITY

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 64, 96)
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.vel_y = 0
        self.is_big = True
        self.facing_right = True
        self.target_right = True
        self.flip_progress = 1.0
        self.is_flipping = False
        self.state = "NORMAL" # 状態管理用
        self.dance_timer = 0
        self.flip_progress = 1.0 # 向き反転のアニメーション用
        self.on_ground = False # 接地フラグを追加
        self.air_timer = 0.0
        self.change_count = 0

    def update(self, keys, tiles, platforms, dt):
        if self.state == "CLEAR":
            # クリア後は物理演算（重力以外）を停止、または速度を0にする
            self.vel_y += GRAVITY * dt * 60 # 60fpsベースの定数なら調整が必要
            self.pos_y += self.vel_y * dt
            self.rect.y = int(self.pos_y)
            
            for t in tiles:
                if self.rect.colliderect(t['rect']):
                    if self.vel_y > 0:
                        self.rect.bottom = t['rect'].top
                        self.pos_y = float(self.rect.y)
                        self.vel_y = 0
            return
        
        # 状態に応じたRectサイズの更新（これがないと小さい時にバグる）
        expected_h = 92 if self.is_big else 60
        # Rectのサイズを先に決める（判定用）
        temp_rect = pygame.Rect(int(self.pos_x + 4), int(self.pos_y), 56, expected_h)

        # dtを60倍して「今の1フレームが、旧60FPSの何フレーム分か」を算出
        frame_ratio = dt * 60.0 

        # 向きアニメーション
        target_flip = 1.0 if self.facing_right else -1.0
        if self.flip_progress != target_flip:
            flip_speed = 12.0 * dt # 約0.08秒で反転完了
            if self.flip_progress < target_flip:
                self.flip_progress = min(target_flip, self.flip_progress + flip_speed)
            else:
                self.flip_progress = max(target_flip, self.flip_progress - flip_speed)

        # --- 1. 左右移動の判定 ---
        # 以前の1フレームあたりの移動量 (例: 5.0) を基準にする
        dx_per_frame = 5.0 
        
        # dtを60倍した比率を掛けることで、以前の5px移動と同じ感覚にする
        # frame_ratio = dt * 60.0  <- 垂直判定のところで計算済みのものを使用
        dx_val = 0
        if keys.get(pygame.K_LEFT, False): 
            dx_val = -dx_per_frame * frame_ratio
            self.facing_right = False
        elif keys.get(pygame.K_RIGHT, False): 
            dx_val = dx_per_frame * frame_ratio
            self.facing_right = True

        # --- 横方向の移動と衝突判定 ---
        if dx_val != 0:
            self.pos_x += dx_val
            temp_rect.x = int(self.pos_x + 4)
            for obs in tiles:
                if temp_rect.colliderect(obs['rect']):
                    if dx_val > 0: 
                        temp_rect.right = obs['rect'].left
                    elif dx_val < 0: 
                        temp_rect.left = obs['rect'].right
                    
                    # 【重要】衝突後は float座標を Rectの結果に必ず同期させる
                    self.pos_x = float(temp_rect.x - 4)
        
        # 2.垂直方向（ジャンプ・落下）の判定
        self.pos_y += self.vel_y * frame_ratio

        # この1フレーム間の重力による加速分を計算
        # 物理公式の 0.5 * a * t^2 に基づき、移動距離に加速分を加える
        delta_v = GRAVITY * frame_ratio
        self.pos_y += 0.5 * delta_v * frame_ratio

        # 次のフレームのために速度を更新する
        self.vel_y += delta_v
        temp_rect.y = int(self.pos_y)
        
        if self.on_ground:
            self.air_timer = 0
        else:
            self.air_timer += dt # 秒で加算
        self.on_ground = False 

        for obs in tiles:
            if temp_rect.colliderect(obs['rect']):
                if self.vel_y > 0: # 落下中：着地
                    temp_rect.bottom = obs['rect'].top
                    self.vel_y = 0
                    self.on_ground = True
                    self.pos_y = float(temp_rect.y)
                elif self.vel_y < 0: # 上昇中：頭打ち
                    temp_rect.top = obs['rect'].bottom
                    self.vel_y = 0
                    self.pos_y = float(temp_rect.y)

        # 2-2. すり抜け床（プラットフォーム）
        if not keys.get(pygame.K_DOWN, False) and self.vel_y >= 0:
            # 今回の移動で通過したであろう距離（前回の足元位置を推測）
            prev_bottom = temp_rect.bottom - (self.vel_y * frame_ratio)
            
            for p in platforms:
                if temp_rect.colliderect(p):
                    # 1. 移動前(prev_bottom)が床の上端(p.top)より上にあった
                    # 2. 現在の足元(temp_rect.bottom)が床の上端より下にある
                    if prev_bottom <= p.top + 2: # +2は浮動小数点誤差の遊び
                        temp_rect.bottom = p.top
                        self.pos_y = float(temp_rect.y)
                        self.vel_y = 0
                        self.on_ground = True
                        break # 一つ床に乗ったら判定終了

        # --- 5. 結果の反映 ---
        # --- Hitboxの結果を実際の表示用Rectに反映させる ---
        self.rect.size = temp_rect.size
        self.rect.topleft = temp_rect.topleft

    def draw(self, screen, images, dt):
        base_w, base_h = self.rect.width, self.rect.height
        img_key = 'player_big' if self.is_big else 'player_small'
        
        if self.state == "CLEAR":
            img_key = 'player_smile'
            self.dance_timer += 6.0 * dt # 1秒間に約1サイクル
            
            # クリア時のダンス
            stretch_y = 1.0 + math.sin(self.dance_timer * 2.0 + 1) * 0.5
            shear_x = math.cos(self.dance_timer * 1.0) * 30 # 左右への最大ズレ幅
            
            curr_h = int(base_h * stretch_y)
            p_img = images.get(img_key)
            if p_img:
                # 向きに合わせて反転したあと、現在の伸縮サイズにリサイズ
                p_img = pygame.transform.flip(p_img, not self.facing_right, False)
                p_img = pygame.transform.scale(p_img, (base_w, curr_h))
                
                # 足元を軸に平行四辺形変形（スライス描画）
                for i in range(curr_h):
                    # 上にいくほど大きくずらす (足元 i=curr_h-1 でズレ0)
                    offset_x = shear_x * (1 - i / curr_h)
                    
                    # 1ピクセル分の横細のスライスを取得
                    line_rect = pygame.Rect(0, i, base_w, 1)
                    
                    # 描画位置：足元の中心を軸に計算
                    draw_x = (self.rect.centerx - base_w // 2) + OFFSET_X + offset_x
                    draw_y = (self.rect.bottom + OFFSET_Y - curr_h) + i
                    
                    screen.blit(p_img, (draw_x, draw_y), line_rect)
                return # スライス描画したのでここで終了

        # --- 通常時の描画 (NORMAL) ---
        curr_w = max(1, int(base_w * abs(self.flip_progress)))
        p_x = (self.rect.centerx - curr_w // 2) + OFFSET_X
        p_y = self.rect.y + OFFSET_Y
        p_img = images.get(img_key)
        if p_img:
            curr_w = max(1, int(base_w * abs(self.flip_progress)))
            f = pygame.transform.flip(p_img, not self.facing_right, False)
            s = pygame.transform.scale(f, (curr_w, base_h))
            # 常に自身のrectの中心を軸に描画することで震えを防ぐ
            draw_x = self.rect.centerx - (curr_w // 2) + OFFSET_X
            draw_y = self.rect.y + OFFSET_Y
            screen.blit(s, (draw_x, draw_y))
        else:
            pygame.draw.rect(screen, (0, 120, 255), (self.rect.x + OFFSET_X, self.rect.y + OFFSET_Y, self.rect.width, base_h))