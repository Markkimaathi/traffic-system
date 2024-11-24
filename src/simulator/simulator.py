SCREEN_WIDTH = 900
SCREEN_HEIGHT = 900

# world describes 100mx100m space
WORLD_WIDTH = 100
WORLD_HEIGHT = 100

import pygame
import numpy as np
from classes.vehicle import Vehicle
from manager.route import Node, Edge, Route
from .render import render_world
from .update import update_world

def run_simulation(initial_vehicles: list[Vehicle], nodes: list[Node], edges: list[Edge], routes: list[Route]): # requires initialization of lanes, manager, vehicles
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    running = True
    delta_time: float = 0

    vehicles = initial_vehicles

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("grey")

        # optionally render nodes and edges. for now always on
        render_world(screen, vehicles, nodes, edges)

        # we do not yet consider that Manager is a parallel computation. We can directly apply the adjustments that Manager makes to the vehicles.
        # manager adjust function call
        update_world(delta_time, vehicles)

        # flip() the display to put your work on screen
        pygame.display.flip()
        delta_time = clock.tick(60) / 1000
    pygame.quit()