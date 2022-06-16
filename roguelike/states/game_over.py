from typing import (
    ClassVar,
    TYPE_CHECKING
)

from roguelike.engine import (
    assets,
    text,
    tween
)
from roguelike.states import ui

if TYPE_CHECKING:
    from roguelike.engine.sprite import Sprite
    from roguelike.engine.text import CharBank

class GameOverState(ui.PoppableMenu):
    header_scale: ClassVar[float]
    button_scale: ClassVar[float]
    text_height: ClassVar[float] = 520
    button_height: ClassVar[float] = 150
    button_width: ClassVar[float] = 375
    button_margin: ClassVar[float] = 30
    button_padding: ClassVar[float] = 30
    screen_width: ClassVar[float] = 1440
    active_button_bg: ClassVar['Sprite']
    inactive_button_bg: ClassVar['Sprite']
    font: ClassVar['CharBank']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_button_bg = assets.Sprites.instance.button_active
        self.inactive_button_bg = assets.Sprites.instance.button_inactive
        self.callbacks_on_push.append(GameOverState.rise_up)
        self.obscures = True
        self.widget.reset_scr = [0, 0, 0, 1]
        self.mainholder = self.widget.widget
        self.mainholder.buffer_display = 0
        self.mainholder.scroll = False
        self.mainholder.spacing = self.text_height + self.button_padding
        gameover_label = ui.Label(
            text="Game Over", text_rect=[
                0., 0., self.screen_width, self.text_height],
            font=self.font,
            alignment=text.CENTER_CENTER)
        self.selection_menu = ui.WidgetHolder(
            horizontal=True, buffer_display=0, scroll=False,
            spacing=self.button_width + self.button_padding)
        text_rect = (
            self.button_padding, self.button_padding,
            self.button_width - self.button_padding * 2,
            self.button_height - self.button_padding * 2)
        self.restart_button = ui.build_button_widget(
            "Restart", list(text_rect), self.header_scale,
            (self.button_padding, self.button_padding),
            command = lambda _: self.restart_game(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=self.active_button_bg,
            inactive_bg_sprite=self.inactive_button_bg)
        self.quit_button = ui.build_button_widget(
            "Quit", list(text_rect), self.header_scale,
            (self.button_padding, self.button_padding),
            command = lambda _: self.quit_game(),
            alignment=text.CENTER_CENTER,
            active_bg_sprite=self.active_button_bg,
            inactive_bg_sprite=self.inactive_button_bg)
        self.selection_menu.widgets += [self.restart_button, self.quit_button]
        self.selection_menu.base_offset.x =\
            self.screen_width / 2 - self.button_width - self.button_padding
        self.mainholder.widgets += (gameover_label, self.selection_menu)
        
    def rise_up(self):
        self.mainholder.base_offset.y = 1000
        anim = tween.Animation([
            (0., tween.Tween(self.mainholder.base_offset, 'y', 1000, 0, 1))
        ])
        anim.attach(self)
        self.begin_animation(anim)
    
    def restart_game(self):
        # print("I don't think we can restart until I have some kind of map generation")
        self.manager.state_stack[-2].respawn()
        self.manager.pop_state()
    
    def quit_game(self):
        self.manager.state_stack.clear()
    
    @classmethod
    def init_resources(cls) -> None:
        cls.font = ui.default_font
        w = cls.button_width - cls.button_padding * 2
        h = cls.button_height - cls.button_padding * 2
        cls.header_scale = cls.font.scale_to_bound(
            "Game Over", (w, h))
        cls.button_scale = cls.font.scale_to_bound(
            "Restart", (w * .5, h * .5))
