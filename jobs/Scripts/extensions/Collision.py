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
    LGSVL__SIMULATION_DURATION_SECS = 120.0
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

    def on_collision(agent1, agent2, contact):
        name1 = "STATIC OBSTACLE" if agent1 is None else agent1.name
        name2 = "STATIC OBSTACLE" if agent2 is None else agent2.name
        error_message = "{} collided with {}".format(name1, name2)
        set_passed(case_json_path)
        sys.exit()

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

    print("adding npcs")
    # school bus, 20m ahead, perpendicular to road, stopped
    state = lgsvl.AgentState()
    forward = lgsvl.utils.transform_to_forward(spawns[0])
    right = lgsvl.utils.transform_to_right(spawns[0])
    state.transform.position = spawns[0].position + 20.0 * forward
    state.transform.rotation.y = spawns[0].rotation.y + 90.0
    bus = sim.add_agent("SchoolBus", lgsvl.AgentType.NPC, state)

    state = lgsvl.AgentState()
    state.velocity = 6 * forward
    state.transform = spawns[spawn_index]  # TODO some sort of Env Variable so that user/wise can select from list
    print("Loading vehicle {}...".format(vehicle_conf))
    ego = sim.add_agent(vehicle_conf, lgsvl.AgentType.EGO, state)
    ego.on_collision(on_collision)

    sim.run(LGSVL__SIMULATION_DURATION_SECS)
