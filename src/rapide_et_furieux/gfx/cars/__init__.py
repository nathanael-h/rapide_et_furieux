#!/usr/bin/env python3

import collections
import math

import pygame

from .. import RelativeSprite
from ... import assets
from ... import util
from ..collisions import CollisionObject


Controls = collections.namedtuple(
    typename="controls",
    field_names=(
        # all are booleans
        "accelerate",
        "brake",
        "steer_left",
        "steer_right",
    ),
)


class Car(RelativeSprite, CollisionObject):
    def __init__(self, resource, race_track, game_settings,
                 spawn_point, spawn_orientation, image=None):
        super().__init__(resource, image)

        self.h = hash(spawn_point)

        self.game_settings = game_settings
        self.parent = race_track

        self.angle = spawn_orientation

        self.pts = []
        self._position = (0, 0)
        # we work in radians here
        self._radians = 0

        self.controls = Controls(
            accelerate=False,
            brake=False,
            steer_left=False,
            steer_right=False
        )

        # relative to the car
        # so first number is the forward speed,
        # and second one is the lateral speed (drifting)
        self.speed = (0, 0)

        self.original_size = self.original.get_size()

        self.radians = spawn_orientation * math.pi / 180 - (math.pi / 2)
        self.position = (
            # center of the car
            (spawn_point[0] * assets.TILE_SIZE[0]) + (assets.TILE_SIZE[0] / 2),
            (spawn_point[1] * assets.TILE_SIZE[1]) + (assets.TILE_SIZE[1] / 2),
        )

        self.update_image()

    def hash(self):
        return self.h

    COLLISION_MARGIN = 3

    def recompute_pts(self):
        pts = [
            ((- (self.original_size[0] / 2)) + self.COLLISION_MARGIN,
             (- (self.original_size[1] / 2)) + self.COLLISION_MARGIN),
            ((self.original_size[0] / 2) - self.COLLISION_MARGIN,
             (- (self.original_size[1] / 2)) + self.COLLISION_MARGIN),
            ((self.original_size[0] / 2) - self.COLLISION_MARGIN,
             (self.original_size[1] / 2) - self.COLLISION_MARGIN),
            ((- (self.original_size[0] / 2)) + self.COLLISION_MARGIN,
             (self.original_size[1] / 2) - self.COLLISION_MARGIN),
        ]
        # TODO(Jflesch): can optim: to_polar() could be called only once,
        # and the other points can be deduced
        pts = [util.to_polar(pt) for pt in pts]
        pts = [
            (
                length,
                # The gfx are oriented to the up side, but radians=0 == right
                angle - self.radians + (math.pi / 2)
            ) for (length, angle) in pts
        ]
        pts = [util.to_cartesian(pt) for pt in pts]
        pts = [
            (x + self.position[0], y + self.position[1])
            for (x, y) in pts
        ]
        self.pts = pts

    def _set_radians(self, v):
        self._radians = v
        self.recompute_pts()

    def _get_radians(self):
        return self._radians

    radians = property(_get_radians, _set_radians)

    def _set_position(self, v):
        self._position = v
        self.recompute_pts()

    def _get_position(self):
        return self._position

    position = property(_get_position, _set_position)

    def update_image(self):
        # The gfx are oriented to the up side, but radians=0 == right
        self.angle = (-self.radians + (math.pi / 2)) * 180 / math.pi
        self.image = pygame.transform.rotate(self.original, -self.angle)
        self.size = self.image.get_size()
        self.relative = (
            int(self.position[0]) - (self.size[0] / 2),
            int(self.position[1]) - (self.size[1] / 2),
        )

    def compute_forward_speed(self, current_speed, frame_interval, terrain):
        engine_braking = self.game_settings['engine braking'][terrain]
        engine_braking *= frame_interval
        if current_speed < 0:
            engine_braking *= -1

        if not self.controls.accelerate and not self.controls.brake:
            if current_speed == 0:
                return 0

            # --> engine braking
            speed = current_speed - engine_braking

            # if speed change sign, just stall the car
            if current_speed >= 0 and speed <= 0:
                speed = 0
            elif current_speed <= 0 and speed >= 0:
                speed = 0
        elif self.controls.brake and current_speed > 0:
            # TODO(Jflesch): burning tires

            # --> braking
            acceleration = -self.game_settings['braking'][terrain]
            acceleration *= frame_interval

            # apply to speed
            speed = current_speed + acceleration
            if speed < 0:
                speed = 0
        else:
            # --> accelerate (forward or backward)
            acceleration = self.game_settings['acceleration'][terrain]
            acceleration *= frame_interval

            if self.controls.brake:
                acceleration *= -1

            # apply to speed
            speed = current_speed + acceleration

        # limit speed based on terrain
        max_speed = self.game_settings['max_speed'][terrain]
        if speed > max_speed['forward']:
            speed = max(current_speed - engine_braking, max_speed['forward'])
        elif speed < -max_speed['reverse']:
            speed = min(current_speed - engine_braking, -max_speed['reverse'])

        return speed

    def compute_lateral_speed(self, speed, frame_interval, terrain):
        slowdown = self.game_settings['lateral_speed_slowdown'][terrain]
        if speed == 0:
            return speed

        # TODO(Jflesch): we may be burning tires

        if speed > 0:
            speed -= slowdown * frame_interval
            return speed if speed >= 0 else 0
        else:  # speed < 0
            speed += slowdown * frame_interval
            return speed if speed <= 0 else 0

    def update_speed(self, frame_interval, terrain):
        self.speed = (
            self.compute_forward_speed(self.speed[0], frame_interval, terrain),
            self.compute_lateral_speed(self.speed[1], frame_interval, terrain)
        )

    def apply_speed(self, frame_interval, position, speed=None):
        # self.speed is relative to the car, but self.position is relative
        # to the race track
        # so we switch to polar coordinates, change the angle, and switch
        # back to cartesian coordinates

        if speed is None:
            speed = self.speed
        speed = util.to_polar(speed)
        speed = (speed[0], speed[1] - self.radians)
        speed = util.to_cartesian(speed)
        speed = (speed[0] * frame_interval, speed[1] * frame_interval)

        return (
            position[0] + speed[0],
            position[1] + speed[1],
        )

    def get_steering(self, frame_interval, terrain):
        if not self.controls.steer_left and not self.controls.steer_right:
            return 0
        ref_speed = self.game_settings['steering']['ref_speed']
        angle_change = self.game_settings['steering'][terrain] * frame_interval
        if self.controls.steer_left:
            angle_change *= -1
        if self.speed[0] < 0:
            angle_change *= -1
        angle_change *= min(1.0, abs(self.speed[0]) / ref_speed)
        return angle_change

    def turn(self, angle_change):
        self.radians = self.radians - angle_change

        # cars turns, but not its speed / momentum
        # turn the speed into polar coordinates --> change the angle,
        # switch back
        speed = util.to_polar(self.speed)
        speed = (speed[0], speed[1] - angle_change)
        self.speed = util.to_cartesian(speed)
        return angle_change

    def move(self, frame_interval):
        COLLISION = True

        terrain = self.parent.get_terrain(self.position)

        self.update_speed(frame_interval, terrain)

        # steering
        steering = self.get_steering(frame_interval, terrain)
        previous_radians = self.radians
        previous_speed = self.speed
        self.turn(steering)

        if COLLISION:
            collisions = self.parent.collisions.get_collisions(self, limit=1)
            if len(collisions) > 0:
                # cancel steering
                self.speed = previous_speed
                self.radians = previous_radians

        # move
        prev_position = self.position
        self.position = self.apply_speed(frame_interval, self.position)

        if COLLISION:
            collisions = self.parent.collisions.get_collisions(self)
            if len(collisions) > 0:
                # cancel movement
                self.position = prev_position

                # update speed based on collision
                prev_radians = self.radians
                (self.speed, self.radians) = self.parent.collisions.collide(
                    self, collisions, frame_interval
                )

                # apply new speed if possible before it's cancelled
                # + angle
                prev_position = self.position
                self.position = self.apply_speed(frame_interval, self.position)

                collisions = self.parent.collisions.get_collisions(
                    self, limit=1
                )
                if len(collisions) > 0:
                    # .. without angle ?
                    self.radians = prev_radians
                    self.position = prev_position
                    self.position = self.apply_speed(frame_interval,
                                                     self.position)
                    collisions = self.parent.collisions.get_collisions(
                        self, limit=1
                    )

                    if len(collisions) > 0:
                        # ok screw it ...
                        self.radians = prev_radians
                        self.position = prev_position

        self.update_image()

    def draw(self, screen):
        super().draw(screen)
        if not self.parent.debug:
            return
        # it would be faster to draw the rectangle on the image itself
        # but this piece of code is actually used to check that the points of
        # the car are correctly found.
        p = self.parent.absolute
        for (a, b) in util.pairwise(self.pts):
            pygame.draw.line(
                screen, (255, 0, 0),
                (a[0] + p[0], a[1] + p[1]),
                (b[0] + p[0], b[1] + p[1]),
                2
            )
