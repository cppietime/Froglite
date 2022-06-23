import logging
import threading
from typing import (
    TYPE_CHECKING
)

from roguelike import settings
from roguelike.engine import (
    assets,
    text
)
from roguelike.states import (
    game_over,
    ui
)
from roguelike.world import (
    dungeon,
    world_gen
)

if TYPE_CHECKING:
    from roguelike.engine.sprite import Sprite
    from roguelike.engine.text import CharBank

class WorldSelect(ui.PoppableMenu):
    button_h: float = 200
    button_w: float = 400
    button_text_margin_x: float = 20
    button_text_margin_y: float = 20
    button_padding: float = 40
    header_hang: float = 50
    scroll_threshold: int = 3
    active_button_bg: 'Sprite'
    inactive_button_bg: 'Sprite'
    font: 'CharBank'
    
    def __init__(self):
        super().__init__()
        self.widget.reset_scr = [0, 0, 0, 1]
        self.mainholder = self.widget.widget
        self.mainholder.spacing = 1440 / 3
        self.mainholder.base_offset.x = 1440 / 3 - self.button_w / 2
        self.mainholder.buffer_display = 0
        self.mainholder.scroll = False
        self.mainholder.horizontal = True
        
        self.sideholder = ui.WidgetHolder(
            spacing=self.button_h + self.button_padding,
            buffer_display=0,
            scroll=False)
        self.mainholder.widgets.append(self.sideholder)
        
        self.statscreen = ui.Label(
            text='You should not see this', text_rect=[0, 0, 1440 / 3, 1080],
            font=self.font)
        self.mainholder.widgets.append(self.statscreen)
        
        self.holder = ui.WidgetHolder(
            spacing=self.button_h + self.button_padding)
        self.sideholder.widgets.append(ui.Label(
            text="Select world",
            text_rect=[-self.header_hang, 0,
                       self.button_w + self.header_hang * 2, self.button_h],
            font=self.font,
            alignment=text.CENTER_CENTER))
        self.sideholder.widgets.append(self.holder)
        
        self.world_keys = list(assets.persists['unlocked'].keys())
        numb = len(self.world_keys)
        for key, value in assets.persists['unlocked'].items():
            if not value:
                continue
            button = ui.build_button_widget(
                key, [0, 0,
                      self.button_w,
                      self.button_h], None,
                (self.button_text_margin_x, self.button_text_margin_y),
                command=lambda _, name=key: self.button_chose(name),
                active_bg_sprite=self.active_button_bg,
                inactive_bg_sprite=self.inactive_button_bg)
            self.holder.widgets.append(button)
        self.holder.widgets.append(ui.build_button_widget(
            "Quit", [0, 0, self.button_w, self.button_h], None,
            (self.button_text_margin_x, self.button_text_margin_y),
            command=lambda _: self.quit(),
            active_bg_sprite=self.active_button_bg,
            inactive_bg_sprite=self.inactive_button_bg,
            active_text_color=[1, 0, 0, 1]))
        self.holder.buffer_display = 0 if numb <= self.scroll_threshold\
            else 1
        self.holder.scroll = numb > self.scroll_threshold
    
    def button_chose(self, name: str) -> None:
        logging.debug(f'Chosen {name}')
        assets.variables['world_gen'] = name
        def _thread():
            map_size = (20, 20) # TODO
            tile_size = settings.BASE_TILE_SIZE
            game_over.reset_func()
            gen = world_gen.world_generators[name]
            state = dungeon.DungeonMapState(tile_size=tile_size,
                                            base_generator=gen,
                                            base_size=map_size)
            self.die()
            self.manager.push_state(state)
        threading.Thread(target=_thread).start()
    
    def quit(self) -> None:
        assets.running = False
    
    def render_gamestate(self, delta_time, renderer):
        index = self.holder.selection
        if index < len(self.world_keys):
            key = self.world_keys[index]
            highscore = assets.persists['highests'].get(key, 0)
            self.statscreen.text = f"Highest reached:\n{highscore}"
        else:
            self.statscreen.text = "Goodbye"
        super().render_gamestate(delta_time, renderer)
    
    @classmethod
    def init_globs(cls):
        cls.active_button_bg = assets.Sprites.instance.button_active
        cls.inactive_button_bg = assets.Sprites.instance.button_inactive
        cls.font = ui.default_font