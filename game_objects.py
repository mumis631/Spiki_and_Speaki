import pygame
import math
from settings import GRAVITY

class PushableBlock:
    def __init__(self, x, y, img_key):
        self.rect = pygame.Rect(x, y, 64, 64)
        self.pos_x = float(x) # float座標を追加
        self.pos_y = float(y)
        self.img_key = img_key
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False

    def update(self, obstacles, platforms, dt):
        # 1フレームあたりの比率を算出
        frame_ratio = dt * 60.0

        # --- 1. X軸の移動と衝突判定 ---
        # 摩擦：以前の「1フレームごとに0.9倍にする」挙動を再現
        # 0.9 の frame_ratio 乗にすることで、FPSが変わっても減速時間を一定にします
        self.vel_x *= math.pow(0.885, frame_ratio)
        
        # 速度が極小になったら停止（以前の 0.1 相当）
        if abs(self.vel_x) < 0.1: 
            self.vel_x = 0

        self.pos_x += self.vel_x * frame_ratio
        self.rect.x = int(self.pos_x)
        
        for target in obstacles:
            t_rect = target['rect'] if isinstance(target, dict) else target.rect
            if self.rect.colliderect(t_rect):
                if self.vel_x > 0: self.rect.right = t_rect.left
                elif self.vel_x < 0: self.rect.left = t_rect.right
                self.vel_x = 0
                self.pos_x = float(self.rect.x)

        # --- 2. Y軸の移動（重力）と衝突判定 ---
        if not self.on_ground:
            # Playerと同じ重力値 (GRAVITY = 0.8) を使用
            self.vel_y += GRAVITY * frame_ratio
        
        # 終端速度：以前の 12.0 相当に制限
        if self.vel_y > 12.0: self.vel_y = 12.0

        self.on_ground = False
        self.pos_y += self.vel_y * frame_ratio
        self.rect.y = int(self.pos_y)
        
        for target in obstacles:
            t_rect = target['rect'] if isinstance(target, dict) else target.rect
            if self.rect.colliderect(t_rect):
                if self.vel_y > 0: # 着地
                    self.rect.bottom = t_rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0: # 頭打ち
                    self.rect.top = t_rect.bottom
                    self.vel_y = 0
                self.pos_y = float(self.rect.y)

        # すり抜け床判定
        for pf in platforms:
            target_rect = pf if isinstance(pf, pygame.Rect) else pf.rect
            if self.vel_y > 0:
                if self.rect.colliderect(target_rect):
                    # 前フレームの足元位置から判定（ここも frame_ratio に合わせる）
                    if (self.rect.bottom - self.vel_y * frame_ratio) <= target_rect.top + 5:
                        self.rect.bottom = target_rect.top
                        self.vel_y = 0
                        self.on_ground = True
                        self.pos_y = float(self.rect.y)