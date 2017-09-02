#!/usr/bin/env python3

import logging
import sys

import pygame

from . import assets
from . import util
from .gfx import ui
from .gfx.objects import RaceTrackObject
from .gfx.racetrack import RaceTrack
from .gfx.tiles import Tile


CAPTION = "Rapide et Furieux - Level editor"

BACKGROUND_LAYER = -1
ELEMENT_SELECTOR_LAYER = 100
ELEMENT_SELECTOR_ARROWS_LAYER = 150
RACE_TRACK_LAYER = 50
MOUSE_CURSOR_LAYER = 500

logger = logging.getLogger(__name__)


class Editor(object):
    def __init__(self, screen):
        elements = [Tile(tile_rsc) for tile_rsc in assets.TILES]
        elements += [RaceTrackObject(obj_rsc) for obj_rsc in assets.OBJECTS]
        elements += [RaceTrackObject(obj_rsc) for obj_rsc in assets.CARS]
        elements += [RaceTrackObject(obj_rsc) for obj_rsc in assets.MOTORCYCLES]
        elements += [RaceTrackObject(obj_rsc) for obj_rsc in assets.POWERUPS]
        elements += [
            RaceTrackObject(obj_rsc)
            for explosion in assets.EXPLOSIONS
            for obj_rsc in explosion
        ]

        self.element_selector = ui.ElementSelector(elements, screen)
        self.selected = None

        self.arrow_up = ui.Arrow(assets.ARROW_UP)
        self.arrow_up.relative = (
            (self.element_selector.size[0] / 2) - (self.arrow_up.size[0] / 2),
            0
        )
        self.arrow_down = ui.Arrow(assets.ARROW_DOWN)
        self.arrow_down.relative = (
            (self.element_selector.size[0] / 2) - (self.arrow_down.size[0] / 2),
            screen.get_size()[1] - self.arrow_down.size[1]
        )

        element_offset = (
            self.element_selector.size[1] -
            (self.element_selector.size[1] % assets.TILE_SIZE[1])
        )
        self.element_selector_controls = [
            (self.arrow_down, -element_offset),
            (self.arrow_up, element_offset),
        ]

        self.race_track = RaceTrack(grid_margin=5)

        util.register_drawer(BACKGROUND_LAYER, ui.Background())
        util.register_drawer(ELEMENT_SELECTOR_LAYER, self.element_selector)
        for (control, offset) in self.element_selector_controls:
            util.register_drawer(ELEMENT_SELECTOR_ARROWS_LAYER, control)
        util.register_drawer(RACE_TRACK_LAYER, self.race_track)
        util.register_event_listener(self.on_click)
        util.register_event_listener(self.on_mouse_motion)

    def on_click(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        position = pygame.mouse.get_pos()

        # control ?
        for (control, offset) in self.element_selector_controls:
            if control.rect.collidepoint(position):
                self.element_selector.relative = (
                    self.element_selector.relative[0],
                    min(0, self.element_selector.relative[1] + offset)
                )
                return

        # Element selected ?
        selected = self.element_selector.get_element(position)
        if selected is not None:
            if self.selected:
                util.unregister_drawer(self.selected)
            self.selected = selected.copy()
            self.selected.relative = position
            util.register_drawer(MOUSE_CURSOR_LAYER, self.selected)
            logger.info("Selected: %s", self.selected)
            return

        if self.selected is None:
            return

        # place the selected element on the race track
        self.race_track.add_element(position, self.selected)
        util.unregister_drawer(self.selected)
        self.selected = None

    def on_mouse_motion(self, event):
        if event.type != pygame.MOUSEMOTION:
            return
        if self.selected is None:
            return
        position = pygame.mouse.get_pos()
        self.selected.relative = position


def on_uncatched_exception_cb(exc_type, exc_value, exc_tb):
    logger.error(
        "=== UNCATCHED EXCEPTION ===",
        exc_info=(exc_type, exc_value, exc_tb)
    )
    logger.error(
        "==========================="
    )


def main():
    lg = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)-6s %(name)-30s %(message)s')
    handler.setFormatter(formatter)
    lg.addHandler(handler)
    sys.excepthook = on_uncatched_exception_cb
    logging.getLogger().setLevel(logging.DEBUG)

    logger.info(CAPTION)

    logger.info("Loading ...")
    pygame.init()
    screen = util.set_default_resolution()
    pygame.display.set_caption(CAPTION)

    Editor(screen)
    util.main_loop(screen)
