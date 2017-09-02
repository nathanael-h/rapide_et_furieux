import pygame

from .. import RelativeGroup
from .. import RelativeSprite
from ... import assets


class Tile(RelativeSprite):
    def __init__(self, resource):
        super().__init__(resource)

    def copy(self):
        return Tile(self.resource, self.image)


class Arrow(RelativeSprite):
    def __init__(self, resource):
        super().__init__(resource)


class TileSelector(RelativeGroup):
    MARGIN = 5
    COLUMNS = 4
    ARROW_UP = ("rapide_et_furieux.gfx.ui", "arrowUp.png")
    ARROW_DOWN = ("rapide_et_furieux.gfx.ui", "arrowDown.png")

    def __init__(self, tiles, screen):
        super().__init__()
        for (idx, tile) in enumerate(tiles):
            tile.relative = (
                (idx % self.COLUMNS) * (assets.TILE_SIZE[0] + self.MARGIN),
                int(idx / self.COLUMNS) * (assets.TILE_SIZE[1] + self.MARGIN)
            )
            tile.parent = self
        self.add(*tiles)

        arrow_up = Arrow(self.ARROW_UP)
        arrow_up.relative = (
            ((assets.TILE_SIZE[0] + self.MARGIN) * self.COLUMNS) / 2 -
            arrow_up.size[0] / 2,
            0
        )
        arrow_down = Arrow(self.ARROW_DOWN)
        arrow_down.relative = (
            ((assets.TILE_SIZE[0] + self.MARGIN) * self.COLUMNS) / 2 -
            arrow_down.size[0] / 2,
            screen.get_size()[1] - arrow_down.size[1]
        )
        self.controls = [arrow_down, arrow_up]

        self.size = (
            self.COLUMNS * (self.MARGIN + assets.TILE_SIZE[0]),
            screen.get_size()[1]
        )

    @property
    def rect(self):
        return ((0, 0), self.size)

    def draw(self, screen):
        pygame.draw.rect(screen, (128, 128, 128), self.rect, 0)
        super().draw(screen)
