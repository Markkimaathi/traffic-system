import numpy as np
from classes.vehicle import Vehicle, update_cmd
from classes.route import Route, route_position_to_world_position
from itertools import combinations
from scipy.optimize import minimize_scalar
from random import randint

CAR_COLLISION_DISTANCE = 2.5 # meters

class Collision:
    """A Collision represents a collision between two Vehicles at a given time."""
    vehicle0: Vehicle
    vehicle1: Vehicle
    delta0: float
    delta1: float
    time: float

    def __init__(self, vehicle0: Vehicle, vehicle1: Vehicle, delta0: float, delta1: float, time: float) -> None:
        self.vehicle0 = vehicle0
        self.vehicle1 = vehicle1
        self.delta0 = delta0
        self.delta1 = delta1
        self.time = time

class Manager:
    """A Manager controls all Vehicles within its radius, calculating and sending commands to ensure that Vehicles do
    not collide with each other."""
    position: np.ndarray
    radius: float = 25
    vehicles: list[Vehicle] = []
    intersecting_points = None
    collisions: list[Collision] = []
    run_once_for_debug = 0


    def __init__(self, position: np.ndarray, radius: float, routes: list[Route]) -> None:
        # initialize
        self.position = position
        self.radius = radius
        self.i = 0

def reset(manager: Manager) -> None:
    """Clear manager.vehicles attribute."""
    manager.vehicles.clear()

def manager_event_loop(manager: Manager, vehicles: list[Vehicle], cur_time: float) -> None:
    """Event loop for Manager. Updates manager.vehicles if a Vehicle enters its radius. Also recalculates and sends Commands on update of manager.vehicles."""
    if _update_manager_vehicle_list(manager, vehicles):
        _compute_and_send_acceleration_commands(manager, cur_time)

def _update_manager_vehicle_list(manager: Manager, vehicles: list[Vehicle]) -> bool:
    """Return True if new vehicles have been added to manager.vehicles."""
    new_vehicle = False
    for vehicle in vehicles:

        # vehicle within manager radius? 
        distance_to_vehicle = np.linalg.norm(route_position_to_world_position(vehicle.route, vehicle.route_position)-manager.position)

        # vehicle already in list and within manager radius?
        vehicle_in_list = any(manager_vehicle.id == vehicle.id for manager_vehicle in manager.vehicles)

        # append if not in list and inside radius
        if not vehicle_in_list and distance_to_vehicle <= manager.radius:
            manager.vehicles.append(vehicle)
            new_vehicle = True

        # remove if in list and outside radius
        elif vehicle_in_list and distance_to_vehicle > manager.radius:
            manager.vehicles.remove(vehicle)
            new_vehicle = True
    return new_vehicle

def get_collisions(manager: Manager, cur_time: float) -> list[Collision]:
    """Return list of Collisions between Vehicles in manager's radius."""
    collisions = []
    vehicle_pairs = combinations(manager.vehicles, 2)
    
    for vehicle_pair in vehicle_pairs:
        vehicle_out_of_bounds_time = int(min(time_until_end_of_route(vehicle_pair[0]), time_until_end_of_route(vehicle_pair[1])))
        def distance_objective(t):
            wp0 = route_position_to_world_position(vehicle_pair[0].route, route_position_at_delta_time(vehicle_pair[0], t, cur_time))
            wp1 = route_position_to_world_position(vehicle_pair[1].route, route_position_at_delta_time(vehicle_pair[1], t, cur_time))
            return np.linalg.norm(wp1-wp0)
        
        result = minimize_scalar(distance_objective, bounds=(0, vehicle_out_of_bounds_time), method='bounded')
        if result.success:
            time_of_collision = result.x + cur_time
            if distance_objective(result.x) <= CAR_COLLISION_DISTANCE:
                # print(f"The objects come within 2.5 meters of each other at t = {time_of_collision}")
                # print(f"{vehicle_pair[0].name}: {route_position_to_world_position(vehicle_pair[0].route, route_position_at_time(vehicle_pair[0], result.x, cur_time))}")
                # print(f"{vehicle_pair[1].name}: {route_position_to_world_position(vehicle_pair[1].route, route_position_at_time(vehicle_pair[1], result.x, cur_time))}")
                delta0 = vehicle_pair[0].route.total_length - route_position_at_delta_time(vehicle_pair[0], time_of_collision - cur_time, cur_time)
                delta1 = vehicle_pair[1].route.total_length - route_position_at_delta_time(vehicle_pair[1], time_of_collision - cur_time, cur_time)
                collisions.append(Collision(vehicle_pair[0], vehicle_pair[1], delta0, delta1, time_of_collision))
    return collisions

