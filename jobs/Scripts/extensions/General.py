from datetime import datetime
from environs import Env
import random
import lgsvl
from actions import *


def execute(case_json_path):
    env = Env()

    SIMULATOR_HOST = env.str("LGSVL__SIMULATOR_HOST", "127.0.0.1")
    SIMULATOR_PORT = env.int("LGSVL__SIMULATOR_PORT", 8181)
    BRIDGE_HOST = env.str("LGSVL__AUTOPILOT_0_HOST", "127.0.0.1")
    BRIDGE_PORT = env.int("LGSVL__AUTOPILOT_0_PORT", 9090)

    LGSVL__AUTOPILOT_HD_MAP = env.str("LGSVL__AUTOPILOT_HD_MAP", "Borregas Ave")
    LGSVL__AUTOPILOT_0_VEHICLE_CONFIG = env.str("LGSVL__AUTOPILOT_0_VEHICLE_CONFIG", 'Lincoln2017MKZ_LGSVL')
    LGSVL__SIMULATION_DURATION_SECS = 90.0
    LGSVL__RANDOM_SEED = env.int("LGSVL__RANDOM_SEED", 51472)

    vehicle_conf = env.str("LGSVL__VEHICLE_0", lgsvl.wise.DefaultAssets.ego_lincoln2017mkz_apollo6_modular)
    scene_name = env.str("LGSVL__MAP", lgsvl.wise.DefaultAssets.map_borregasave)
    sim = lgsvl.Simulator(SIMULATOR_HOST, SIMULATOR_PORT)

    try:
        print("Loading map {}...".format(scene_name))
        sim.load(scene_name, LGSVL__RANDOM_SEED) # laod map with random seed
    except Exception:
        if sim.current_scene == scene_name:
            sim.reset()
        else:
            sim.load(scene_name)


    # reset time of the day
    sim.set_date_time(datetime(2020, 7, 1, 15, 0, 0, 0), True)

    spawns = sim.get_spawn()
    # select spawn deterministically depending on the seed
    spawn_index = LGSVL__RANDOM_SEED % len(spawns)

    state = lgsvl.AgentState()
    state.transform = spawns[spawn_index]  # TODO some sort of Env Variable so that user/wise can select from list
    print("Loading vehicle {}...".format(vehicle_conf))
    ego = sim.add_agent(vehicle_conf, lgsvl.AgentType.EGO, state)

    print("Connecting to bridge...")
    # The EGO is now looking for a bridge at the specified IP and port
    ego.connect_bridge(BRIDGE_HOST, BRIDGE_PORT)

    def on_collision(agent1, agent2, contact):
        name1 = "STATIC OBSTACLE" if agent1 is None else agent1.name
        name2 = "STATIC OBSTACLE" if agent2 is None else agent2.name
        error_message = "{} collided with {}".format(name1, name2)
        set_error(case_json_path, error_message)
        sys.exit()

    ego.on_collision(on_collision)

    dv = lgsvl.dreamview.Connection(sim, ego, BRIDGE_HOST)
    dv.set_hd_map(LGSVL__AUTOPILOT_HD_MAP)
    dv.set_vehicle(LGSVL__AUTOPILOT_0_VEHICLE_CONFIG)

    destination_index = LGSVL__RANDOM_SEED % len(spawns[spawn_index].destinations)
    destination = spawns[spawn_index].destinations[destination_index] # TODO some sort of Env Variable so that user/wise can select from list

    default_modules = [
        'Localization',
        'Transform',
        'Routing',
        'Prediction',
        'Planning',
        'Control',
        'Recorder'
    ]

    dv.disable_apollo()
    dv.setup_apollo(destination.position.x, destination.position.z, default_modules)

    set_passed(case_json_path)

    sim.run(LGSVL__SIMULATION_DURATION_SECS)