def get_collisions_between_two_vehicles(vehicle0: Vehicle, vehicle1: Vehicle, cur_time: float) -> Collision | None:
    vehicle_out_of_bounds_time = int(min(time_until_end_of_route(vehicle0), time_until_end_of_route(vehicle1)))
    def distance_objective(t):
            wp0 = route_position_to_world_position(vehicle0.route, route_position_at_delta_time(vehicle0, t, cur_time))
            wp1 = route_position_to_world_position(vehicle1.route, route_position_at_delta_time(vehicle1, t, cur_time))
            return np.linalg.norm(wp1-wp0) - CAR_COLLISION_DISTANCE
        
    result = minimize_scalar(distance_objective, bounds=(0, vehicle_out_of_bounds_time), method='bounded')
    if result.success:
        time_of_collision = result.x + cur_time
        if distance_objective(result.x) <= CAR_COLLISION_DISTANCE:
            print(f"The objects come within 2.5 meters of each other at t = {time_of_collision}")
            print(f"{vehicle0.name}: {route_position_to_world_position(vehicle0.route, route_position_at_delta_time(vehicle0, result.x, cur_time))}")
            print(f"{vehicle1.name}: {route_position_to_world_position(vehicle1.route, route_position_at_delta_time(vehicle1, result.x, cur_time))}")
            delta0 = vehicle0.route.total_length - route_position_at_delta_time(vehicle0, time_of_collision - cur_time, cur_time)
            delta1 = vehicle1.route.total_length - route_position_at_delta_time(vehicle1, time_of_collision - cur_time, cur_time)
            return Collision(vehicle0, vehicle1, delta0, delta1, time_of_collision)
    return None
    
def route_position_at_delta_time(vehicle: Vehicle, delta_time: float, cur_time: float) -> float:
    """Return vehicle's route position along its Route after delta_time seconds has passed."""

    if delta_time == 0:
        return vehicle.route_position
    # this allows us to assume that there will always be at least 2 elements in junction_list

    end_time = cur_time + delta_time
    # A junction is a period of time in which we can assume there is no change to acceleration
    # create junction lists
    junction_lists = [cur_time]
    for i in range(len(vehicle.command.accel_func.x)):
        if vehicle.command.accel_func.x[i] > cur_time and vehicle.command.accel_func.x[i] < end_time:
            junction_lists.append(vehicle.command.accel_func.x[i])
    junction_lists.append(end_time)

    start_junction_index = 0
    next_junction_index = 1
    velocity = vehicle.velocity
    delta_distance = 0
    while(start_junction_index != len(junction_lists)-1):
        junction_time_delta = junction_lists[next_junction_index] - junction_lists[start_junction_index]
        acceleration = vehicle.command.accel_func(junction_lists[start_junction_index])
        delta_distance += velocity*junction_time_delta + 0.5*acceleration*junction_time_delta**2
        velocity = velocity + acceleration*junction_time_delta

        start_junction_index += 1
        next_junction_index += 1

    return vehicle.route_position + delta_distance

def time_until_end_of_route(vehicle: Vehicle) -> float:
    """Return time til vehicle reaches the end of its route."""
    return (vehicle.route.total_length - vehicle.route_position) / vehicle.velocity

def _compute_and_send_acceleration_commands(manager: Manager, elapsed_time: float) -> None:
    """Compute and send commands."""

    # if manager.run_once_for_debug != 0:
    #     return
    # manager.run_once_for_debug = 1
    manager.vehicles.sort(key=lambda v: v.route_position, reverse=True)

    for i in range(len(manager.vehicles) - 1):
        # t = [elapsed_time, elapsed_time+1.8] # this will make cars crash for presets/collision_by_command.json
        # a = [0, 6]
        # if manager.vehicles[i].name == "acc":
        #     manager.vehicles[i].command = update_cmd(manager.vehicles[i].command, t, a, elapsed_time) # this will make cars crash for presets/collision_by_command.json



        # print(manager.vehicles[i+1].name)
        # print(f"route position at time: {elapsed_time}")
        # print(route_position_at_delta_time(manager.vehicles[i+1], 0, elapsed_time))
        # print(route_position_to_world_position(manager.vehicles[i+1].route, route_position_at_delta_time(manager.vehicles[i+1], 0, elapsed_time)))

        # print(f"route position at time: {elapsed_time+4}")
        # print(route_position_at_delta_time(manager.vehicles[i+1], 4, elapsed_time))
        # print(route_position_to_world_position(manager.vehicles[i+1].route, route_position_at_delta_time(manager.vehicles[i+1], 4, elapsed_time)))

        get_collisions_between_two_vehicles(manager.vehicles[i], manager.vehicles[i+1], elapsed_time)

        # def distance_objective(t):
        #     wp0 = route_position_to_world_position(manager.vehicles[i].route, route_position_at_delta_time(manager.vehicles[i], t, elapsed_time))
        #     wp1 = route_position_to_world_position(manager.vehicles[i+1].route, route_position_at_delta_time(manager.vehicles[i+1], t, elapsed_time))
        #     print(wp0)
        #     print(wp1)
        #     return np.linalg.norm(wp1-wp0) - CAR_COLLISION_DISTANCE
        
        # start = 0
        # end = 10
        # step = 0.5
        # current = start   
        # while current < end:
        #     print(f"at t = {current+elapsed_time}")
        #     print(distance_objective(current))
        #     print("")
        #     current += step





    # manager.collisions = get_collisions(manager, elapsed_time)

def _compute_command(elapsed_time: float) -> tuple[np.array, np.array]:
    """Return np.array of acceleration and time values."""
    # t = [elapsed_time, elapsed_time + 2.5] # this will make cars crash for presets/collision_by_command.json
    # a = [0, 6]
    t = [elapsed_time, elapsed_time + randint(1, 3), elapsed_time + randint(3, 5)]
    a = [randint(1, 3), randint(-3, 3), 3]
    return np.array(t), np.array(a)